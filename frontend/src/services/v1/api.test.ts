import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const { upload } = vi.hoisted(() => ({ upload: vi.fn() }))
vi.mock('@vercel/blob/client', () => ({ upload }))

beforeEach(() => { vi.resetModules(); upload.mockReset() })
afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs() })

describe('ZIP transport', () => {
  it('uploads hosted ZIP bytes privately to Blob then finalizes only its path', async () => {
    vi.stubEnv('VITE_HOSTED', 'true')
    const pathname = `uploads/${'a'.repeat(64)}/${'b'.repeat(32)}.zip`
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(Response.json({ status: 'ready' }))
      .mockResolvedValueOnce(Response.json({ pathname }))
      .mockResolvedValueOnce(Response.json({ run_id: 'run', project_id: 'project' }))
    vi.stubGlobal('fetch', fetchMock)
    upload.mockResolvedValue({ pathname, url: 'https://private-store.invalid/object.zip' })
    const file = new File(['PK source fixture'], 'repository.zip') // Browser MIME can be empty.
    const { importZip } = await import('./api')
    expect(await importZip(file)).toEqual({ run_id: 'run', project_id: 'project' })
    expect(upload).toHaveBeenCalledWith(pathname, file, {
      access: 'private', handleUploadUrl: '/api/upload', contentType: 'application/zip', multipart: true,
    })
    expect(fetchMock.mock.calls[1][0]).toBe('/api/upload')
    expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual({ type: 'grepo.prepare-upload', name: file.name, size: file.size })
    expect(fetchMock.mock.calls[2][0]).toMatch(/\/api\/v1\/imports\/blob$/)
    expect(JSON.parse(fetchMock.mock.calls[2][1].body)).toEqual({ pathname, name: file.name })
    expect(fetchMock.mock.calls.every(([, init]) => !(init.body instanceof FormData))).toBe(true)
  })

  it('retains local multipart upload when hosting is disabled', async () => {
    vi.stubEnv('VITE_HOSTED', 'false')
    const fetchMock = vi.fn().mockResolvedValue(Response.json({ run_id: 'local', project_id: 'project' }))
    vi.stubGlobal('fetch', fetchMock)
    const { importZip } = await import('./api')
    await importZip(new File(['PK'], 'repository.zip'))
    expect(fetchMock.mock.calls[0][0]).toMatch(/\/api\/v1\/imports\/zip$/)
    expect(fetchMock.mock.calls[0][1].body).toBeInstanceOf(FormData)
    expect(upload).not.toHaveBeenCalled()
  })

  it('rejects oversized hosted files before contacting storage', async () => {
    vi.stubEnv('VITE_HOSTED', 'true')
    const fetchMock = vi.fn(); vi.stubGlobal('fetch', fetchMock)
    const { importZip } = await import('./api')
    await expect(importZip({ name: 'huge.zip', size: 1024 ** 3 + 1 } as File)).rejects.toMatchObject({ status: 413 })
    expect(fetchMock).not.toHaveBeenCalled()
    expect(upload).not.toHaveBeenCalled()
  })
})
