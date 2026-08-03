const puppeteer = require('puppeteer');
const OUT = (process.env.WS_SHOTS || require('os').tmpdir());

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900 });
  await page.setCacheEnabled(false);
  const errs = [];
  page.on('pageerror', e => { errs.push(e.message); console.log('PAGEERROR:', e.message); });

  const fail = m => { console.log('FAIL: ' + m); process.exitCode = 1; };

  // ---- 1. Reader home shows this week's card ----
  await page.goto((process.env.WS_BASE || 'http://localhost:8091') + '/library/', { waitUntil: 'networkidle2', timeout: 30000 });
  await page.waitForFunction(() => {
    const el = document.getElementById('title-cfm');
    return el && !el.hidden && el.querySelectorAll('.cfm-card-chip').length > 0;
  }, { timeout: 20000 }).catch(() => fail('home Today card never appeared'));

  const card = await page.evaluate(() => {
    const el = document.getElementById('title-cfm');
    if (!el || el.hidden) return null;
    return {
      title: el.querySelector('.cfm-card-title')?.textContent,
      dates: el.querySelector('.cfm-card-dates')?.textContent,
      chips: [...el.querySelectorAll('.cfm-card-chip')].map(c => c.textContent),
      hasGo: !!el.querySelector('[data-cfm-start]'),
    };
  });
  console.log('HOME CARD:', JSON.stringify(card));
  if (!card) fail('no home card');
  else {
    if (!card.hasGo) fail('home card missing Start reading button');
    if (card.chips.length < 2) fail('home card chips too few: ' + card.chips.length);
  }
  await page.screenshot({ path: OUT + '/cfm-home-card.png' });

  // ---- 2. Start reading lands in the week, strip present ----
  await page.click('#title-cfm [data-cfm-start]');
  await page.waitForFunction(() => {
    const s = document.getElementById('cfm-strip');
    return s && !s.hidden && s.querySelectorAll('.cfm-chip').length > 0;
  }, { timeout: 20000 }).catch(() => fail('strip never appeared after Start reading'));

  const s1 = await page.evaluate(() => ({
    chapter: currentChapter,
    kicker: document.querySelector('.cfm-strip-kicker')?.textContent,
    title: document.querySelector('.cfm-strip-title')?.textContent,
    progress: document.querySelector('.cfm-strip-progress')?.textContent,
    chips: [...document.querySelectorAll('.cfm-chip')].map(c => c.textContent),
    prevDisabled: document.querySelector('[data-cfm-step="-1"]')?.disabled,
    readerHasClass: document.getElementById('reader').classList.contains('has-cfm-strip'),
  }));
  console.log('STRIP:', JSON.stringify(s1));
  if (s1.chips.length < 2) fail('strip has too few chips');
  if (!s1.readerHasClass) fail('reader missing has-cfm-strip class');
  if (!s1.prevDisabled) fail('prev should be disabled on first chapter of week');
  if (!/^1 of /.test(s1.progress || '')) fail('progress should start at 1 of N, got ' + s1.progress);

  // ---- 3. Next walks the WEEK order, not book order ----
  // Ezra 1 -> Ezra 3 (week skips Ezra 2); plain book order would give Ezra 2.
  const before = s1.chapter;
  await page.click('[data-cfm-step="1"]');
  await page.waitForFunction(prev => window.currentChapter && window.currentChapter !== prev, { timeout: 15000 }, before)
    .catch(() => fail('Next did not change chapter'));
  await new Promise(r => setTimeout(r, 800));

  const s2 = await page.evaluate(() => ({
    chapter: currentChapter,
    progress: document.querySelector('.cfm-strip-progress')?.textContent,
    activeChip: document.querySelector('.cfm-chip--active')?.textContent,
  }));
  console.log('AFTER NEXT:', JSON.stringify(s2), 'from', before);

  const weekOrder = await page.evaluate(() => {
    const w = findCfmWeekForChapter(currentChapter);
    return expandCfmWeekChapters(w).map(c => c.id);
  });
  const expected = weekOrder[weekOrder.indexOf(before) + 1];
  if (s2.chapter !== expected) fail(`Next should follow week order: expected ${expected}, got ${s2.chapter}`);
  if (!/^2 of /.test(s2.progress || '')) fail('progress should read 2 of N, got ' + s2.progress);
  await page.screenshot({ path: OUT + '/cfm-strip-after-next.png' });

  // ---- 4. Chip jump ----
  const lastId = weekOrder[weekOrder.length - 1];
  await page.click(`.cfm-chip[data-chapter-id="${lastId}"]`);
  await page.waitForFunction(id => window.currentChapter === id, { timeout: 15000 }, lastId)
    .catch(() => fail('chip jump failed'));
  const s3 = await page.evaluate(() => ({
    chapter: currentChapter,
    progress: document.querySelector('.cfm-strip-progress')?.textContent,
    nextDisabled: document.querySelector('[data-cfm-step="1"]')?.disabled,
  }));
  console.log('AFTER CHIP (last):', JSON.stringify(s3));
  if (!s3.nextDisabled) fail('next should be disabled on the last chapter of the week');

  // ---- 5. Unassigned chapter inside a week's book keeps the week on screen ----
  // Some weeks skip chapters ("Ezra 1; 3-7" leaves out Ezra 2); you still reach
  // the skipped one by reading on. Weeks that cover whole books have no such
  // chapter, so this case is derived from the live week rather than assumed.
  const skipped = await page.evaluate(() => {
    const week = findCfmWeekForChapter(currentChapter);
    const inWeek = new Set(expandCfmWeekChapters(week).map(c => c.id));
    const books = new Set(expandCfmWeekChapters(week).map(c => c.book));
    for (const id of Object.keys(chapterMeta)) {
      if (!inWeek.has(id) && books.has(chapterMeta[id].book)) return id;
    }
    return null;
  });
  if (skipped) {
    await page.evaluate(id => jumpTo(id), skipped);
    await new Promise(r => setTimeout(r, 1200));
    const s5 = await page.evaluate(() => ({
      chapter: currentChapter,
      hidden: document.getElementById('cfm-strip').hidden,
      progress: document.querySelector('.cfm-strip-progress')?.textContent,
      steps: document.querySelectorAll('.cfm-step').length,
      activeChip: document.querySelector('.cfm-chip--active')?.textContent || null,
    }));
    console.log('SKIPPED CHAPTER (' + skipped + '):', JSON.stringify(s5));
    if (s5.hidden) fail('strip should stay while reading an unassigned chapter of a week book');
    if (s5.activeChip) fail('no chip should be active on an unassigned chapter');
    if (s5.steps !== 0) fail('step buttons should be absent with no position in the list');
  } else {
    console.log('note: this week covers whole books, no skipped-chapter case to test');
  }

  // ---- 6. Strip hides on a chapter no week assigns ----
  const outside = await page.evaluate(() => {
    for (const id of Object.keys(chapterMeta)) {
      if (!findCfmWeekForChapter(id)) return id;
    }
    return null;
  });
  if (!outside) return fail('every chapter belongs to a week; cannot test the hidden case');
  await page.evaluate(id => jumpTo(id), outside);
  // Jumping prepends the chapter while earlier ones stay loaded, so the
  // position observer can fire once more as the scroll settles. Wait for the
  // settled state instead of guessing a delay.
  await page.waitForFunction(id => window.currentChapter === id
    && document.getElementById('cfm-strip').hidden, { timeout: 15000 }, outside)
    .catch(() => {});
  const s4 = await page.evaluate(() => ({
    chapter: currentChapter,
    hidden: document.getElementById('cfm-strip').hidden,
    readerHasClass: document.getElementById('reader').classList.contains('has-cfm-strip'),
  }));
  console.log('OUTSIDE WEEK (' + outside + '):', JSON.stringify(s4));
  if (!s4.hidden) fail('strip should hide on a chapter no week assigns');
  if (s4.readerHasClass) fail('has-cfm-strip should be removed when strip hides');

  if (errs.length) fail('page errors: ' + errs.join(' | '));
  console.log(process.exitCode ? 'RESULT: RED' : 'RESULT: GREEN');
  await browser.close();
})();
