/**
 * Corpus “Browse standard works” tiles use Church hub cover JPEGs (per testament).
 *
 * Targets the **repo-root** landing page (repo `index.html`), which embeds
 * `#corpus-root` under `#library-books-details`. This is not deployed on Netlify
 * (`publish = library` only); run locally or in CI with repo-root `http.server`.
 *
 * Serve repo root: python3 -m http.server 4173
 *   node test-corpus-book-covers.js
 *
 * Override: TEST_HOME_URL=http://127.0.0.1:PORT/index.html node test-corpus-book-covers.js
 */

const { launchBrowser } = require('./tools/puppeteer_launch.js');

const DEFAULT_LANDING = 'http://127.0.0.1:4173/index.html';

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

async function run() {
  const url = process.env.TEST_HOME_URL || DEFAULT_LANDING;
  const browser = await launchBrowser();
  const page = await browser.newPage();
  await page.setViewport({ width: 1100, height: 1400, deviceScaleFactor: 1 });

  await page.goto(url, { waitUntil: 'networkidle0', timeout: 90000 });

  await page.evaluate(() => {
    const d = document.getElementById('library-books-details');
    if (d) d.open = true;
  });

  await page.waitForSelector('#corpus-root .book-tile-cover', { timeout: 60000 });

  const bgByBlock = await page.evaluate(() => {
    const out = {};
    ['corpus-ot', 'corpus-nt', 'corpus-bom', 'corpus-dc', 'corpus-pgp'].forEach((id) => {
      const el = document.querySelector(`#${id} .book-tile-cover`);
      out[id] = el ? (el.getAttribute('style') || '') : '';
    });
    return out;
  });

  const checks = [
    ['corpus-ot', 'church_ot.jpg'],
    ['corpus-nt', 'church_nt.jpg'],
    ['corpus-bom', 'church_bom.jpg'],
    ['corpus-dc', 'church_dc.jpg'],
    ['corpus-pgp', 'church_pgp.jpg'],
  ];
  for (const [block, file] of checks) {
    const style = bgByBlock[block] || '';
    assert(style.includes(file), `expected #${block} cover style to reference ${file}, got: ${style.slice(0, 200)}`);
  }

  console.log(JSON.stringify({ ok: true, url, test: 'corpus-book-covers' }, null, 2));
  await browser.close();
}

run().catch((err) => {
  console.error(err.stack || String(err));
  process.exit(1);
});
