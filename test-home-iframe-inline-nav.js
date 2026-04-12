/**
 * Title page: "Scriptures" opens the left Contents sidebar (standard works volumes).
 *
 * Serve repo root: python3 -m http.server 4173
 *   node test-home-iframe-inline-nav.js
 *
 * TEST_HOME_URL default: http://127.0.0.1:4173/library/index.html
 */

const fs = require('fs');
const puppeteer = require('puppeteer');

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

const DEFAULT_HOME = 'http://127.0.0.1:4173/library/index.html';

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
  const url = process.env.TEST_HOME_URL || DEFAULT_HOME;
  const browser = await launchBrowser();
  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 1100, deviceScaleFactor: 1 });

  await page.goto(url, { waitUntil: 'networkidle0', timeout: 90000 });
  await page.waitForSelector('#splash.gone', { timeout: 90000 });
  await page.waitForSelector('#ch-title_page', { timeout: 30000 });
  await page.waitForSelector('#ch-title_page a[data-open-shelf="scriptures"]', { timeout: 15000 });

  await page.click('#ch-title_page a[data-open-shelf="scriptures"]');
  await page.waitForFunction(
    () => document.getElementById('toc-title')?.textContent?.trim() === 'Scriptures',
    { timeout: 20000 }
  );

  const tocVisible = await page.evaluate(() => {
    const t = document.getElementById('toc');
    return t && !t.classList.contains('hidden');
  });
  assert(tocVisible, 'expected #toc visible after opening Scriptures');
  await page.waitForSelector('#toc-grid .toc-tile[data-action="volume"]', { timeout: 25000 });

  console.log(JSON.stringify({ ok: true, url, test: 'title-page-scriptures-opens-toc' }, null, 2));
  await browser.close();
}

run().catch((err) => {
  console.error(err.stack || String(err));
  process.exit(1);
});
