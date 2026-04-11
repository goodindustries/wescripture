/**
 * Home page embeds index.html in #home-reader; shelf clicks postMessage → inline title nav.
 *
 * Serve repo root: python3 -m http.server 4173
 *   node test-home-iframe-inline-nav.js
 *
 * TEST_BASE_URL default: http://127.0.0.1:4173/library/home.html
 */

const fs = require('fs');
const puppeteer = require('puppeteer');

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

const DEFAULT_HOME = 'http://127.0.0.1:4173/library/home.html';

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

  await page.waitForSelector('#home-reader', { timeout: 30000 });
  const frameEl = await page.$('#home-reader');
  assert(frameEl, '#home-reader iframe missing');
  const frame = await frameEl.contentFrame();
  assert(frame, 'iframe contentFrame unavailable');
  await frame.waitForFunction(() => document.getElementById('splash')?.classList.contains('gone'), {
    timeout: 90000,
  });
  await frame.waitForSelector('#ch-title_page', { timeout: 30000 });

  await page.click('#library-shelf a.shelf-tile[data-collection="scriptures"]');

  await frame.waitForFunction(
    () =>
      document.querySelectorAll('#ch-title_page #title-inline-nav-grid .title-inline-tile[data-action="volume"]')
        .length > 0,
    { timeout: 25000 }
  );

  const iframeTocHidden = await frame.evaluate(() => {
    const t = document.getElementById('toc');
    return t && t.classList.contains('hidden');
  });
  assert(iframeTocHidden, 'expected reader #toc hidden in iframe after shelf click');

  console.log(JSON.stringify({ ok: true, url, test: 'home-iframe-scriptures-inline-nav' }, null, 2));
  await browser.close();
}

run().catch((err) => {
  console.error(err.stack || String(err));
  process.exit(1);
});
