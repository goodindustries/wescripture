/**
 * Study panel intro shows Church study-summary text from .chapter-heading in the chapter block.
 *
 * Serve repo root: python3 -m http.server 4173
 *   node test-study-panel-heading.js
 */

const { launchBrowser } = require('./tools/puppeteer_launch.js');

const DEFAULT_URL = 'http://127.0.0.1:4173/library/index.html';

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

function norm(s) {
  return String(s || '')
    .replace(/\s+/g, ' ')
    .trim();
}

async function run() {
  const url = process.env.TEST_LIBRARY_URL || DEFAULT_URL;
  const browser = await launchBrowser();
  const page = await browser.newPage();
  await page.setViewport({ width: 1200, height: 900, deviceScaleFactor: 1 });
  await page.evaluateOnNewDocument(() => {
    try {
      localStorage.removeItem('lds_position');
    } catch (e) {
      /* ignore */
    }
  });

  await page.goto(url, { waitUntil: 'networkidle0', timeout: 90000 });
  await page.waitForSelector('#splash.gone', { timeout: 90000 });

  await page.evaluate(() => {
    if (typeof jumpTo !== 'function') throw new Error('jumpTo missing');
    jumpTo('genesis_1');
  });

  await page.waitForSelector('#ch-genesis_1 .chapter-heading', { timeout: 30000 });
  await page.waitForSelector('#panel-body .panel-chapter-body', { timeout: 15000 });

  const { heading, panel } = await page.evaluate(() => {
    const h = document.querySelector('#ch-genesis_1 .chapter-heading');
    const p = document.querySelector('#panel-body .panel-chapter-body');
    return {
      heading: h ? h.textContent : '',
      panel: p ? p.textContent : '',
    };
  });

  const hn = norm(heading);
  const pn = norm(panel);
  assert(hn.length > 40, 'expected chapter heading in reader');
  assert(pn.length > 40, 'expected panel intro body');
  assert(pn.includes(hn.slice(0, 50)), 'panel intro should echo chapter heading from source');

  console.log(JSON.stringify({ ok: true, url, test: 'study-panel-heading' }, null, 2));
  await browser.close();
}

run().catch((err) => {
  console.error(err.stack || String(err));
  process.exit(1);
});
