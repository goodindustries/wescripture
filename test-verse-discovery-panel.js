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
  page.on('pageerror', (err) => {
    console.error('PAGEERROR', err && (err.stack || err.message || String(err)));
  });
  page.on('console', (msg) => {
    try {
      const type = msg.type();
      const text = msg.text();
      if (type === 'error') console.error('CONSOLE', text);
    } catch (e) {
      /* ignore */
    }
  });
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
  // Navigate by URL param to avoid coupling to sidebar TOC markup.
  await page.goto('http://127.0.0.1:4173/library/index.html?jump=Genesis%201:1', {
    waitUntil: 'networkidle0',
    timeout: 60000,
  });
  await page.waitForSelector('#ch-genesis_1', { timeout: 60000 });
  await page.$eval('#ch-genesis_1', (el) => el.scrollIntoView({ block: 'start' }));
  await page.waitForSelector('#ch-genesis_1 .verse[id="v1"]', { timeout: 15000 });

  // Click verse discovery dot (opens verse panel).
  await page.waitForSelector('#ch-genesis_1 .verse[id="v1"] .verse-num .verse-disc', { timeout: 20000 });
  await page.click('#ch-genesis_1 .verse[id="v1"] .verse-num .verse-disc');
  await page.waitForSelector('#panel-body[data-panel-mode="verse"]', { timeout: 20000 });

  const state = await page.evaluate(() => {
    const pb = document.getElementById('panel-body');
    const sections = [...pb.querySelectorAll('.panel-section')].map((e) => e.textContent.trim());
    const hasPeopleHdr = [...pb.querySelectorAll('.panel-section')].some((e) =>
      /^People\s*·\s*Places\s*·\s*Things/i.test((e.textContent || '').trim())
    );
    const donaIdx = sections.indexOf('Donaldson');
    const connIdx = sections.indexOf('Connections');
    const kwIdx = sections.indexOf('Key words');
    const crIdx = sections.indexOf('Cross References');
    const ntBad = (pb.innerText || '').includes('New Testament Commentary');
    const kwCollapsed = pb.querySelectorAll('.word-card.word-card--kw-collapsed').length;
    const commCards = pb.querySelectorAll('.comm-card').length;
    const hasLink = pb.querySelectorAll('.comm-card.has-link').length;
    const chipRow = !!pb.querySelector('.panel-verse-entities .ep-chip-row');
    let connCardCount = 0;
    let showMoreBtn = false;
    const connHdr = [...pb.querySelectorAll('.panel-section')].find((e) => (e.textContent || '').trim() === 'Connections');
    if (connHdr) {
      const wrap = connHdr.nextElementSibling;
      if (wrap && wrap.classList && wrap.classList.contains('verse-panel-cards')) {
        connCardCount = wrap.querySelectorAll('.comm-card').length;
        showMoreBtn = !!wrap.querySelector('button.word-more-btn');
      }
    }
    return { sections, hasPeopleHdr, donaIdx, connIdx, kwIdx, crIdx, ntBad, kwCollapsed, commCards, hasLink, chipRow, connCardCount, showMoreBtn };
  });

  assert(!state.hasPeopleHdr, 'standalone People · Places · Things panel-section should not appear');
  assert(state.donaIdx !== -1, 'Donaldson section missing');
  assert(state.connIdx !== -1, 'Connections section missing');
  assert(state.kwIdx === -1 || state.connIdx < state.kwIdx, 'Connections must appear before Key words');
  assert(state.crIdx === -1 || state.kwIdx === -1 || state.kwIdx < state.crIdx, 'Cross References must follow Key words when both exist');
  assert(!state.ntBad, 'Donaldson cards must not use hard-coded New Testament Commentary work line');
  assert(state.commCards > 0, 'expected at least one comm-card for Genesis 1:1');
  if (state.kwIdx !== -1) {
    assert(state.kwCollapsed > 0, 'keyword cards should use collapsed definition shell when Key words present');
  }
  if (state.connCardCount > 5) {
    assert(state.showMoreBtn, 'expected "Show 5 more" button for connections when >5');
  }

  console.log(JSON.stringify(state, null, 2));
  await browser.close();
}

run().catch((error) => {
  console.error(error.stack || String(error));
  process.exit(1);
});
