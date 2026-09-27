import { test, expect } from '@playwright/test'
import { execFileSync } from 'node:child_process'
import { resolve } from 'node:path'

test('loader reports actual progress and supports reduced motion and cancellation', async ({page}) => {
  let cancelled = false
  await page.route('**/api/v1/imports/github', route => route.fulfill({status:202,json:{run_id:'loader-run',project_id:'loader-project'}}))
  await page.route('**/api/v1/runs/loader-run', route => route.fulfill({json:{id:'loader-run',project_id:'loader-project',status:cancelled?'cancelled':'running',stage:'inventory',stage_progress:0.42,diagnostics:[],started_at:new Date().toISOString()}}))
  await page.route('**/api/v1/runs/loader-run/cancel', route => {cancelled=true;return route.fulfill({status:202,json:{id:'loader-run',status:'cancelled'}})})
  await page.goto('/')
  await page.getByLabel('GitHub repository URL',{exact:true}).fill('https://github.com/example/repo')
  await page.getByRole('button',{name:'Explore repository',exact:true}).click()
  await expect(page.getByRole('progressbar',{name:'Files inspected'})).toHaveAttribute('aria-valuenow','42')
  await page.setViewportSize({width:390,height:844})
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await expect(page.getByRole('button',{name:'Cancel import'})).toBeInViewport()
  await page.emulateMedia({reducedMotion:'reduce'})
  await expect(page.locator('.gecko-scout')).toHaveCSS('animation-name','none')
  await page.screenshot({path:resolve(process.env.CODECANOPY_EVIDENCE_DIR ?? 'test-results/browser-evidence','gecko-loader-mobile.png')})
  await page.getByRole('button',{name:'Cancel import'}).click()
  await expect(page.getByText('Import cancelled. You can start another import.')).toBeVisible()
})

test('cited chat opens deep source and supports more than five conversation turns', async ({page}) => {
  const fixture=resolve('node_modules/.cache/grepo-e2e/deep-chat.zip')
  execFileSync('python3',['-c',`from pathlib import Path
import zipfile,sys
Path(sys.argv[1]).parent.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(sys.argv[1],'w') as z:
 z.writestr('main.py', '# padding\\n'*700+'def renew_lease(token):\\n    return token + "renewed"\\n')
`,fixture])
  await page.goto('/')
  await page.getByRole('button',{name:'Upload ZIP',exact:true}).click()
  await page.getByLabel('Repository ZIP archive').setInputFiles(fixture)
  await page.getByRole('button',{name:'Explore repository',exact:true}).click()
  await page.waitForURL(/\/overview$/)
  const base=page.url().replace(/\/overview$/,'')
  const ids=new URL(base).pathname.match(/\/p\/([^/]+)\/s\/([^/]+)/)!
  const inventory=await (await page.request.get(`http://127.0.0.1:8000/api/v1/projects/${ids[1]}/snapshots/${ids[2]}/files`)).json()
  const file=inventory.files.find((f:{path:string})=>f.path==='main.py')
  // Browser behavior is deterministic here; real-provider retrieval is checked separately.
  await page.route('**/chat', route => {
    const body=route.request().postDataJSON()
    expect(body.history.length).toBeLessThanOrEqual(10)
    return route.fulfill({json:{answer:'The function renews the token [S1].',context_hint:'Searched 1 of 1 eligible files.',sources:[{id:'S1',file_id:file.id,path:'main.py',line_start:701,line_end:702}],limitations:[]}})
  })
  await page.goto(base+'/ask')
  await page.getByRole('button',{name:'Open GREPO',exact:true}).click()
  for(let i=0;i<7;i++) {
    await page.getByRole('textbox',{name:'Chat input'}).fill(`Explain renew_lease, turn ${i}`)
    await page.getByRole('button',{name:'Ask',exact:true}).click()
    await expect(page.getByRole('textbox',{name:'Chat input'})).toBeEnabled()
    await expect(page.locator('.chat-sources button')).toHaveCount(i+1)
  }
  await page.locator('.chat-sources button').last().click()
  await expect(page.getByRole('region',{name:'Source: main.py'})).toBeVisible()
  await expect(page.getByText('def renew_lease(token):',{exact:true})).toBeVisible()
  await page.screenshot({path:resolve(process.env.CODECANOPY_EVIDENCE_DIR ?? 'test-results/browser-evidence','deep-source-citation.png')})
})
