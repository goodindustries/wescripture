/**
 * Regression: the core interaction — tapping a verse opens its study material.
 *
 * The markup reflow turned each verse from a <div> into a <span>, and every
 * click handler still queried closest('div.verse'), so clicking a verse did
 * nothing at all. Nothing caught it because the other tests call
 * openVerseDiscovery() directly. This one clicks, the way a reader does.
 *
 * Found by /qa on 2026-08-03.
 */
const puppeteer = require('puppeteer');
const { openReader } = require('./helpers');

(async () => {
  const b = await puppeteer.launch({ headless: 'new' });
  const p = await b.newPage();
  await p.setViewport({ width: 1440, height: 900 });
  let bad = 0;
  const fail = m => { console.log('FAIL: ' + m); bad = 1; };

  await openReader(p);

  const target = '.scripture .verse.v[data-depth]:not([data-depth="0"])';
  const expected = await p.evaluate(sel => {
    const v = document.querySelector(sel);
    if (!v) return null;
    v.scrollIntoView({ block: 'center' });
    const m = chapterMeta[currentChapter];
    return `${m.book} ${m.label}:${v.id.replace('v', '')}`;
  }, target);
  if (!expected) return fail('no verse with study material to click');
  await new Promise(r => setTimeout(r, 500));

  // 1. Clicking the verse text.
  await p.click(target + ' .verse-text');
  await new Promise(r => setTimeout(r, 2000));
  const byText = await p.evaluate(() => ({
    open: document.getElementById('channel').classList.contains('open'),
    ref: document.querySelector('.panel-verse-ref')?.textContent,
  }));
  console.log('click verse text  ->', JSON.stringify(byText));
  if (!byText.open) fail('clicking verse text did not open the study pane');
  if (byText.ref && byText.ref !== expected) fail(`opened ${byText.ref}, expected ${expected}`);

  // 2. Clicking the verse number.
  await p.evaluate(() => closeChannel());
  await new Promise(r => setTimeout(r, 400));
  await p.click(target + ' .verse-num');
  await new Promise(r => setTimeout(r, 2000));
  const byNum = await p.evaluate(() => ({
    open: document.getElementById('channel').classList.contains('open'),
    ref: document.querySelector('.panel-verse-ref')?.textContent,
  }));
  console.log('click verse number ->', JSON.stringify(byNum));
  if (!byNum.open) fail('clicking the verse number did not open the study pane');

  // 3. The pane must be dismissable with the mouse, not just Escape.
  const close = await p.$('#ch-close');
  const box = close ? await close.boundingBox() : null;
  if (!box) fail('no visible close control on the study pane');
  else {
    await close.click();
    await new Promise(r => setTimeout(r, 500));
    const closed = await p.evaluate(() => !document.getElementById('channel').classList.contains('open'));
    if (!closed) fail('clicking the close control did not dismiss the pane');
  }

  console.log(bad ? 'RESULT: RED' : 'RESULT: GREEN');
  process.exitCode = bad;
  await b.close();
})();
