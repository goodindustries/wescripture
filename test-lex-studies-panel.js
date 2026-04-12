/**
 * Pre-generated *_lexstudies.json: NT keyword card shows Greek when confidence is high;
 * BoM shows English study without a Greek subline.
 *
 * Serve repo root: python3 -m http.server 4173
 *   node test-lex-studies-panel.js
 *
 * Override: TEST_BASE_URL=http://127.0.0.1:4173/library/index.html node test-lex-studies-panel.js
 */

const fs = require('fs');
const puppeteer = require('puppeteer');

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

const DEFAULT_BASE = 'http://127.0.0.1:4173/library/index.html';

function launchBrowser() {
  const opts = {
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  };
  const macChrome = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
  if (process.env.PUPPETEER_EXECUTABLE_PATH) {
    opts.executablePath = process.env.PUPPETEER_EXECUTABLE_PATH;
  } else if (fs.existsSync(macChrome)) {
    opts.executablePath = macChrome;
  }
  return puppeteer.launch(opts);
}

async function run() {
  const baseUrl = process.env.TEST_BASE_URL || DEFAULT_BASE;
  const browser = await launchBrowser();
  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 900, deviceScaleFactor: 1 });

  await page.goto(baseUrl, { waitUntil: 'networkidle0', timeout: 90000 });
  await page.waitForSelector('#splash.gone', { timeout: 90000 });

  await page.evaluate(() => {
    jumpTo('john_3', 3);
  });
  await page.waitForSelector('#ch-john_3 div.verse#v3', { timeout: 60000 });
  await page.waitForFunction(() => typeof currentChapter === 'string' && currentChapter === 'john_3', {
    timeout: 60000,
  });
  await page.click('#ch-john_3 div.verse#v3 .verse-num');
  await page.waitForSelector('#channel.open #panel-body[data-panel-mode="verse"]', { timeout: 20000 });

  const nt = await page.evaluate(() => {
    const panel = document.getElementById('panel-body');
    const greekLine = panel && panel.querySelector('.word-original[lang="el"]');
    const kwText = panel && panel.querySelector('.word-kw-text');
    return {
      greek: greekLine ? greekLine.textContent.trim() : '',
      studySnippet: kwText ? kwText.textContent.trim().slice(0, 400) : '',
    };
  });
  assert(nt.greek.includes('βασιλεία'), `expected Greek surface/lemma in panel, got: ${JSON.stringify(nt.greek)}`);
  assert(
    nt.studySnippet.toLowerCase().includes('kingdom'),
    `expected study body to mention kingdom, got: ${JSON.stringify(nt.studySnippet.slice(0, 120))}`
  );

  await page.evaluate(() => {
    jumpTo('1_nephi_1', 1);
  });
  await page.waitForSelector('#ch-1_nephi_1 div.verse#v1', { timeout: 60000 });
  await page.waitForFunction(() => typeof currentChapter === 'string' && currentChapter === '1_nephi_1', {
    timeout: 60000,
  });
  await page.click('#ch-1_nephi_1 div.verse#v1 .verse-num');
  await page.waitForSelector('#channel.open #panel-body[data-panel-mode="verse"]', { timeout: 20000 });

  const bom = await page.evaluate(() => {
    const panel = document.getElementById('panel-body');
    const greekLines = panel ? panel.querySelectorAll('.word-original[lang="el"]') : [];
    const kwBlocks = panel ? panel.querySelectorAll('.word-kw-text') : [];
    const texts = [];
    kwBlocks.forEach((n) => texts.push(n.textContent.trim().slice(0, 200)));
    return { greekCount: greekLines.length, kwPreviews: texts };
  });
  assert(bom.greekCount === 0, `BoM verse panel should not show lang=el Greek line; count=${bom.greekCount}`);
  assert(
    bom.kwPreviews.some((t) => /restoration-era volume|no public verse-token|stays in english/i.test(t)),
    `expected English-only honesty cue in a keyword card, got: ${JSON.stringify(bom.kwPreviews)}`
  );

  console.log(
    JSON.stringify(
      { ok: true, baseUrl, tests: ['nt-lex-greek-line', 'bom-no-fake-greek', 'bom-english-cue'] },
      null,
      2
    )
  );
  await browser.close();
}

run().catch((err) => {
  console.error(err.stack || String(err));
  process.exit(1);
});
