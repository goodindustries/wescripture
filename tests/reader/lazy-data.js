/**
 * Deferred data still arrives: the entity records and sources corpus load off
 * the critical path, so anything that reads them must still work.
 *
 * Guards the regression where person annotation keys were built before the
 * records arrived and memoised empty, leaving chapters with no people linked.
 */
const puppeteer = require('puppeteer');
(async () => {
  const b = await puppeteer.launch({ headless: 'new' });
  const p = await b.newPage();
  await p.setViewport({ width: 1440, height: 900 });
  await p.setCacheEnabled(false);
  let bad = 0; const fail = m => { console.log('FAIL: ' + m); bad = 1; };
  const errs = []; p.on('pageerror', e => errs.push(e.message));

  // Ezra 1 carries entity annotations; this week's chapter may not, which is
  // true of the pre-existing build too and says nothing about lazy loading.
  await p.goto((process.env.WS_BASE || 'http://localhost:8091') + '/library/?jump=ezra_1', { waitUntil: 'networkidle2', timeout: 60000 });
  await p.waitForFunction(() => window.currentChapter === 'ezra_1', { timeout: 30000 });
  await new Promise(r => setTimeout(r, 3000));

  // 1. Entity chips in the verse panel need full records.
  const ref = await p.evaluate(() => {
    const m = chapterMeta[currentChapter];
    const v = document.querySelector('.scripture .verse.v[data-depth]:not([data-depth="0"])');
    return `${m.book} ${m.label}:${v.id.replace('v','')}`;
  });
  await p.evaluate(r => openVerseDiscovery(r), ref);
  await p.waitForFunction(() => document.getElementById('channel').classList.contains('open'), { timeout: 20000 });
  await new Promise(r => setTimeout(r, 1200));
  const chips = await p.evaluate(() => document.querySelectorAll('.panel-verse-entities .ep-chip').length);
  console.log('entity chips in panel:', chips);
  if (!chips) fail('verse panel rendered no entity chips (full records did not arrive)');

  // 2. Chapter linkification (uses the small index only).
  const links = await p.evaluate(() => document.querySelectorAll('.scripture .verse-text span.w[data-entity], .scripture .verse-text span.w[data-place]').length);
  console.log('entity links in chapter:', links);
  if (!links) fail('no entity links rendered in the chapter');
  const pk = await p.evaluate(() => _aePersonKeys.length);
  console.log('person annotation keys:', pk);
  if (!pk) fail('person annotation keys empty — entity records never rebuilt them');

  // 3. Sources shelf still builds after lazy load.
  await p.evaluate(() => jumpTo('title_page'));
  await new Promise(r => setTimeout(r, 2000));
  await p.evaluate(() => setTitleLibraryOpen(true));
  await new Promise(r => setTimeout(r, 2500));
  const sources = await p.evaluate(() => ({
    treeSources: (typeof tocTree !== 'undefined' && tocTree.sources) ? tocTree.sources.length : 0,
    sourceMetaKeys: typeof sourceMeta !== 'undefined' ? Object.keys(sourceMeta).length : 0,
    menuRendered: document.querySelectorAll('#title-menu [data-action]').length,
  }));
  console.log('sources:', JSON.stringify(sources));
  if (!sources.treeSources) fail('sources shelf empty after lazy load');
  if (!sources.sourceMetaKeys) fail('sourceMeta not populated');

  // 4. Entity profile opens.
  const profile = await p.evaluate(async () => {
    const id = Object.values(entityIndex)[0];
    openEntityProfile(id);
    await new Promise(r => setTimeout(r, 1500));
    const pb = document.getElementById('panel-body');
    return { mode: pb?.dataset.panelMode, hasContent: (pb?.textContent || '').length > 60 };
  });
  console.log('entity profile:', JSON.stringify(profile));
  if (!profile.hasContent) fail('entity profile rendered empty');

  if (errs.length) fail('page errors: ' + errs.slice(0,3).join(' | '));
  console.log(bad ? 'RESULT: RED' : 'RESULT: GREEN');
  process.exitCode = bad;
  await b.close();
})();
