"""Isolated anonymous local workspace sessions. No GitHub/Watson credentials."""
import hashlib
import os
import re
import secrets

from fastapi import APIRouter, Request, Response

from app.services.v1_errors import WorkspaceError

router = APIRouter()
COOKIE = 'codecanopy_workspace'
TOKEN = re.compile(r'^[a-f0-9]{64}$')


def workspace_session(request: Request) -> str:
    token = request.cookies.get(COOKIE, '')
    if not TOKEN.fullmatch(token):
        raise WorkspaceError('SESSION_REQUIRED', 'Open GREPO to start a workspace session.', 401)
    return hashlib.sha256(token.encode()).hexdigest()


@router.post('/session')
def create_session(request: Request, response: Response):
    token = request.cookies.get(COOKIE, '')
    if not TOKEN.fullmatch(token):
        token = secrets.token_hex(32)
    response.set_cookie(COOKIE, token, httponly=True, secure=request.url.scheme == 'https' or bool(os.environ.get('VERCEL')), samesite='strict', max_age=86400)
    return {'schema_version': '1.0', 'status': 'ready'}
