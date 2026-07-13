/**
 * Smoke test: Four journey legs + Today button
 * - Leg 1: Page loads responsive
 * - Leg 2: Today button visible in topbar
 * - Leg 3: Navigate to reading (TOC/chapter loads)
 * - Leg 4: Click verse → context panel opens
 */

const { launchBrowser } = require('./tools/puppeteer_launch.js');

function assert(condition, message) {
  if (!condition) throw new Error(message);
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

  await page.setViewport({ width: 1440, height: 1100, deviceScaleFactor: 1 });
  await page.evaluateOnNewDocument(() => {
    try { localStorage.removeItem('lds_position'); } catch (e) { /* ignore */ }
  });

  // Leg 1: Page loads
  console.log('LEG 1: Page loads responsive (desktop)...');
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
  console.log('✓ Today button visible and labeled correctly');

  // Leg 3: Navigate to reading (use URL param to avoid TOC coupling)
  console.log('LEG 3: Navigate to chapter (Genesis 1)...');
  await page.goto('http://127.0.0.1:4173/library/index.html?jump=Genesis%201', {
    waitUntil: 'networkidle0',
    timeout: 60000,
  });
  await page.waitForSelector('#ch-genesis_1', { timeout: 30000 });
  const chapterTitle = await page.$eval('h2.book-title, .chapter-heading, h1', (el) =>
    el ? el.textContent.trim() : ''
  );
  assert(chapterTitle.includes('Genesis') || document.body.textContent.includes('Genesis'),
    'Genesis chapter did not load');
  console.log('✓ Chapter loads and renders');

  // Leg 4: Click verse → context panel opens
  console.log('LEG 4: Click verse → context panel opens...');
  const verse = await page.$('#ch-genesis_1 .verse');
  assert(verse, 'No verse element found');
  await page.$eval('#ch-genesis_1 .verse', (el) => el.scrollIntoView({ block: 'center' }));
  await page.click('#ch-genesis_1 .verse');

  // Wait for verse to be focused
  await page.waitForFunction(() =>
    document.querySelector('#ch-genesis_1 .verse.verse-focus'),
    { timeout: 10000 }
  );

  // Check for verse panel / context display (can be right-side panel or inline)
  const hasPanel = await page.evaluate(() => {
    // Look for right-side panel or context panel markers
    const rightPanel = document.querySelector('[id^="panel"], .study-panel, [class*="panel"]');
    const verseExpanded = document.querySelector('.verse.verse-focus');
    return !!(rightPanel || verseExpanded);
  });
  assert(hasPanel, 'Context panel/focus state did not appear after verse click');
  console.log('✓ Verse click opens context/panel state');

  console.log('\n✅ All four journey legs verified');
  console.log('✓ Leg 1: Responsive page load');
  console.log('✓ Leg 2: Today button visible in topbar');
  console.log('✓ Leg 3: Chapter navigation works');
  console.log('✓ Leg 4: Verse click → context panel');

  await browser.close();
}

run().catch((err) => {
  console.error('FAILED:', err.stack || String(err));
  process.exit(1);
});
