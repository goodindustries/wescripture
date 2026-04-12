const { launchBrowser } = require('./tools/puppeteer_launch.js');

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function run() {
  const browser = await launchBrowser();
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 1400, deviceScaleFactor: 1 });

  await page.evaluateOnNewDocument(() => {
    try {
      localStorage.removeItem('lds_position');
    } catch (e) {
      /* ignore */
    }
  });

  await page.goto('http://127.0.0.1:4173/library/index.html', {
    waitUntil: 'networkidle0',
    timeout: 90000,
  });

  await page.waitForSelector('#splash.gone', { timeout: 90000 });
  await page.waitForSelector('#ch-title_page', { timeout: 30000 });

  const idle = await page.evaluate(() => ({
    title: document.querySelector('#ch-title_page .dashboard-title')?.textContent?.trim(),
    navTitle: document.querySelector('#ch-title_page #title-inline-nav-title')?.textContent?.trim(),
    placeholder: document.querySelector('#ch-title_page #title-inline-nav-grid .title-inline-placeholder')?.textContent?.trim(),
  }));

  assert(idle.title && /WeScripture/i.test(idle.title), 'title page hero missing');
  assert(idle.navTitle === 'Library browser', 'expected idle inline nav title');
  assert(idle.placeholder && idle.placeholder.length > 10, 'expected idle inline nav placeholder');

  await page.click('#ch-title_page a[data-open-shelf="scriptures"]');
  await page.waitForFunction(
    () => document.querySelector('#ch-title_page #title-inline-nav-title')?.textContent === 'Scriptures',
    { timeout: 15000 },
  );
  const volTiles = await page.$$eval(
    '#ch-title_page #title-inline-nav-grid .title-inline-tile[data-action="volume"]',
    (els) => els.length,
  );
  assert(volTiles >= 2, 'expected scripture volume tiles on title page');

  const dash = await page.evaluate(async () => {
    const r = await fetch('./source-dashboard.json');
    if (!r.ok) return null;
    return r.json();
  });
  assert(dash && dash.totals && typeof dash.totals.docs === 'number', 'source-dashboard.json totals missing');

  console.log(
    JSON.stringify(
      {
        ok: true,
        idleNavTitle: idle.navTitle,
        volumeTiles: volTiles,
        docsMetric: dash.totals.docs,
      },
      null,
      2,
    ),
  );
  await browser.close();
}

run().catch((error) => {
  console.error(error.stack || String(error));
  process.exit(1);
});
