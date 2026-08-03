/**
 * Shared helpers for the reader tests.
 *
 * The Come Follow Me week changes every Sunday, so any test that hardcodes
 * "Ezra 1:2" passes for seven days and then fails for the wrong reason. These
 * helpers derive the target from whatever the app is actually showing.
 */

const BASE = process.env.WS_BASE || 'http://localhost:8091';

/** Open the reader on this week's reading and wait for scripture to render. */
async function openReader(page, query = '?today=1') {
  await page.setCacheEnabled(false);
  await page.goto(BASE + '/library/' + query, { waitUntil: 'networkidle2', timeout: 45000 });
  await page.waitForFunction(() => window.currentChapter && document.querySelectorAll('.scripture .verse').length > 0,
    { timeout: 25000 });
  await new Promise(r => setTimeout(r, 1200));
}

/**
 * Reference of a verse in the open chapter carrying study material, preferring
 * the richest one so every tab has something to show.
 */
async function richestVerseRef(page) {
  return page.evaluate(() => {
    const meta = chapterMeta[currentChapter];
    if (!meta) return null;
    const verses = [...document.querySelectorAll('.scripture .verse.v[data-depth]')]
      .filter(v => v.dataset.depth !== '0')
      .sort((a, b) => Number(b.dataset.depth) - Number(a.dataset.depth));
    const el = verses[0] || document.querySelector('.scripture .verse.v');
    return el ? `${meta.book} ${meta.label}:${el.id.replace('v', '')}` : null;
  });
}

/** Open a verse's study pane and wait for the tabs to render. */
async function openVerse(page, ref) {
  await page.evaluate(r => openVerseDiscovery(r), ref);
  await page.waitForSelector('#panel-body .vp-tabs', { timeout: 20000 });
  await new Promise(r => setTimeout(r, 900));
}

/** The panel's tab order must always be a subsequence of the spec order. */
const TAB_ORDER = ['refs', 'commentary', 'words', 'translations'];

function tabsInSpecOrder(panes) {
  let i = -1;
  return panes.every(p => {
    const at = TAB_ORDER.indexOf(p);
    if (at <= i) return false;
    i = at;
    return true;
  });
}

module.exports = { BASE, openReader, richestVerseRef, openVerse, TAB_ORDER, tabsInSpecOrder };
