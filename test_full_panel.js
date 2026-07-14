const { launchBrowser } = require('./tools/puppeteer_launch.js');

(async () => {
  const browser = await launchBrowser();
  const page = await browser.newPage();

  await page.setViewport({ width: 1440, height: 1100, deviceScaleFactor: 1 });
  await page.goto('http://127.0.0.1:4173/library/index.html?jump=Genesis%201', { waitUntil: 'networkidle0', timeout: 60000 });

  // Click verse to open panel
  await page.waitForSelector('#ch-genesis_1 .verse-num', { timeout: 10000 });
  await page.click('#ch-genesis_1 .verse-num');
  await new Promise((r) => setTimeout(r, 1500));

  // Get all panel sections
  const allSections = await page.evaluate(() => {
    const panelBody = document.getElementById('panel-body');
    if (!panelBody) return [];

    const sections = [];
    let currentSection = null;

    Array.from(panelBody.querySelectorAll('.panel-section, .verse-panel-cards')).forEach(el => {
      if (el.classList.contains('panel-section')) {
        currentSection = {
          title: el.textContent.trim(),
          content: []
        };
        sections.push(currentSection);
      }
    });

    return sections.map(s => s.title);
  });

  console.log('Panel sections found:', allSections);

  // Screenshot of full panel
  await page.screenshot({ path: '/Users/reify/Classified/wescripture/panel-full-sections.png', fullPage: true });
  console.log('Full panel screenshot saved');

  await browser.close();
})();
