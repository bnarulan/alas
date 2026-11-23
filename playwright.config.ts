import { defineConfig, devices } from '@playwright/test'

const python = process.env.ALAS_TEST_PYTHON ?? 'python'
const channel = process.env.ALAS_TEST_BROWSER_CHANNEL

export default defineConfig({
  testDir: './tests/e2e',
  workers: 1,
  use: { baseURL: 'http://127.0.0.1:4173', channel },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'] } },
    { name: 'mobile', use: { ...devices['Pixel 7'] } },
  ],
  webServer: [
    { command: '"' + python + '" -m tests.browser_api', port: 4180, timeout: 15_000 },
    {
      command: 'npm run preview -- --host 127.0.0.1 --port 4173 --strictPort',
      url: 'http://127.0.0.1:4173',
      env: { ALAS_TTS_PROXY_TARGET: 'http://127.0.0.1:4180' },
      timeout: 15_000,
    },
  ],
})
