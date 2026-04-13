/**
 * Title-page navigation drilldown + ?open= deep-link smoke (no left TOC).
 *
 * Serve repo root: python3 -m http.server 4173
 *   node test-title-inline-nav.js
 *
 * Override: TEST_BASE_URL=http://127.0.0.1:4173/index.html node test-title-inline-nav.js
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

  await page.waitForSelector('#ch-title_page', { timeout: 30000 });
  const tocPresent = await page.evaluate(() => !!document.getElementById('toc'));
  assert(!tocPresent, 'did not expect #toc in 2-pane mode');

  await page.click('#ch-title_page a[data-open-shelf="scriptures"]');
  await page.waitForFunction(() => document.querySelector('#title-nav-title')?.textContent?.trim() === 'Scriptures', {
    timeout: 15000,
  });

  await page.click('#title-nav-grid .title-nav-tile[data-action="volume"][data-volume="Old Testament"]');
  await page.waitForFunction(() => document.querySelector('#title-nav-title')?.textContent?.trim() === 'Books', { timeout: 15000 });

  await page.click('#title-nav-grid .title-nav-tile[data-action="book"][data-book="Genesis"]');
  await page.waitForFunction(
    () =>
      document.querySelector('#title-nav-title')?.textContent?.trim() === 'Chapters' &&
      document.querySelector('#title-nav-subtitle')?.textContent?.trim() === 'Genesis',
    { timeout: 15000 },
  );

  await page.click('#title-nav-grid .title-nav-tile[data-action="chapter"][data-id="genesis_1"]');
  await page.waitForSelector('#ch-genesis_1', { timeout: 25000 });

  // Round-trip home and drill again (basic state sanity)
  await page.click('#site-home');
  await page.waitForSelector('#ch-title_page', { timeout: 25000 });
  await page.click('#ch-title_page a[data-open-shelf="scriptures"]');
  await page.waitForFunction(() => document.querySelector('#title-nav-title')?.textContent?.trim() === 'Scriptures', {
    timeout: 15000,
  });

  const sourcesUrl = new URL(baseUrl);
  sourcesUrl.searchParams.set('open', 'general_conference');
  await page.goto(sourcesUrl.href, { waitUntil: 'networkidle0', timeout: 90000 });
  await page.waitForSelector('#splash.gone', { timeout: 90000 });

  await page.waitForFunction(() => document.getElementById('title-nav')?.hidden === false, { timeout: 20000 });
  await page.waitForFunction(
    () => document.querySelectorAll('#title-nav-grid .title-nav-tile').length > 0,
    { timeout: 20000 },
  );

  console.log(
    JSON.stringify({ ok: true, baseUrl, tests: ['title-nav-drill', 'home-roundtrip', 'open-param-sources-smoke'] }, null, 2),
  );
  await browser.close();
}

run().catch((err) => {
  console.error(err.stack || String(err));
  process.exit(1);
});
