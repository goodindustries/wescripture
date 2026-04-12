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
    tocHidden: document.getElementById('toc')?.classList.contains('hidden'),
    inlineNav: document.querySelector('#ch-title_page #title-inline-nav'),
  }));

  assert(idle.title && /WeScripture/i.test(idle.title), 'title page hero missing');
  assert(idle.tocHidden === true, 'expected title page to start with Contents sidebar collapsed');
  assert(!idle.inlineNav, 'title page should not embed duplicate inline browse panel');

  await page.click('#ch-title_page a[data-open-shelf="scriptures"]');
  await page.waitForFunction(
    () =>
      !document.getElementById('toc')?.classList.contains('hidden') &&
      document.getElementById('toc-title')?.textContent?.trim() === 'Scriptures',
    { timeout: 15000 },
  );
  const volTiles = await page.$$eval('#toc-grid .toc-tile[data-action="volume"]', (els) => els.length);
  assert(volTiles >= 2, 'expected scripture volume tiles in left TOC');

  await page.evaluate(() => {
    jumpTo('genesis_1');
  });
  await page.waitForSelector('#ch-genesis_1', { timeout: 25000 });
  await page.click('#site-home');
  await page.waitForFunction(
    () => document.getElementById('toc')?.classList.contains('hidden') === true,
    { timeout: 20000 },
  );

  console.log(
    JSON.stringify(
      {
        ok: true,
        idleTocHidden: idle.tocHidden,
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
