import { afterEach, expect, it, vi } from 'vitest'

afterEach(() => {vi.unstubAllEnvs(); vi.resetModules()})
it.each([{hosted:'true',format:'webp'},{hosted:'false',format:'png'}])('uses $format mascot delivery for hosted=$hosted', async ({hosted,format}) => {
  vi.stubEnv('VITE_HOSTED',hosted); vi.resetModules()
  const {brandLogo} = await import('./assets')
  expect(brandLogo).toBe(`/codecanopy-logo.${format}`)
})
