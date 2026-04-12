/**
 * Verse discovery channel: commentary-first layout, inline entity chips, no legacy section header.
 *
 * Serve repo root: python3 -m http.server 4173
 *   node test-verse-discovery-panel.js
 */

const { launchBrowser } = require('./tools/puppeteer_launch.js');

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function run() {
  const browser = await launchBrowser();
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 1100, deviceScaleFactor: 1 });
  await page.evaluateOnNewDocument(() => {
    try {
      localStorage.removeItem('lds_position');
    } catch (e) {
      /* ignore */
    }
  });
  await page.goto('http://127.0.0.1:4173/library/index.html', {
    waitUntil: 'networkidle0',
    timeout: 60000,
  });

  await page.waitForSelector('#splash.gone', { timeout: 60000 });
  await page.waitForSelector('#toc-grid .toc-tile', { timeout: 10000 });

  await page.click('.toc-tile[data-action="scripture-root"]');
  await page.waitForFunction(() => document.querySelector('#toc-subtitle')?.textContent === 'The Holy Scriptures');
  await page.click('.toc-tile[data-action="volume"][data-volume="Old Testament"]');
  await page.waitForFunction(() => document.querySelector('#toc-subtitle')?.textContent === 'Old Testament');
  await page.click('.toc-tile[data-action="book"][data-book="Genesis"]');
  await page.waitForFunction(() => document.querySelector('#toc-subtitle')?.textContent === 'Genesis');
  await page.click('.toc-tile[data-action="chapter"][data-id="genesis_1"]');

  await page.waitForSelector('#ch-genesis_1', { timeout: 20000 });
  await page.$eval('#ch-genesis_1', (el) => el.scrollIntoView({ block: 'start' }));
  await page.waitForSelector('#ch-genesis_1 .verse[id="v1"]', { timeout: 15000 });

  await page.click('#ch-genesis_1 .verse[id="v1"]');
  await page.waitForSelector('#panel-body[data-panel-mode="verse"]', { timeout: 15000 });

  const state = await page.evaluate(() => {
    const pb = document.getElementById('panel-body');
    const sections = [...pb.querySelectorAll('.panel-section')].map((e) => e.textContent.trim());
    const hasPeopleHdr = [...pb.querySelectorAll('.panel-section')].some((e) =>
      /^People\s*·\s*Places\s*·\s*Things/i.test((e.textContent || '').trim())
    );
    const commIdx = sections.indexOf('Commentary');
    const kwIdx = sections.indexOf('Key words');
    const crIdx = sections.indexOf('Cross References');
    const ntBad = (pb.innerText || '').includes('New Testament Commentary');
    const kwCollapsed = pb.querySelectorAll('.word-card.word-card--kw-collapsed').length;
    const hasComm = pb.querySelectorAll('.comm-card').length;
    const hasLink = pb.querySelectorAll('.comm-card.has-link').length;
    const chipRow = !!pb.querySelector('.panel-verse-entities .ep-chip-row');
    return { sections, hasPeopleHdr, commIdx, kwIdx, crIdx, ntBad, kwCollapsed, hasComm, hasLink, chipRow };
  });

  assert(!state.hasPeopleHdr, 'standalone People · Places · Things panel-section should not appear');
  assert(state.commIdx !== -1, 'Commentary section missing');
  assert(state.kwIdx === -1 || state.commIdx < state.kwIdx, 'Commentary must appear before Key words');
  assert(state.crIdx === -1 || state.kwIdx === -1 || state.kwIdx < state.crIdx, 'Cross References must follow Key words when both exist');
  assert(!state.ntBad, 'Donaldson cards must not use hard-coded New Testament Commentary work line');
  assert(state.hasComm > 0, 'expected at least one commentary card for Genesis 1:1');
  if (state.kwIdx !== -1) {
    assert(state.kwCollapsed > 0, 'keyword cards should use collapsed definition shell when Key words present');
  }

  console.log(JSON.stringify(state, null, 2));
  await browser.close();
}

run().catch((error) => {
  console.error(error.stack || String(error));
  process.exit(1);
});
