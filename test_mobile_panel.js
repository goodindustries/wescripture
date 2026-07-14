const { launchBrowser } = require('./tools/puppeteer_launch.js');

(async () => {
  const browser = await launchBrowser();
  const page = await browser.newPage();

  // Set 390px viewport
  await page.setViewport({ width: 390, height: 844, deviceScaleFactor: 1 });

  // Navigate to Genesis 1
  await page.goto('http://127.0.0.1:4173/library/index.html?jump=Genesis%201', { waitUntil: 'networkidle0', timeout: 60000 });

  // Click verse number to open panel
  await page.waitForSelector('#ch-genesis_1 .verse-num', { timeout: 10000 });
  await page.click('#ch-genesis_1 .verse-num');

  // Wait for panel to open
  await new Promise((r) => setTimeout(r, 1000));

  // Take screenshot
  await page.screenshot({ path: '/Users/reify/Classified/wescripture/mobile-panel-390px.png', fullPage: false });

  console.log('Screenshot saved to mobile-panel-390px.png');
  await browser.close();
})();
