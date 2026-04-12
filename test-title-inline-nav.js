/**
 * Left Contents sidebar + ?open= deep-link smoke (title page starts with TOC collapsed).
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
  const tocHidden = await page.evaluate(() => {
    const t = document.getElementById('toc');
    return t && t.classList.contains('hidden');
  });
  assert(tocHidden, 'expected #toc collapsed on title page load');

  await page.click('#ch-title_page a[data-open-shelf="scriptures"]');
  await page.waitForFunction(() => document.querySelector('#toc-title').textContent === 'Scriptures', {
    timeout: 15000,
  });

  await page.click('#toc-grid .toc-tile[data-action="volume"][data-volume="Old Testament"]');
  await page.waitForFunction(() => document.querySelector('#toc-title').textContent === 'Books', { timeout: 15000 });

  await page.click('#toc-grid .toc-tile[data-action="book"][data-book="Genesis"]');
  await page.waitForFunction(
    () =>
      document.querySelector('#toc-title').textContent === 'Chapters' &&
      document.querySelector('#toc-subtitle').textContent === 'Genesis',
    { timeout: 15000 }
  );

  await page.click('#toc-grid .toc-tile[data-action="chapter"][data-id="genesis_1"]');
  await page.waitForSelector('#ch-genesis_1', { timeout: 25000 });

  await page.evaluate(() => {
    setTocPathForChapter('genesis_1');
    tocBack();
    tocOpen = true;
    document.getElementById('toc').classList.remove('hidden');
  });
  await page.waitForFunction(() => document.querySelector('#toc-title').textContent === 'Books', { timeout: 10000 });

  const sourcesUrl = new URL(baseUrl);
  sourcesUrl.searchParams.set('open', 'general_conference');
  await page.goto(sourcesUrl.href, { waitUntil: 'networkidle0', timeout: 90000 });
  await page.waitForSelector('#splash.gone', { timeout: 90000 });

  const tocStillVisible = await page.evaluate(() => {
    const t = document.getElementById('toc');
    return t && !t.classList.contains('hidden');
  });
  assert(tocStillVisible, 'expected #toc visible after ?open=general_conference');
  await page.waitForFunction(
    () => document.querySelector('#toc-grid') && document.querySelectorAll('#toc-grid .toc-tile').length > 0,
    { timeout: 20000 }
  );

  console.log(
    JSON.stringify({ ok: true, baseUrl, tests: ['sidebar-toc-drill', 'toc-back', 'open-param-sources-smoke'] }, null, 2)
  );
  await browser.close();
}

run().catch((err) => {
  console.error(err.stack || String(err));
  process.exit(1);
});
