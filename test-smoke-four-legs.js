/**
 * Smoke test: Four journey legs + Today button at BOTH desktop (1440px) and mobile (390px)
 * - Leg 1: Page loads responsive
 * - Leg 2: Today button visible in topbar
 * - Leg 3: Navigate to reading (TOC/chapter loads)
 * - Leg 4: Click verse → context panel opens
 *
 * Mobile requirements (390px viewport):
 * - Verse text readable (no squeeze)
 * - Tap targets ≥44px
 * - Today button reachable
 * - Panel responsive (bottom-sheet or overlay, not side pane)
 */

const { launchBrowser } = require('./tools/puppeteer_launch.js');

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function testLegs(page, viewport) {
  const vp = `${viewport.width}x${viewport.height}`;
  console.log(`\n${'-'.repeat(60)}\nTesting at ${vp} viewport\n${'-'.repeat(60)}`);

  // Leg 1: Page loads
  console.log(`LEG 1: Page loads responsive (${vp})...`);
  await page.goto('http://127.0.0.1:4173/library/index.html', {
    waitUntil: 'networkidle0',
    timeout: 60000,
  });
  await page.waitForSelector('#splash.gone', { timeout: 60000 });
  console.log('✓ Page loads');

  // Leg 2: Today button visible in topbar
  console.log('LEG 2: Today button visible...');
  const todayBtn = await page.$('#today-btn');
  assert(todayBtn, 'Today button (#today-btn) not found in topbar');
  const todayText = await page.$eval('#today-btn', (el) => el.textContent.trim());
  assert(todayText === 'Today', `Today button text is "${todayText}", expected "Today"`);

  // Mobile: verify tap target ≥44px
  if (viewport.width <= 390) {
    const btnSize = await page.$eval('#today-btn', (el) => {
      const rect = el.getBoundingClientRect();
      return { width: Math.ceil(rect.width), height: Math.ceil(rect.height) };
    });
    assert(btnSize.height >= 44 || btnSize.width >= 44, `Today button tap target too small: ${btnSize.width}x${btnSize.height} (need ≥44px)`);
  }
  console.log('✓ Today button visible and labeled correctly');

  // Leg 3: Navigate to reading (use URL param to avoid TOC coupling)
  console.log('LEG 3: Navigate to chapter (Genesis 1)...');
  await page.goto('http://127.0.0.1:4173/library/index.html?jump=Genesis%201', {
    waitUntil: 'networkidle0',
    timeout: 60000,
  });
  await page.waitForSelector('#ch-genesis_1', { timeout: 30000 });
  const hasGenesisText = await page.evaluate(() => document.body.textContent.includes('Genesis'));
  assert(hasGenesisText, 'Genesis chapter did not load');

  // Mobile: verify verse text is readable (not squeezed)
  if (viewport.width <= 390) {
    const verseSize = await page.$eval('#ch-genesis_1 .verse-text', (el) => {
      const style = window.getComputedStyle(el);
      return {
        fontSize: parseFloat(style.fontSize),
        lineHeight: parseFloat(style.lineHeight),
        width: Math.ceil(el.getBoundingClientRect().width)
      };
    });
    assert(verseSize.fontSize >= 14, `Verse font too small: ${verseSize.fontSize}px (need ≥14px)`);
    assert(verseSize.width >= 280, `Verse text area too narrow: ${verseSize.width}px (need ≥280px)`);
  }
  console.log('✓ Chapter loads and renders (verse text readable)');

  // Leg 4: Click verse → context panel opens
  console.log('LEG 4: Click verse → context panel opens...');
  const verse = await page.$('#ch-genesis_1 .verse');
  assert(verse, 'No verse element found');
  await page.$eval('#ch-genesis_1 .verse', (el) => el.scrollIntoView({ block: 'center' }));

  // Click verse number to trigger discovery panel
  await page.click('#ch-genesis_1 .verse-num');

  // Wait for panel to open (channel becomes visible)
  await page.waitForFunction(() => {
    const channel = document.getElementById('channel');
    return channel && channel.classList.contains('open');
  }, { timeout: 10000 });

  // Mobile: verify panel width ≥90% viewport (full-width bottom-sheet)
  if (viewport.width <= 390) {
    const panelInfo = await page.evaluate(() => {
      const channel = document.getElementById('channel');
      const rect = channel.getBoundingClientRect();
      return {
        width: Math.ceil(rect.width),
        viewportWidth: window.innerWidth
      };
    });
    const panelPercentWidth = (panelInfo.width / panelInfo.viewportWidth * 100).toFixed(1);
    assert(
      panelPercentWidth >= 90,
      `Mobile panel width ${panelPercentWidth}% (need ≥90% for full-width bottom-sheet)`
    );
  }
  console.log('✓ Verse click opens context/panel state');

  console.log(`\n✅ All four journey legs verified at ${vp}`);
}

async function run() {
  const browser = await launchBrowser();
  const page = await browser.newPage();
  page.on('pageerror', (err) => {
    console.error('PAGEERROR', err && (err.stack || err.message || String(err)));
  });
  page.on('console', (msg) => {
    const type = msg.type();
    if (type === 'error') console.error('CONSOLE ERROR:', msg.text());
  });

  await page.evaluateOnNewDocument(() => {
    try { localStorage.removeItem('lds_position'); } catch (e) { /* ignore */ }
  });

  // Test at DESKTOP (1440px)
  await page.setViewport({ width: 1440, height: 1100, deviceScaleFactor: 1 });
  await testLegs(page, { width: 1440, height: 1100 });

  // Test at MOBILE (390px)
  await page.setViewport({ width: 390, height: 844, deviceScaleFactor: 1 });
  await testLegs(page, { width: 390, height: 844 });

  console.log('\n' + '='.repeat(60));
  console.log('✅ MOBILE + DESKTOP ACCEPTANCE GATES PASSED');
  console.log('='.repeat(60));

  await browser.close();
}

run().catch((err) => {
  console.error('FAILED:', err.stack || String(err));
  process.exit(1);
});
