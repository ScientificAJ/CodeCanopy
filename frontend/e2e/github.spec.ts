import { test, expect } from '@playwright/test'
import { mkdirSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('live public GitHub import resolves an immutable revision', async ({ page }) => {
  test.skip(process.env.CODECANOPY_LIVE_GITHUB !== '1', 'Opt in to the external GitHub integration check')
  test.setTimeout(180000)
  const repository = process.env.CODECANOPY_TEST_REPOSITORY ?? 'https://github.com/deepseek-ai/deepseek-harness'
  const evidence = resolve(process.env.CODECANOPY_EVIDENCE_DIR ?? 'test-results/browser-evidence')
  mkdirSync(evidence, { recursive: true })
  await page.goto('/')
  await page.getByLabel('GitHub repository URL', { exact: true }).fill(repository)
  await page.getByRole('button', { name: 'Explore repository', exact: true }).click()
  await page.waitForURL(/\/overview$/, { timeout: 150000 })
  await page.getByRole('link', {name:'Explore architecture',exact:true}).click()
  await expect(page.getByRole('button', { name: 'Export HTML', exact: true })).toBeEnabled({ timeout: 40000 })
  const match = new URL(page.url()).pathname.match(/^\/p\/([^/]+)\/s\/([^/]+)/)!
  const response = await page.request.get(`http://127.0.0.1:8000/api/v1/projects/${match[1]}/snapshots/${match[2]}`)
  expect(response.ok()).toBe(true)
  const snapshot = await response.json()
  expect(snapshot.source.resolved_commit).toMatch(/^[a-f0-9]{40}$/)
  await page.getByRole('textbox', { name: 'Search repository files', exact: true }).fill('README.md')
  await page.getByRole('treeitem', { name: 'README.md', exact: true }).click()
  await expect(page.getByRole('region', { name: 'Source: README.md', exact: true })).toBeVisible()
  await page.screenshot({ path: `${evidence}/github-workspace-1672.png` })
  writeFileSync(`${evidence}/github-result.json`, JSON.stringify({ repository, snapshot, workspace: page.url() }, null, 2))
})
