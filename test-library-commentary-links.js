const { launchBrowser } = require('./tools/puppeteer_launch.js');

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function run() {
  const browser = await launchBrowser();

  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 1100, deviceScaleFactor: 1 });
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

  await page.waitForSelector('#ch-genesis_1', { timeout: 20000 });
  await page.$eval('#ch-genesis_1', (el) => el.scrollIntoView({ block: 'start' }));
  await page.waitForFunction(() => {
    const verse = document.querySelector('#ch-genesis_1 .verse[id="v1"]');
    return !!verse && !!verse.querySelector('.ref-link');
  }, { timeout: 30000 });

  const commentaryState = await page.$eval('#ch-genesis_1 .verse[id="v1"]', (verse) => {
    const block = verse.querySelector('.lds-commentary-block, .donaldson-block, .semantic-quote');
    const style = block ? getComputedStyle(block) : null;
    return {
      hasBlock: !!block,
      borderRadius: style ? style.borderRadius : '',
      backgroundColor: style ? style.backgroundColor : '',
      firstRefText: verse.querySelector('.ref-link')?.textContent?.trim() || '',
    };
  });
  assert(commentaryState.hasBlock, 'commentary block did not load');
  assert(commentaryState.firstRefText.length > 0, 'commentary reference link did not render');

  await page.$eval('#ch-genesis_1 .verse[id="v1"] .ref-link', (el) => el.click());
  await page.waitForFunction(() => {
    const label = document.querySelector('#location-label')?.textContent || '';
    return /Genesis · 1/.test(label) || !!document.querySelector('#ch-genesis_1 .verse.verse-focus');
  }, { timeout: 15000 });

  const navState = await page.evaluate(() => ({
    location: document.querySelector('#location-label')?.textContent?.trim() || '',
    focusedVerse: document.querySelector('.verse.verse-focus')?.id || '',
  }));

  assert(navState.focusedVerse === 'v1', 'commentary reference did not focus the linked scripture verse');

  console.log(JSON.stringify({ commentaryState, navState }, null, 2));
  await browser.close();
}

run().catch((error) => {
  console.error(error.stack || String(error));
  process.exit(1);
});
