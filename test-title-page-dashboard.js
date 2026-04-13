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
    tocPresent: !!document.getElementById('toc'),
    history: !!document.querySelector('#ch-title_page #title-recents'),
    navHidden: document.querySelector('#ch-title_page #title-nav')?.hidden,
  }));

  assert(idle.title && /WeScripture/i.test(idle.title), 'title page hero missing');
  assert(idle.tocPresent === false, 'did not expect left TOC in 2-pane mode');
  assert(idle.history === true, 'expected title page history container');
  assert(idle.navHidden === false, 'expected title nav visible by default');

  await page.waitForFunction(
    () =>
      document.querySelector('#ch-title_page #title-nav')?.hidden === false &&
      document.getElementById('title-nav-title')?.textContent?.trim() === 'Scriptures',
    { timeout: 15000 },
  );
  const volTiles = await page.$$eval('#title-nav-grid .title-nav-tile[data-action="volume"]', (els) => els.length);
  assert(volTiles >= 2, 'expected scripture volume tiles on title page');

  await page.evaluate(() => {
    jumpTo('genesis_1');
  });
  await page.waitForSelector('#ch-genesis_1', { timeout: 25000 });
  await page.click('#site-home');
  await page.waitForSelector('#ch-title_page', { timeout: 20000 });

  console.log(
    JSON.stringify(
      {
        ok: true,
        volumeTiles: volTiles,
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
