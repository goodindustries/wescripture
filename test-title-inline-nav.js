/**
 * Title-page inline browse panel (scriptures + sources smoke).
 *
 * Serve the repo root so /library/index.html is available:
 *   cd /path/to/wescripture && python3 -m http.server 4173
 *
 * Then:
 *   node test-title-inline-nav.js
 *
 * Override URL: TEST_BASE_URL=http://127.0.0.1:4173/index.html node test-title-inline-nav.js
 * (if you serve only `library/` as docroot, use that origin + /index.html)
 *
 * Chrome: set PUPPETEER_EXECUTABLE_PATH if not using bundled Chromium.
 */

const fs = require('fs');
const puppeteer = require('puppeteer');

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

const DEFAULT_BASE = 'http://127.0.0.1:4173/library/index.html';

function launchBrowser() {
  const opts = {
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  };
  const macChrome = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
  if (process.env.PUPPETEER_EXECUTABLE_PATH) {
    opts.executablePath = process.env.PUPPETEER_EXECUTABLE_PATH;
  } else if (fs.existsSync(macChrome)) {
    opts.executablePath = macChrome;
  }
  return puppeteer.launch(opts);
}

async function run() {
  const baseUrl = process.env.TEST_BASE_URL || DEFAULT_BASE;
  const browser = await launchBrowser();
  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 900, deviceScaleFactor: 1 });

  await page.goto(baseUrl, { waitUntil: 'networkidle0', timeout: 90000 });
  await page.waitForSelector('#splash.gone', { timeout: 90000 });

  const tocHidden = await page.evaluate(() => {
    const t = document.getElementById('toc');
    return t && t.classList.contains('hidden');
  });
  assert(tocHidden, 'expected #toc hidden on load (sidebar not auto-open)');

  await page.waitForSelector('#ch-title_page', { timeout: 30000 });

  await page.click('#ch-title_page [data-open-shelf="scriptures"]');
  await page.waitForFunction(
    () =>
      document.querySelectorAll('#ch-title_page #title-inline-nav-grid .title-inline-tile[data-action="volume"]')
        .length > 0,
    { timeout: 20000 }
  );

  await page.click(
    '#ch-title_page #title-inline-nav-grid .title-inline-tile[data-action="volume"][data-volume="Old Testament"]'
  );
  await page.waitForFunction(
    () =>
      document.querySelectorAll('#ch-title_page #title-inline-nav-grid .title-inline-tile[data-action="book"]')
        .length > 0,
    { timeout: 15000 }
  );

  await page.click(
    '#ch-title_page #title-inline-nav-grid .title-inline-tile[data-action="book"][data-book="Genesis"]'
  );
  await page.waitForFunction(
    () =>
      document.querySelectorAll('#ch-title_page #title-inline-nav-grid .title-inline-tile[data-action="chapter"]')
        .length > 0,
    { timeout: 15000 }
  );

  await page.click(
    '#ch-title_page #title-inline-nav-grid .title-inline-tile[data-action="chapter"][data-chapter-id="genesis_1"]'
  );
  await page.waitForSelector('#ch-genesis_1', { timeout: 25000 });

  await page.click('#ch-title_page #title-inline-nav-back');
  await page.waitForFunction(
    () => document.querySelector('#ch-title_page #title-inline-nav-title').textContent.trim() === 'Books',
    { timeout: 10000 }
  );

  const sourcesUrl = new URL(baseUrl);
  sourcesUrl.searchParams.set('open', 'general_conference');
  await page.goto(sourcesUrl.href, { waitUntil: 'networkidle0', timeout: 90000 });
  await page.waitForSelector('#splash.gone', { timeout: 90000 });
  await page.waitForFunction(
    () =>
      document.querySelectorAll('#ch-title_page #title-inline-nav-grid .title-inline-tile').length > 0,
    { timeout: 20000 }
  );
  const tocStillClosed = await page.evaluate(() => {
    const t = document.getElementById('toc');
    return t && t.classList.contains('hidden');
  });
  assert(tocStillClosed, 'expected #toc still hidden after ?open=general_conference');

  console.log(JSON.stringify({ ok: true, baseUrl, tests: ['inline-scriptures-drill', 'back-button', 'sources-open-smoke'] }, null, 2));
  await browser.close();
}

run().catch((err) => {
  console.error(err.stack || String(err));
  process.exit(1);
});
