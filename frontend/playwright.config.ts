import { defineConfig } from '@playwright/test'
export default defineConfig({
  testDir: './e2e', timeout: 90000, fullyParallel: false, workers: 1,
  use: {baseURL: 'http://127.0.0.1:5173', viewport: {width:1672,height:941}, launchOptions:{args:['--no-sandbox']}, trace:'retain-on-failure'},
  reporter: [['list']], outputDir: 'test-results',
  webServer: [
    { command: '.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000', cwd: '../backend', url: 'http://127.0.0.1:8000/api/health', reuseExistingServer: true, timeout: 30000 },
    { command: 'npm run dev -- --host 127.0.0.1 --port 5173', url: 'http://127.0.0.1:5173', reuseExistingServer: true, timeout: 30000 },
  ],
})
