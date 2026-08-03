/**
 * Translations pane: KJV anchors the comparison, public-domain versions sit
 * beside it, and non-Bible volumes get no tab at all.
 */
const puppeteer = require('puppeteer');
const { openReader, richestVerseRef, openVerse, tabsInSpecOrder } = require('./helpers');

(async () => {
  const b = await puppeteer.launch({ headless: 'new' });
  const p = await b.newPage();
  await p.setViewport({ width: 1440, height: 900 });
  let bad = 0;
  const fail = m => { console.log('FAIL: ' + m); bad = 1; };

  await openReader(p);
  const ref = await richestVerseRef(p);
  console.log('verse under test:', ref);
  await openVerse(p, ref);

  const tabs = await p.evaluate(() => [...document.querySelectorAll('.vp-tab')].map(t => t.dataset.pane));
  console.log('TABS:', JSON.stringify(tabs));
  if (!tabs.includes('translations')) fail('no Translations tab on a Bible verse');
  if (!tabsInSpecOrder(tabs)) fail('tab order off spec: ' + tabs);

  await p.click('.vp-tab[data-pane="translations"]');
  await new Promise(r => setTimeout(r, 300));
  const pane = await p.evaluate(() => ({
    vis: [...document.querySelectorAll('.vp-pane')].filter(x => getComputedStyle(x).display !== 'none').map(x => x.dataset.pane),
    rows: [...document.querySelectorAll('.tr-row')].map(r => ({
      label: r.querySelector('.tr-label')?.textContent.trim(),
      text: r.querySelector('.tr-text')?.textContent.trim(),
      base: r.classList.contains('tr-row--base'),
    })),
  }));
  console.log('ROWS:', JSON.stringify(pane.rows.map(r => ({ label: r.label, base: r.base, text: (r.text || '').slice(0, 50) })), null, 1));

  if (pane.vis.join(',') !== 'translations') fail('translations pane not shown on click');
  if (pane.rows.length !== 3) fail('expected KJV + WEB + ASV, got ' + pane.rows.length);
  if (!pane.rows[0]?.base) fail('KJV should be the base row and come first');
  const texts = pane.rows.map(r => r.text);
  if (new Set(texts).size !== texts.length) fail('translation rows are duplicates');
  if (texts.some(t => !t || t.length < 10)) fail('a translation row is empty');

  // A book with no Bible translations must not sprout the tab.
  await p.evaluate(() => jumpTo('1_nephi_1'));
  await p.waitForFunction(() => window.currentChapter === '1_nephi_1', { timeout: 20000 }).catch(() => {});
  await new Promise(r => setTimeout(r, 1500));
  await p.evaluate(() => openVerseDiscovery('1 Nephi 1:1'));
  await new Promise(r => setTimeout(r, 1800));
  const bom = await p.evaluate(() => [...document.querySelectorAll('.vp-tab')].map(t => t.dataset.pane));
  console.log('BOOK OF MORMON TABS:', JSON.stringify(bom));
  if (bom.includes('translations')) fail('Book of Mormon should have no Translations tab');

  console.log(bad ? 'RESULT: RED' : 'RESULT: GREEN');
  process.exitCode = bad;
  await b.close();
})();
