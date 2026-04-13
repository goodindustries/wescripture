/**
 * Regression: title-page Scripture volume tiles must load Church hub JPEGs.
 * Covers toc.json label "Doctrine & Covenants" vs map key "Doctrine and Covenants".
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
  await page.waitForSelector('#ch-title_page', { timeout: 30000 });

  await page.click('#ch-title_page a[data-open-shelf="scriptures"]');
  await page.waitForFunction(
    () => document.querySelector('#title-nav-title') && document.querySelector('#title-nav-title').textContent.trim() === 'Scriptures',
    { timeout: 15000 },
  );

  const rows = await page.evaluate(() => {
    return Array.from(document.querySelectorAll('#title-nav-grid button.title-nav-tile--cover[data-action="volume"]')).map(
      (btn) => {
        const img = btn.querySelector('img.title-nav-tile-cover-img');
        return {
          volume: btn.getAttribute('data-volume') || '',
          src: img ? img.getAttribute('src') || '' : '',
        };
      },
    );
  });

  assert(rows.length === 5, `expected 5 volume cover tiles, got ${rows.length}`);

  for (const [volLabel, file] of EXPECTED) {
    const row = rows.find((r) => r.volume === volLabel);
    assert(row, `missing volume tile for "${volLabel}"`);
    assert(row.src.includes(file), `volume "${volLabel}" img src should include ${file}, got: ${row.src}`);
  }

  console.log(JSON.stringify({ ok: true, url, test: 'title-nav-volume-covers' }, null, 2));
  await browser.close();
}

run().catch((err) => {
  console.error(err.stack || String(err));
  process.exit(1);
});
