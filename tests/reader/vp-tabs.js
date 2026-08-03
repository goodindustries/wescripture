const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900 });
  page.on('pageerror', e => console.log('PAGEERROR:', e.message));

  await page.goto((process.env.WS_BASE || 'http://localhost:8091') + '/library/?today=1', { waitUntil: 'networkidle2', timeout: 30000 });
  await page.waitForFunction(() => document.querySelectorAll('.scripture .verse').length > 0, { timeout: 20000 });

  // Open verse panel directly
  await page.evaluate(() => openVerseDiscovery('Ezra 1:2'));
  await page.waitForSelector('#panel-body .vp-tabs', { timeout: 15000 });
  await new Promise(r => setTimeout(r, 600));

  const state = await page.evaluate(() => {
    const tabs = [...document.querySelectorAll('#panel-body .vp-tab')].map(t => ({
      label: t.textContent.trim().replace(/\s+/g, ' '),
      pane: t.dataset.pane,
      active: t.classList.contains('vp-tab--active'),
    }));
    const panes = [...document.querySelectorAll('#panel-body .vp-pane')].map(p => ({
      pane: p.dataset.pane,
      visible: getComputedStyle(p).display !== 'none',
    }));
    const clampEls = document.querySelectorAll('#panel-body .comm-text--clamp').length;
    const donaMoreBtns = document.querySelectorAll('#panel-body .dona-more-btn').length;
    return { tabs, panes, clampEls, donaMoreBtns };
  });
  console.log(JSON.stringify(state, null, 2));

  const fail = m => { console.log('FAIL: ' + m); process.exitCode = 1; };
  if (!state.tabs.length) fail('no tabs rendered');
  const order = state.tabs.map(t => t.pane).join(',');
  const expected = ['refs', 'commentary', 'words', 'translations'].filter(id => state.tabs.some(t => t.pane === id)).join(',');
  if (order !== expected) fail('tab order wrong: ' + order);
  if (state.tabs[0] && !state.tabs[0].active) fail('first tab not active');
  const visiblePanes = state.panes.filter(p => p.visible);
  if (visiblePanes.length !== 1) fail('expected exactly 1 visible pane, got ' + visiblePanes.length);
  if (visiblePanes[0] && visiblePanes[0].pane !== state.tabs[0].pane) fail('visible pane != active tab');

  await page.screenshot({ path: (process.env.WS_SHOTS || require('os').tmpdir()) + '/vp-tabs-refs.png' });

  // Switch to Commentary tab if present
  const hasComm = state.tabs.some(t => t.pane === 'commentary');
  if (hasComm) {
    await page.click('#panel-body .vp-tab[data-pane="commentary"]');
    await new Promise(r => setTimeout(r, 300));
    const after = await page.evaluate(() => {
      const vis = [...document.querySelectorAll('#panel-body .vp-pane')].filter(p => getComputedStyle(p).display !== 'none').map(p => p.dataset.pane);
      const clamped = document.querySelector('#panel-body .comm-text--clamp');
      let clampHeightOk = null;
      if (clamped) clampHeightOk = clamped.scrollHeight > clamped.clientHeight;
      return { vis, clampHeightOk };
    });
    console.log('after commentary click:', JSON.stringify(after));
    if (after.vis.join(',') !== 'commentary') fail('commentary tab switch broken: ' + after.vis);
    await page.screenshot({ path: (process.env.WS_SHOTS || require('os').tmpdir()) + '/vp-tabs-commentary.png' });

    // Read-more toggle
    const btn = await page.$('#panel-body .dona-more-btn');
    if (btn) {
      await btn.click();
      await new Promise(r => setTimeout(r, 200));
      const open = await page.evaluate(() => !document.querySelector('#panel-body .verse-panel-cards.expanded .comm-text--clamp, #panel-body .vp-pane--active .comm-text--clamp'));
      console.log('read-more expanded clamp removed:', open);
      if (!open) fail('read-more did not unclamp');
    }
  }

  console.log(process.exitCode ? 'RESULT: RED' : 'RESULT: GREEN');
  await browser.close();
})();
