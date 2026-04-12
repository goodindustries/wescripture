/**
 * Regression: reader sidebar Scripture volume tiles must load Church hub JPEGs.
 * Covers toc.json label "Doctrine & Covenants" vs map key "Doctrine and Covenants".
 *
 * Serve repo root: python3 -m http.server 4173
 *   node test-toc-volume-covers.js
 *
 * TEST_LIBRARY_URL default: http://127.0.0.1:4173/library/index.html
 */

const { launchBrowser } = require('./tools/puppeteer_launch.js');

const DEFAULT_URL = 'http://127.0.0.1:4173/library/index.html';

const EXPECTED = [
  ['Old Testament', 'church_ot.jpg'],
  ['New Testament', 'church_nt.jpg'],
  ['Book of Mormon', 'church_bom.jpg'],
  ['Doctrine & Covenants', 'church_dc.jpg'],
  ['Pearl of Great Price', 'church_pgp.jpg'],
];

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

async function run() {
  const url = process.env.TEST_LIBRARY_URL || DEFAULT_URL;
  const browser = await launchBrowser();
  const page = await browser.newPage();
  await page.setViewport({ width: 1200, height: 900, deviceScaleFactor: 1 });
  await page.evaluateOnNewDocument(() => {
    try {
      localStorage.removeItem('lds_position');
    } catch (e) { /* ignore */ }
  });

  await page.goto(url, { waitUntil: 'networkidle0', timeout: 90000 });
  await page.waitForSelector('#splash.gone', { timeout: 60000 });

  await page.evaluate(() => {
    if (typeof setTocPathForChapter !== 'function' || typeof renderTocView !== 'function') {
      throw new Error('reader TOC API missing');
    }
    setTocPathForChapter('title_page');
    if (typeof tocOpen !== 'undefined') tocOpen = true;
    const toc = document.getElementById('toc');
    if (toc) toc.classList.remove('hidden');
    renderTocView();
  });

  await page.waitForSelector('#toc-grid .toc-tile[data-action="scripture-root"]', { timeout: 15000 });
  await page.click('#toc-grid .toc-tile[data-action="scripture-root"]');
  await page.waitForFunction(
    () => document.querySelector('#toc-title') && document.querySelector('#toc-title').textContent === 'Scriptures',
    { timeout: 15000 }
  );

  const rows = await page.evaluate(() => {
    return Array.from(document.querySelectorAll('#toc-grid button.toc-tile--cover[data-action="volume"]')).map(
      (btn) => {
        const img = btn.querySelector('img.toc-tile-cover-img');
        return {
          volume: btn.getAttribute('data-volume') || '',
          src: img ? img.getAttribute('src') || '' : '',
        };
      }
    );
  });

  assert(rows.length === 5, `expected 5 volume cover tiles, got ${rows.length}`);

  for (const [volLabel, file] of EXPECTED) {
    const row = rows.find((r) => r.volume === volLabel);
    assert(row, `missing volume tile for "${volLabel}"`);
    assert(
      row.src.includes(file),
      `volume "${volLabel}" img src should include ${file}, got: ${row.src}`
    );
  }

  console.log(JSON.stringify({ ok: true, url, test: 'toc-volume-covers' }, null, 2));
  await browser.close();
}

run().catch((err) => {
  console.error(err.stack || String(err));
  process.exit(1);
});
