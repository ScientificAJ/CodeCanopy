from dotenv import load_dotenv
from pathlib import Path
# Search upward for .env so it works whether uvicorn is started from
# backend/ or from the repo root (e.g. e:\CodeCanopy\.env)
load_dotenv(Path(__file__).resolve().parent.parent.parent / '.env')
load_dotenv()  # also pick up backend/.env if present

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router

import asyncio
from contextlib import asynccontextmanager, suppress
from app.services.retention_service import purge_expired


@asynccontextmanager
async def lifespan(app: FastAPI):
    await asyncio.to_thread(purge_expired)
    async def retention_loop():
        while True:
            await asyncio.sleep(60)
            await asyncio.to_thread(purge_expired)
    task = asyncio.create_task(retention_loop())
    yield
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task


app = FastAPI(title="GREPO API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

# V1 errors use the PRD envelope; the legacy routes retain their contracts.
import uuid
import os
import secrets
from fastapi import Request
from app.services import cloud_storage
from fastapi.responses import JSONResponse
from app.services.v1_errors import WorkspaceError


@app.exception_handler(WorkspaceError)
async def workspace_error_handler(request: Request, error: WorkspaceError):
    return JSONResponse(status_code=error.status, content={'error': {
        'code': error.code, 'message': error.message, 'retryable': error.status in {408, 429, 502, 503},
        'request_id': uuid.uuid4().hex, 'details': {},
    }})


@app.middleware('http')
async def local_workspace_boundary(request: Request, call_next):
    if cloud_storage.enabled() and request.url.path.startswith('/api/projects'):
        return JSONResponse(status_code=404, content={'detail': 'Not found'})
    if request.url.path.startswith('/api/v1'):
        origin = request.headers.get('origin')
        allowed = {'http://localhost:5173', 'http://127.0.0.1:5173', str(request.base_url).rstrip('/')}
        if origin and origin not in allowed:
            return JSONResponse(status_code=403, content={'error': {'code': 'ORIGIN_DENIED', 'message': 'Workspace origin is not allowed.', 'retryable': False, 'request_id': uuid.uuid4().hex, 'details': {}}})
    response = await call_next(request)
    if request.url.path.startswith('/api/v1'):
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler


@app.exception_handler(RequestValidationError)
async def request_validation_handler(request: Request, error: RequestValidationError):
    if request.url.path.startswith('/api/v1'):
        # Do not echo submitted values (URLs can accidentally contain credentials).
        return await workspace_error_handler(request, WorkspaceError('INVALID_REQUEST', 'One or more request fields are invalid.', 422))
    return await request_validation_exception_handler(request, error)


@app.get('/api/internal/cleanup', include_in_schema=False)
async def cleanup_hosted_workspaces(request: Request):
    expected = os.environ.get('CRON_SECRET', '')
    supplied = request.headers.get('authorization', '')
    if not expected or not secrets.compare_digest(supplied, 'Bearer ' + expected):
        return JSONResponse(status_code=401, content={'detail': 'Unauthorized'})
    if not cloud_storage.enabled():
        return {'deleted': 0}
    deleted = await asyncio.to_thread(cloud_storage.purge_expired)
    await asyncio.to_thread(purge_expired)
    return {'deleted': deleted}
