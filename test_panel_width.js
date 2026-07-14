const { launchBrowser } = require('./tools/puppeteer_launch.js');

(async () => {
  const browser = await launchBrowser();
  const page = await browser.newPage();

  await page.setViewport({ width: 390, height: 844, deviceScaleFactor: 1 });
  await page.goto('http://127.0.0.1:4173/library/index.html?jump=Genesis%201', { waitUntil: 'networkidle0', timeout: 60000 });

  // Click verse to open panel
  await page.waitForSelector('#ch-genesis_1 .verse-num', { timeout: 10000 });
  await page.click('#ch-genesis_1 .verse-num');
  await new Promise((r) => setTimeout(r, 500));

  // Measure panel dimensions
  const panelInfo = await page.evaluate(() => {
    const panel = document.getElementById('channel') || document.querySelector('[id*="panel"]') || document.querySelector('.panel') || document.querySelector('[class*="panel"]');
    const viewport = { width: window.innerWidth, height: window.innerHeight };
    
    if (!panel) {
      console.log('No panel found');
      return { error: 'No panel found', viewport };
    }

    const rect = panel.getBoundingClientRect();
    const panelWidth = Math.ceil(rect.width);
    const panelHeight = Math.ceil(rect.height);
    const panelPercentWidth = (panelWidth / viewport.width * 100).toFixed(1);
    
    return {
      panelWidth,
      panelHeight,
      viewportWidth: viewport.width,
      viewportHeight: viewport.height,
      panelPercentWidth: parseFloat(panelPercentWidth),
      panelVisible: panel.offsetParent !== null,
      panelClasses: panel.className
    };
  });

  console.log('Panel dimensions at 390px:', JSON.stringify(panelInfo, null, 2));
  
  if (panelInfo.panelPercentWidth >= 90) {
    console.log('✓ Panel occupies ≥90% viewport width');
  } else {
    console.log('✗ Panel occupies only ' + panelInfo.panelPercentWidth + '% viewport width (need ≥90%)');
  }

  await browser.close();
})();
