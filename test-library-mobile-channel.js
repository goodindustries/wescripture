/**
 * Mobile viewport: bottom sheet channel opens with scrollable #panel-body (verse study).
 *
 * Serve repo root: python3 -m http.server 4173
 *   node test-library-mobile-channel.js
 */

const { launchBrowser } = require('./tools/puppeteer_launch.js');

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function run() {
  const browser = await launchBrowser();

  const page = await browser.newPage();
  await page.setViewport({
    width: 390,
    height: 844,
    deviceScaleFactor: 2,
    isMobile: true,
    hasTouch: true,
  });

  await page.goto('http://127.0.0.1:4173/library/index.html', {
    waitUntil: 'networkidle0',
    timeout: 60000,
  });

  await page.waitForSelector('#splash.gone', { timeout: 60000 });

  await page.evaluate(() => {
    var t = document.getElementById('toc');
    if (!t) return;
    window.tocOpen = true;
    t.classList.remove('hidden');
  });
  await page.waitForSelector('#toc:not(.hidden)', { timeout: 10000 });
  await page.waitForSelector('#toc-grid .toc-tile', { timeout: 10000 });

  await page.$eval('.toc-tile[data-action="scripture-root"]', (el) => el.scrollIntoView({ block: 'center' }));
  await page.click('.toc-tile[data-action="scripture-root"]');
  await page.waitForFunction(() => document.querySelector('#toc-subtitle')?.textContent === 'The Holy Scriptures', { timeout: 30000 });
  await page.$eval('.toc-tile[data-action="volume"][data-volume="Old Testament"]', (el) => el.scrollIntoView({ block: 'center' }));
  await page.click('.toc-tile[data-action="volume"][data-volume="Old Testament"]');
  await page.waitForFunction(() => document.querySelector('#toc-subtitle')?.textContent === 'Old Testament', { timeout: 30000 });
  await page.$eval('.toc-tile[data-action="book"][data-book="Genesis"]', (el) => el.scrollIntoView({ block: 'center' }));
  await page.click('.toc-tile[data-action="book"][data-book="Genesis"]');
  await page.waitForFunction(() => document.querySelector('#toc-subtitle')?.textContent === 'Genesis', { timeout: 30000 });
  await page.$eval('.toc-tile[data-action="chapter"][data-id="genesis_1"]', (el) => el.scrollIntoView({ block: 'center' }));
  await page.click('.toc-tile[data-action="chapter"][data-id="genesis_1"]');

  await page.waitForSelector('#ch-genesis_1', { timeout: 20000 });
  await page.click('#ch-genesis_1 .verse[id="v1"]');
  await page.waitForSelector('#channel.open', { timeout: 15000 });
  await page.waitForSelector('#panel-body[data-panel-mode="verse"]', { timeout: 15000 });

  const initial = await page.evaluate(() => {
    const list = document.querySelector('#panel-body');
    const channel = document.querySelector('#channel');
    const style = list ? getComputedStyle(list) : null;
    return {
      channelOpen: channel.classList.contains('open'),
      panelMode: list ? list.dataset.panelMode : '',
      commCards: document.querySelectorAll('#panel-body .comm-card').length,
      clientHeight: list ? list.clientHeight : 0,
      scrollHeight: list ? list.scrollHeight : 0,
      overflowY: style ? style.overflowY : '',
      touchAction: style ? style.touchAction : '',
    };
  });

  assert(initial.channelOpen, 'mobile channel did not open');
  assert(initial.panelMode === 'verse', 'expected verse study panel');
  assert(initial.commCards >= 1, 'expected commentary cards for Genesis 1:1');
  assert(initial.overflowY === 'auto', 'mobile channel panel overflow-y is not auto');

  const scrolled = await page.evaluate(() => {
    const list = document.querySelector('#panel-body');
    list.scrollTop = 0;
    list.scrollBy({ top: 400, behavior: 'instant' });
    return {
      scrollTop: list.scrollTop,
      maxScroll: list.scrollHeight - list.clientHeight,
    };
  });

  if (initial.scrollHeight > initial.clientHeight + 8) {
    assert(scrolled.maxScroll > 0, 'mobile channel max scroll is not positive');
    assert(scrolled.scrollTop > 0, 'mobile channel panel did not scroll');
  }

  console.log(JSON.stringify({ initial, scrolled }, null, 2));
  await browser.close();
}

run().catch((error) => {
  console.error(error.stack || String(error));
  process.exit(1);
});
