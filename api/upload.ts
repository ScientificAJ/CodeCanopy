import { createHash, randomUUID } from 'node:crypto'
import { handleUpload, type HandleUploadBody } from '@vercel/blob/client'

const MAX_UPLOAD_BYTES = 1024 ** 3
const UPLOAD_PATH = /^uploads\/([a-f0-9]{64})\/([a-f0-9]{32})\.zip$/
const headers = { 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' }

class UploadRequestError extends Error {
  status: number
  code: string
  constructor(status: number, code: string, message: string) {
    super(message)
    this.status = status
    this.code = code
  }
}

function workspace(request: Request): string {
  const origin = request.headers.get('origin')
  if (!origin || origin !== new URL(request.url).origin) {
    throw new UploadRequestError(403, 'ORIGIN_DENIED', 'Workspace origin is not allowed.')
  }
  const cookie = request.headers.get('cookie') ?? ''
  const token = cookie.split(';').map(part => part.trim())
    .find(part => part.startsWith('codecanopy_workspace='))?.slice('codecanopy_workspace='.length)
  if (!token || !/^[a-f0-9]{64}$/.test(token)) {
    throw new UploadRequestError(401, 'SESSION_REQUIRED', 'Open GREPO to start a workspace session.')
  }
  return createHash('sha256').update(token).digest('hex')
}

export default async function upload(request: Request): Promise<Response> {
  if (request.method !== 'POST') {
    return Response.json({ error: 'Use POST for uploads.' }, { status: 405, headers: { ...headers, Allow: 'POST' } })
  }
  try {
    // Only upload metadata reaches this endpoint; ZIP bytes go straight to Blob.
    const raw = await request.text()
    if (raw.length > 8192) throw new UploadRequestError(413, 'INVALID_REQUEST', 'Upload metadata is too large.')
    let body
    try { body = JSON.parse(raw) } catch {
      throw new UploadRequestError(400, 'INVALID_REQUEST', 'Upload metadata is invalid.')
    }
    if (!body || typeof body !== 'object') {
      throw new UploadRequestError(400, 'INVALID_REQUEST', 'Upload metadata is invalid.')
    }
    if (body.type === 'grepo.prepare-upload') {
      const owner = workspace(request)
      if (typeof body.name !== 'string' || body.name.length > 255 || !body.name.toLowerCase().endsWith('.zip')) {
        throw new UploadRequestError(400, 'INVALID_ARCHIVE', 'Choose a ZIP archive.')
      }
      if (!Number.isSafeInteger(body.size) || body.size <= 0 || body.size > MAX_UPLOAD_BYTES) {
        throw new UploadRequestError(413, 'UPLOAD_TOO_LARGE', 'Choose a ZIP archive up to 1 GiB.')
      }
      const pathname = `uploads/${owner}/${randomUUID().replaceAll('-', '')}.zip`
      return Response.json({ pathname, maximumSizeInBytes: MAX_UPLOAD_BYTES }, { headers })
    }
    if (body.type !== 'blob.generate-client-token' && body.type !== 'blob.upload-completed') {
      throw new UploadRequestError(400, 'INVALID_REQUEST', 'Upload request is invalid.')
    }
    // Completion callbacks arrive from Blob, without browser cookies. The SDK
    // verifies their signature before calling onUploadCompleted.
    if (body.type === 'blob.generate-client-token') {
      workspace(request)
      if (!body.payload || typeof body.payload.pathname !== 'string' || typeof body.payload.multipart !== 'boolean') {
        throw new UploadRequestError(400, 'INVALID_REQUEST', 'Upload request is invalid.')
      }
    }
    const result = await handleUpload({
      body: body as HandleUploadBody,
      request,
      onBeforeGenerateToken: async pathname => {
        const owner = workspace(request)
        const match = UPLOAD_PATH.exec(pathname)
        if (!match || match[1] !== owner) {
          throw new UploadRequestError(403, 'UPLOAD_DENIED', 'Upload does not belong to this workspace.')
        }
        return {
          maximumSizeInBytes: MAX_UPLOAD_BYTES,
          allowedContentTypes: ['application/zip'],
          addRandomSuffix: false,
          allowOverwrite: false,
          validUntil: Date.now() + 60 * 60 * 1000,
          callbackUrl: new URL('/api/upload', request.url).href,
          tokenPayload: JSON.stringify({ version: 1, workspace: owner, pathname }),
        }
      },
      onUploadCompleted: async ({ blob, tokenPayload }) => {
        const owner = JSON.parse(tokenPayload ?? '{}')
        const match = UPLOAD_PATH.exec(blob.pathname)
        if (owner.version !== 1 || !match || match[1] !== owner.workspace || blob.pathname !== owner.pathname) {
          throw new UploadRequestError(403, 'UPLOAD_DENIED', 'Upload ownership could not be verified.')
        }
        // The authenticated Python finalizer validates the private Blob again
        // and imports it. No state or credentials are sent to the client here.
      },
    })
    return Response.json(result, { headers })
  } catch (error) {
    if (error instanceof UploadRequestError) {
      return Response.json({ error: error.message, code: error.code }, { status: error.status, headers })
    }
    // SDK errors can contain private object URLs. Keep them out of responses.
    return Response.json({ error: 'Private upload could not be authorized. Please retry.', code: 'UPLOAD_UNAVAILABLE' }, { status: 503, headers })
  }
}
