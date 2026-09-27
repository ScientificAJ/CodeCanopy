"""Hosted chat avoids needless provider work without narrowing real evidence."""
import httpx
import pytest

from app.api.v1 import ask
from test_v1_workspace import client, import_files


@pytest.fixture
def hosted_chat(monkeypatch):
    # Exercise only the hosted chat policy with the normal local fixture store.
    monkeypatch.setattr(ask, '_hosted', lambda: True)
    monkeypatch.setenv('GROQ_API_KEY', 'synthetic-test-key')
    provider_client = ask._provider_client
    provider_client.cache_clear()
    yield
    provider_client.cache_clear()


def test_standalone_hosted_greeting_does_not_scan_or_call_provider(client, hosted_chat, monkeypatch):
    path, _, _ = import_files(client, {'README.md': 'Private fixture content'})
    def unexpected(*args, **kwargs):
        raise AssertionError('A standalone greeting must not scan source or call a provider')
    monkeypatch.setattr(ask, 'retrieve', unexpected)
    monkeypatch.setattr(ask, '_provider_client', unexpected)
    response = client.post(path + '/chat', json={'question': 'Hi GREPO!'})
    assert response.status_code == 200
    assert response.json()['sources'] == []
    assert 'no repository source was searched' in response.json()['context_hint']
    assert 'Private fixture content' not in response.text
    assert 'chat_retrieval;dur=0.0' in response.headers['server-timing']
    assert 'chat_provider;dur=0.0' in response.headers['server-timing']


@pytest.mark.parametrize('body', [
    {'question': 'hi, explain renew_lease'},
    {'question': 'hi', 'purpose': 'documentation'},
    {'question': 'hi', 'history': [{'role': 'user', 'content': 'Explain renew_lease'}]},
])
def test_real_questions_drafts_and_followups_keep_deep_source_and_budgets(client, hosted_chat, monkeypatch, body):
    path, _, _ = import_files(client, {'deep.py': '# padding\n' * 1200 + 'def renew_lease(token):\n    return token + "renewed"\n'})
    calls = []
    class Provider:
        def post(self, url, **kwargs):
            calls.append(kwargs)
            prompt = kwargs['json']['messages'][0]['content']
            # Neither hosting nor the greeting optimization discards deep code.
            if 'renew_lease' in str(body):
                assert '1201: def renew_lease' in prompt
            assert 'untrusted data' in prompt
            return httpx.Response(200, request=httpx.Request('POST', url), json={
                'choices': [{'message': {'content': 'Source evidence [S1].'}, 'finish_reason': 'stop'}],
            })
    monkeypatch.setattr(ask, '_provider_client', lambda: Provider())
    response = client.post(path + '/chat', json=body)
    assert response.status_code == 200
    assert len(calls) == 1
    assert calls[0]['json']['model'] == ask.MODEL
    assert calls[0]['json']['max_tokens'] == (4000 if body.get('purpose') == 'documentation' else 1600)
    assert 'reasoning_effort' not in calls[0]['json']
    assert response.json()['sources']
    assert 'chat_retrieval;dur=' in response.headers['server-timing']
    assert 'chat_provider;dur=' in response.headers['server-timing']


def test_hosted_provider_reuses_connection_client_but_keeps_credentials_request_local(client, hosted_chat, monkeypatch):
    path, _, _ = import_files(client, {'a.py': 'def add(a, b):\n    return a + b\n'})
    created, requests = [], []
    class Provider:
        def __init__(self, **kwargs):
            assert 'headers' not in kwargs
            created.append(self)
        def close(self):
            pass
        def post(self, url, **kwargs):
            requests.append(kwargs)
            return httpx.Response(200, request=httpx.Request('POST', url), json={
                'choices': [{'message': {'content': 'It adds values [S1].'}, 'finish_reason': 'stop'}],
            })
    monkeypatch.setattr(ask.httpx, 'Client', Provider)
    for key in ['synthetic-first-key', 'synthetic-second-key']:
        monkeypatch.setenv('GROQ_API_KEY', key)
        response = client.post(path + '/chat', json={'question': 'What does add do?'})
        assert response.status_code == 200
    assert len(created) == 1 and len(requests) == 2
    assert [request['headers']['Authorization'] for request in requests] == [
        'Bearer synthetic-first-key', 'Bearer synthetic-second-key',
    ]


def test_hosted_greeting_still_requires_authorized_snapshot(client, hosted_chat, monkeypatch):
    path, _, _ = import_files(client, {'a.py': 'x = 1'})
    # An unknown project must fail before the fast path can return success.
    project_id = path.split('/')[4]
    response = client.post(path.replace(project_id, '0' * 32) + '/chat', json={'question': 'hi'})
    assert response.status_code == 404
