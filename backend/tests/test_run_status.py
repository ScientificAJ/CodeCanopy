"""Run status must reflect degradation, not diagnostics.

A binary file and a file above the parse budget both still import: the source
is readable in the workspace, only its syntax could not be extracted. Labelling
the whole run PARTIAL for those made a repository of screenshots look broken.

A run is PARTIAL only when something of severity 'error' was recorded, which in
practice means the import was interrupted. Those paths set FAILED themselves, so
this is the guard that keeps an informational diagnostic from being escalated
and an interrupted run from being softened.
"""
from __future__ import annotations

from app.models.v1.snapshot import RunDiagnostic, RunStatus


def _final_status(diagnostics: list[RunDiagnostic]) -> RunStatus:
    """Mirror the decision made in run_service.finish_run."""
    degraded = [d for d in diagnostics if d.severity == 'error']
    return RunStatus.PARTIAL if degraded else RunStatus.COMPLETED


def test_no_diagnostics_is_completed():
    assert _final_status([]) is RunStatus.COMPLETED


def test_binary_file_alone_is_completed_not_partial():
    """A PNG in the repo is the common case, not a failure."""
    d = RunDiagnostic(
        file_path='bob_sessions/01/task03_summary.png',
        stage='inventory',
        message='Binary or unsupported text encoding; metadata only.',
    )
    assert _final_status([d]) is RunStatus.COMPLETED


def test_parse_budget_alone_is_completed_not_partial():
    """Above 1 MiB the source is still browsable, so the import is whole."""
    d = RunDiagnostic(
        file_path='vendor/archify/bundle.js',
        stage='parse',
        message='Syntax extraction skipped above 1 MiB; source remains browsable.',
    )
    assert _final_status([d]) is RunStatus.COMPLETED


def test_many_informational_diagnostics_stay_completed():
    """The reported bug: 51 diagnostics on a 832-file repo, zero failures."""
    diagnostics = [
        RunDiagnostic(
            file_path=f'bob_sessions/{i:02d}/panel.png',
            stage='inventory',
            message='Binary or unsupported text encoding; metadata only.',
        )
        for i in range(49)
    ] + [
        RunDiagnostic(
            file_path=f'src/large{i}.ts',
            stage='parse',
            message='Syntax extraction failed or exceeded its resource budget; original text remains browsable.',
        )
        for i in range(2)
    ]
    assert len(diagnostics) == 51
    assert _final_status(diagnostics) is RunStatus.COMPLETED


def test_error_severity_marks_partial():
    d = RunDiagnostic(
        stage='import',
        message='Import interrupted by server restart. Please import again.',
        severity='error',
    )
    assert _final_status([d]) is RunStatus.PARTIAL


def test_mixed_diagnostics_with_one_error_stay_partial():
    """Informational noise must not mask a real error."""
    diagnostics = [
        RunDiagnostic(file_path='a.png', stage='inventory', message='Binary or unsupported text encoding; metadata only.'),
        RunDiagnostic(stage='import', message='Import failed.', severity='error'),
    ]
    assert _final_status(diagnostics) is RunStatus.PARTIAL


def test_run_service_uses_severity_not_diagnostic_count():
    """Guard against the original bug returning.

    Reads the real source so a future edit that reverts to counting
    diagnostics fails here rather than in the UI.
    """
    import inspect

    from app.services import run_service

    source = inspect.getsource(run_service._import)
    assert 'RunStatus.PARTIAL if run.diagnostics' not in source, (
        'the import path must not treat any diagnostic as a partial import'
    )
    assert "d.severity == 'error'" in source, (
        'the import path must gate PARTIAL on error severity'
    )
