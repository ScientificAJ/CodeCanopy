import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import test from 'node:test'
import { getPayloadFromClientToken } from '@vercel/blob/client'
import upload from '../api/upload.ts'

// A synthetic credential only: token generation is local signing, no network.
process.env.BLOB_READ_WRITE_TOKEN = 'vercel_blob_rw_teststore_a_test_secret_for_local_tests'
const origin = 'https://grepo.example'
const session = 'a'.repeat(64)
const owner = createHash('sha256').update(session).digest('hex')
const pathname = `uploads/${owner}/${'b'.repeat(32)}.zip`
const request = (body, overrides = {}) => new Request(`${origin}/api/upload`, {
  method: 'POST',
  headers: { 'content-type': 'application/json', origin, cookie: `codecanopy_workspace=${session}`, ...overrides },
  body: JSON.stringify(body),
})
const prepare = { type: 'grepo.prepare-upload', name: 'repository.zip', size: 1024 ** 3 }
const token = path => ({ type: 'blob.generate-client-token', payload: { pathname: path, multipart: true, clientPayload: '{"workspace":"attacker"}' } })

test('preparation accepts the 1 GiB boundary and returns only an owned generated path', async () => {
  const response = await upload(request(prepare))
  assert.equal(response.status, 200)
  const result = await response.json()
  assert.match(result.pathname, new RegExp(`^uploads/${owner}/[a-f0-9]{32}\\.zip$`))
  assert.equal(result.maximumSizeInBytes, 1024 ** 3)
  assert.equal(response.headers.get('cache-control'), 'no-store')
  assert.equal(Object.keys(result).length, 2)
})

test('size and ZIP type validation reject invalid upload metadata', async () => {
  for (const size of [0, -1, 1.5, 1024 ** 3 + 1]) assert.equal((await upload(request({ ...prepare, size }))).status, 413)
  assert.equal((await upload(request({ ...prepare, name: 'source.exe' }))).status, 400)
})

test('a workspace cookie and exact same origin are required', async () => {
  assert.equal((await upload(request(prepare, { cookie: '' }))).status, 401)
  assert.equal((await upload(request(prepare, { cookie: 'codecanopy_workspace=invalid' }))).status, 401)
  assert.equal((await upload(request(prepare, { origin: 'https://attacker.example' }))).status, 403)
  assert.equal((await upload(request(token(pathname), { origin: '' }))).status, 403)
})

test('tokens cannot authorize another workspace or traversal path', async () => {
  for (const path of [`uploads/${'f'.repeat(64)}/${'b'.repeat(32)}.zip`, pathname.replace('uploads/', 'uploads/../'), `${pathname}/other`]) {
    assert.equal((await upload(request(token(path)))).status, 403)
  }
})

test('token grants one immutable ZIP path with trusted ownership and a 1 GiB cap', async () => {
  const response = await upload(request(token(pathname)))
  assert.equal(response.status, 200)
  const result = await response.json()
  const payload = getPayloadFromClientToken(result.clientToken)
  assert.equal(payload.pathname, pathname)
  assert.equal(payload.maximumSizeInBytes, 1024 ** 3)
  assert.equal(payload.allowOverwrite, false)
  assert.equal(payload.addRandomSuffix, false)
  assert.deepEqual(payload.allowedContentTypes, ['application/zip'])
  assert.deepEqual(JSON.parse(payload.onUploadCompleted.tokenPayload), { version: 1, workspace: owner, pathname })
  assert.equal(payload.onUploadCompleted.callbackUrl, `${origin}/api/upload`)
  assert.ok(!JSON.stringify(result).includes(process.env.BLOB_READ_WRITE_TOKEN))
})

test('unsigned completion callbacks cannot be accepted', async () => {
  const response = await upload(request({ type: 'blob.upload-completed', payload: { blob: { pathname }, tokenPayload: '{}' } }, { cookie: '', origin: '' }))
  assert.notEqual(response.status, 200)
})
