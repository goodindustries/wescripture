const puppeteer = require('puppeteer');
(async () => {
  const b = await puppeteer.launch({ headless: 'new' });
  const p = await b.newPage();
  await p.setViewport({ width: 1440, height: 900 });
  await p.setCacheEnabled(false);
  let bad = 0; const fail = m => { console.log('FAIL: ' + m); bad = 1; };

  await p.goto((process.env.WS_BASE || 'http://localhost:8091') + '/library/?today=1', { waitUntil: 'networkidle2' });
  await p.waitForFunction(() => window.currentChapter, { timeout: 20000 });
  await new Promise(r => setTimeout(r, 1200));
  await p.evaluate(() => openVerseDiscovery('Ezra 1:2'));
  await p.waitForSelector('#panel-body .vp-tabs', { timeout: 15000 });
  await new Promise(r => setTimeout(r, 800));

  const tabs = await p.evaluate(() => [...document.querySelectorAll('.vp-tab')].map(t => t.dataset.pane));
  console.log('TABS:', JSON.stringify(tabs));
  if (!tabs.includes('translations')) fail('no Translations tab');
  if (tabs.join(',') !== 'refs,commentary,words,translations') fail('tab order wrong: ' + tabs.join(','));

  await p.click('.vp-tab[data-pane="translations"]');
  await new Promise(r => setTimeout(r, 300));
  const pane = await p.evaluate(() => {
    const vis = [...document.querySelectorAll('.vp-pane')].filter(x => getComputedStyle(x).display !== 'none').map(x => x.dataset.pane);
    const rows = [...document.querySelectorAll('.tr-row')].map(r => ({
      label: r.querySelector('.tr-label')?.textContent.trim(),
      text: r.querySelector('.tr-text')?.textContent.trim().slice(0, 60),
      base: r.classList.contains('tr-row--base'),
    }));
    return { vis, rows };
  });
  console.log('VISIBLE PANE:', pane.vis.join(','));
  console.log('ROWS:', JSON.stringify(pane.rows, null, 1));
  if (pane.vis.join(',') !== 'translations') fail('translations pane not shown on click');
  if (pane.rows.length !== 3) fail('expected KJV + WEB + ASV rows, got ' + pane.rows.length);
  if (!pane.rows[0]?.base) fail('KJV should be the base row and come first');
  const texts = pane.rows.map(r => r.text);
  if (new Set(texts).size !== texts.length) fail('translation rows are duplicates: ' + JSON.stringify(texts));

  // Non-Bible volumes must not sprout a Translations tab.
  await p.evaluate(() => jumpTo('1_nephi_1'));
  await p.waitForFunction(() => window.currentChapter === '1_nephi_1', { timeout: 20000 }).catch(() => {});
  await new Promise(r => setTimeout(r, 1500));
  await p.evaluate(() => openVerseDiscovery('1 Nephi 1:1'));
  await new Promise(r => setTimeout(r, 1800));
  const bomTabs = await p.evaluate(() => [...document.querySelectorAll('.vp-tab')].map(t => t.dataset.pane));
  console.log('BOOK OF MORMON TABS:', JSON.stringify(bomTabs));
  if (bomTabs.includes('translations')) fail('Book of Mormon should have no Translations tab');

  console.log(bad ? 'RESULT: RED' : 'RESULT: GREEN');
  process.exitCode = bad;
  await b.close();
})();
