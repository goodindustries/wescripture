const { launchBrowser } = require('./tools/puppeteer_launch.js');

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

const URL = 'http://127.0.0.1:4173/library/index.html';

async function run() {
  const browser = await launchBrowser();
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 1100, deviceScaleFactor: 1 });

  await page.goto(URL, { waitUntil: 'networkidle0', timeout: 90000 });
  await page.waitForSelector('#splash.gone', { timeout: 60000 });
  await page.waitForSelector('#ch-title_page', { timeout: 30000 });

  await page.click('#ch-title_page a[data-open-shelf="sources"]');
  await page.waitForFunction(() => document.getElementById('title-nav-title')?.textContent?.trim() === 'Sources', { timeout: 15000 });

  await page.click('#title-nav-grid .title-nav-tile[data-action="source-collection"][data-collection="general_conference"]');
  await page.waitForFunction(() => document.getElementById('title-nav-subtitle')?.textContent?.trim() === 'General Conference', { timeout: 15000 });

  await page.click('#title-nav-grid .title-nav-tile[data-action="source-group"][data-collection="general_conference"][data-group="general_conference:year_2007"]');
  await page.waitForFunction(() => document.getElementById('title-nav-subtitle')?.textContent?.trim() === '2007', { timeout: 15000 });

  await page.click('#title-nav-grid .title-nav-tile[data-action="source-doc"][data-doc="general_conference:general_conference_2007_10_good_better_best"]');
  await page.waitForFunction(() => !!document.querySelector('.source-doc .source-title'), { timeout: 30000 });

  await page.goto(`${URL}?open=history_of_church`, { waitUntil: 'networkidle0', timeout: 90000 });
  await page.waitForSelector('#splash.gone', { timeout: 60000 });
  await page.waitForFunction(() => document.getElementById('title-nav')?.hidden === false, { timeout: 20000 });
  await page.waitForFunction(() => document.getElementById('title-nav-subtitle')?.textContent?.trim() === 'History of the Church', { timeout: 20000 });

  console.log(JSON.stringify({ ok: true, tests: ['sources-nav', 'open-param-history'] }, null, 2));
  await browser.close();
}

run().catch((err) => {
  console.error(err.stack || String(err));
  process.exit(1);
});
