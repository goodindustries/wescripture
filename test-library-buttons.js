const { launchBrowser } = require('./tools/puppeteer_launch.js');

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function run() {
  const browser = await launchBrowser();

  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 1100, deviceScaleFactor: 1 });
  await page.evaluateOnNewDocument(() => {
    try {
      localStorage.removeItem('lds_position');
    } catch (e) { /* ignore */ }
  });
  await page.goto('http://127.0.0.1:4173/library/index.html', {
    waitUntil: 'networkidle0',
    timeout: 60000,
  });

  const results = [];
  const pass = (name, details = '') => results.push({ name, ok: true, details });

  await page.waitForSelector('#splash.gone', { timeout: 60000 });
  await page.waitForSelector('#ch-title_page', { timeout: 30000 });
  await page.waitForSelector('#ch-title_page a[data-open-shelf="scriptures"]', { timeout: 15000 });
  pass('initial load', 'reader and title page rendered');

  await page.click('#ch-title_page a[data-open-shelf="scriptures"]');
  await page.waitForFunction(() => document.getElementById('title-nav-title')?.textContent?.trim() === 'Scriptures', { timeout: 15000 });
  pass('open scriptures', 'title nav opened');

  await page.click('#title-nav-grid .title-nav-tile[data-action="volume"][data-volume="Old Testament"]');
  await page.waitForFunction(() => document.getElementById('title-nav-title')?.textContent?.trim() === 'Books', { timeout: 15000 });
  await page.click('#title-nav-grid .title-nav-tile[data-action="book"][data-book="Genesis"]');
  await page.waitForFunction(() => document.getElementById('title-nav-title')?.textContent?.trim() === 'Chapters', { timeout: 15000 });
  await page.click('#title-nav-grid .title-nav-tile[data-action="chapter"][data-id="genesis_1"]');
  await page.waitForSelector('#ch-genesis_1', { timeout: 20000 });
  pass('genesis tile', 'Genesis 1 loads from nav click');

  await page.$eval('#ch-genesis_1 .verse', (el) => el.scrollIntoView({ block: 'center' }));
  await page.click('#ch-genesis_1 .verse');
  await page.waitForFunction(() => document.querySelector('#ch-genesis_1 .verse.verse-focus'));
  pass('verse focus', 'clicking verse focuses');

  await page.click('#search-btn');
  await page.waitForFunction(() => document.querySelector('#search-panel')?.classList.contains('open'));
  await page.type('#search-input', 'light');
  await page.waitForFunction(() => document.querySelectorAll('.search-result').length > 0, { timeout: 15000 });
  await page.click('.search-result');
  await page.waitForFunction(() => !document.querySelector('#search-panel')?.classList.contains('open'), { timeout: 10000 });
  pass('search result click', 'navigates and closes search panel');

  // Allow any async UI updates to settle.
  await sleep(250);

  console.log(JSON.stringify(results, null, 2));
  await browser.close();
}

run().catch((err) => {
  console.error(err.stack || String(err));
  process.exit(1);
});
