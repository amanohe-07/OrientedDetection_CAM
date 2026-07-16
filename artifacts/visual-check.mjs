import { createRequire } from 'node:module'

const require = createRequire(import.meta.url)
const { chromium } = require('C:/Users/Lenovo/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/.pnpm/playwright@1.61.1/node_modules/playwright')

const browser = await chromium.launch({
  headless: true,
  executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
})
const results = []

for (const config of [
  { name: 'desktop', width: 1440, height: 1000 },
  { name: 'mobile', width: 390, height: 844 },
]) {
  for (const route of ['/', '/detect', '/evaluate', '/analysis']) {
    const page = await browser.newPage({ viewport: { width: config.width, height: config.height } })
    const errors = []
    page.on('console', (message) => {
      if (message.type() === 'error') errors.push(`console: ${message.text()}`)
    })
    page.on('pageerror', (error) => errors.push(`page: ${error.message}`))
    await page.goto(`http://127.0.0.1:5173${route}`, { waitUntil: 'networkidle' })
    const routeName = route === '/' ? 'dashboard' : route.slice(1)
    await page.screenshot({ path: `artifacts/${config.name}-${routeName}.png`, fullPage: true })
    results.push({
      name: `${config.name}:${route}`,
      title: await page.title(),
      heading: await page.locator('h2').first().textContent(),
      horizontalOverflow: await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth),
      errors,
    })
    await page.close()
  }
}

await browser.close()
console.log(JSON.stringify(results, null, 2))
