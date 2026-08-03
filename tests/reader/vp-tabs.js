/**
 * Verse panel: pill tabs in spec order, one pane at a time, long commentary
 * collapsed until asked for.
 */
const puppeteer = require('puppeteer');
const { openReader, richestVerseRef, openVerse, tabsInSpecOrder } = require('./helpers');

const OUT = (process.env.WS_SHOTS || require('os').tmpdir());

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900 });
  const errs = [];
  page.on('pageerror', e => { errs.push(e.message); console.log('PAGEERROR:', e.message); });

  const fail = m => { console.log('FAIL: ' + m); process.exitCode = 1; };

  await openReader(page);
  const ref = await richestVerseRef(page);
  console.log('verse under test:', ref);
  if (!ref) return fail('no verse with study material in this week\'s chapter');
  await openVerse(page, ref);

  const state = await page.evaluate(() => ({
    tabs: [...document.querySelectorAll('#panel-body .vp-tab')].map(t => ({
      pane: t.dataset.pane,
      active: t.classList.contains('vp-tab--active'),
      count: Number((t.querySelector('.vp-tab-count') || {}).textContent || 0),
    })),
    panes: [...document.querySelectorAll('#panel-body .vp-pane')].map(p => ({
      pane: p.dataset.pane,
      visible: getComputedStyle(p).display !== 'none',
    })),
  }));
  console.log('TABS:', JSON.stringify(state.tabs));

  if (!state.tabs.length) fail('no tabs rendered');
  if (!tabsInSpecOrder(state.tabs.map(t => t.pane))) fail('tab order off spec: ' + state.tabs.map(t => t.pane));
  if (state.tabs[0] && !state.tabs[0].active) fail('first tab not active');
  if (state.tabs.some(t => t.count === 0)) fail('a tab rendered with a zero count instead of collapsing');
  const visible = state.panes.filter(p => p.visible);
  if (visible.length !== 1) fail('expected exactly 1 visible pane, got ' + visible.length);
  if (visible[0] && visible[0].pane !== state.tabs[0].pane) fail('visible pane is not the active tab');
  await page.screenshot({ path: OUT + '/vp-tabs-first.png' });

  // Switching tabs shows exactly that pane.
  for (const tab of state.tabs.slice(1)) {
    await page.click(`.vp-tab[data-pane="${tab.pane}"]`);
    await new Promise(r => setTimeout(r, 250));
    const shown = await page.evaluate(() => [...document.querySelectorAll('.vp-pane')]
      .filter(p => getComputedStyle(p).display !== 'none').map(p => p.dataset.pane));
    if (shown.join(',') !== tab.pane) fail(`clicking ${tab.pane} showed ${shown}`);
  }

  // Long commentary collapses behind Read more; clicking it unclamps.
  const hasCommentary = state.tabs.some(t => t.pane === 'commentary');
  if (hasCommentary) {
    await page.click('.vp-tab[data-pane="commentary"]');
    await new Promise(r => setTimeout(r, 250));
    const btn = await page.$('#panel-body .dona-more-btn');
    if (btn) {
      const before = await page.evaluate(() => document.querySelectorAll('#panel-body .comm-text--clamp').length);
      await btn.click();
      await new Promise(r => setTimeout(r, 250));
      const after = await page.evaluate(() => document.querySelectorAll('#panel-body .comm-text--clamp').length);
      console.log('clamped before/after Read more:', before, after);
      if (!(before > 0 && after === before - 1)) fail(`Read more did not unclamp (${before} -> ${after})`);
    } else {
      console.log('note: no long commentary on this verse, Read more not exercised');
    }
    await page.screenshot({ path: OUT + '/vp-tabs-commentary.png' });
  }

  if (errs.length) fail('page errors: ' + errs.join(' | '));
  console.log(process.exitCode ? 'RESULT: RED' : 'RESULT: GREEN');
  await browser.close();
})();
