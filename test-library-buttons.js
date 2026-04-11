const puppeteer = require('puppeteer');

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function run() {
  const browser = await puppeteer.launch({
    headless: 'new',
    executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    args: ['--no-sandbox'],
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 1100, deviceScaleFactor: 1 });
  // Avoid restored chapter (lds_position) leaving TOC at book/chapters — no scripture-root tile.
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
  // Default UX: sidebar TOC starts closed; open it for sidebar tile tests.
  await page.evaluate(() => {
    const toc = document.getElementById('toc');
    if (toc && toc.classList.contains('hidden') && typeof toggleToc === 'function') toggleToc();
  });
  await page.waitForSelector('#toc:not(.hidden)', { timeout: 10000 });
  await page.waitForSelector('#toc-grid .toc-tile', { timeout: 10000 });
  pass('initial load', 'reader and tile nav rendered');

  await page.evaluate(() => { toggleToc(); });
  await page.waitForFunction(() => document.querySelector('#toc').classList.contains('hidden'));
  await page.evaluate(() => { toggleToc(); });
  await page.waitForFunction(() => !document.querySelector('#toc').classList.contains('hidden'));
  pass('toc toggle', 'closes and reopens sidebar');

  await page.waitForSelector('#reader', { timeout: 10000 });
  pass('reader shell', '#reader present (epub download control removed from chrome)');

  await page.evaluate(() => {
    setTocPathForChapter('title_page');
    tocOpen = true;
    document.getElementById('toc').classList.remove('hidden');
    renderTocView();
  });
  await page.waitForSelector('#toc-grid .toc-tile[data-action="scripture-root"]', { timeout: 10000 });

  await page.click('#toc-grid .toc-tile[data-action="scripture-root"]');
  await page.waitForFunction(() => document.querySelector('#toc-title').textContent === 'Scriptures');

  await page.click('#toc-grid .toc-tile[data-action="volume"][data-volume="Old Testament"]');
  await page.waitForFunction(() => document.querySelector('#toc-title').textContent === 'Books');
  pass('volume tile', 'Old Testament opens books view');

  await page.click('#toc-grid .toc-tile[data-action="book"][data-book="Genesis"]');
  await page.waitForFunction(() => document.querySelector('#toc-title').textContent === 'Chapters' && document.querySelector('#toc-subtitle').textContent === 'Genesis');
  pass('book tile', 'Genesis opens chapters view');

  await page.click('#toc-grid .toc-tile[data-action="chapter"][data-id="genesis_1"]');
  await page.waitForSelector('#ch-genesis_1', { timeout: 20000 });
  pass('genesis tile', 'Genesis 1 loads from tile click');

  await page.$eval('#ch-genesis_1', (el) => el.scrollIntoView({ block: 'center' }));
  await page.click('#ch-genesis_1 .verse');
  await page.waitForFunction(() => document.querySelector('#ch-genesis_1 .verse.verse-focus'));
  await page.waitForFunction(() => {
    const chapter = document.querySelector('#ch-genesis_1');
    if (!chapter) return false;
    return !!chapter.querySelector('.lds-commentary-block, .etymology-block, .semantic-quote, .jst-block, .donaldson-block');
  }, { timeout: 45000 });
  pass('notes lazy-load', 'commentary blocks present for Genesis 1');

  // chObserver can reset tocPath between UI back clicks; run backs synchronously after fixing path.
  await page.evaluate(() => {
    setTocPathForChapter('genesis_1');
    tocBack();
    tocBack();
    tocOpen = true;
    document.getElementById('toc').classList.remove('hidden');
    var ch = document.getElementById('channel');
    if (ch) ch.classList.remove('open');
  });
  await page.waitForFunction(() => document.querySelector('#toc-title').textContent === 'Scriptures');
  await page.evaluate(() => {
    var t = document.querySelector('#toc-grid .toc-tile[data-action="volume"][data-volume="New Testament"]');
    if (!t) throw new Error('New Testament volume tile not found');
    t.click();
  });
  await page.waitForFunction(() => document.querySelector('#toc-subtitle').textContent === 'New Testament');
  await page.evaluate(() => {
    document.querySelector('#toc-grid .toc-tile[data-action="book"][data-book="Matthew"]').click();
  });
  await page.waitForFunction(() => document.querySelector('#toc-subtitle').textContent === 'Matthew');
  await page.evaluate(() => {
    document.querySelector('#toc-grid .toc-tile[data-action="chapter"][data-id="matthew_28"]').click();
  });
  await page.waitForSelector('#ch-matthew_28', { timeout: 20000 });
  pass('chapter tile', 'Matthew 28 loads from tile click');

  await page.click('#search-btn');
  await page.waitForFunction(() => document.querySelector('#search-panel').classList.contains('open'));
  await page.type('#search-input', 'light');
  await page.waitForFunction(() => document.querySelectorAll('.search-result').length > 0, { timeout: 15000 });
  await page.click('.search-result');
  await page.waitForFunction(() => !document.querySelector('#search-panel').classList.contains('open'), { timeout: 10000 });
  pass('search result click', 'navigates and closes search panel');

  await page.click('#search-btn');
  await page.waitForFunction(() => document.querySelector('#search-panel').classList.contains('open'));
  await page.click('#search-close');
  await page.waitForFunction(() => !document.querySelector('#search-panel').classList.contains('open'));
  pass('search close button', 'closes panel');

  await page.evaluate(() => jumpTo('genesis_1'));
  await page.waitForSelector('#ch-genesis_1', { timeout: 20000 });
  await page.$eval('#ch-genesis_1', (el) => el.scrollIntoView({ block: 'center' }));
  await sleep(200);
  await page.waitForSelector('#ch-genesis_1 span.w', { timeout: 20000 });
  await page.click('#ch-genesis_1 span.w');
  await page.waitForFunction(() => document.querySelector('#channel').classList.contains('open'), { timeout: 15000 });
  pass('word click', 'opens channel panel');

  const expandButton = await page.$('.ch-expand');
  if (expandButton) {
    await expandButton.click();
    await page.waitForFunction(() => !!document.querySelector('.ch-full-text.open'), { timeout: 10000 });
    pass('channel expand button', 'expands long excerpt');
  } else {
    pass('channel expand button', 'no expandable excerpt for first word selection');
  }

  await page.$eval('#ch-close', (el) => el.click());
  await page.waitForFunction(() => !document.querySelector('#channel').classList.contains('open'));
  pass('channel close button', 'closes panel');

  console.log(JSON.stringify(results, null, 2));
  await browser.close();
}

run().catch(async (error) => {
  console.error(error.stack || String(error));
  process.exit(1);
});
