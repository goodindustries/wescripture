const { launchBrowser } = require('./tools/puppeteer_launch.js');

(async () => {
  const browser = await launchBrowser();
  const page = await browser.newPage();

  await page.setViewport({ width: 1440, height: 1100, deviceScaleFactor: 1 });
  await page.goto('http://127.0.0.1:4173/library/index.html?jump=Genesis%201', { waitUntil: 'networkidle0', timeout: 60000 });

  // Click verse to open panel
  await page.waitForSelector('#ch-genesis_1 .verse-num', { timeout: 10000 });
  await page.click('#ch-genesis_1 .verse-num');
  await new Promise((r) => setTimeout(r, 1000));

  // Inspect panel structure
  const panelStructure = await page.evaluate(() => {
    const channel = document.getElementById('channel');
    if (!channel) return { error: 'No channel panel' };

    // Get all section headers and content areas
    const sections = Array.from(channel.querySelectorAll('h2, h3, [class*="section"], [class*="panel"], [class*="card"]'))
      .map(el => ({
        tag: el.tagName,
        class: el.className,
        text: el.textContent.trim().slice(0, 50)
      }))
      .slice(0, 20);

    const panelBody = channel.querySelector('#panelBody') || channel.querySelector('[class*="body"]');
    const panelBodyText = panelBody ? panelBody.textContent.trim().slice(0, 200) : 'No body found';
    const panelBodyHTML = panelBody ? panelBody.innerHTML.slice(0, 500) : '';

    return {
      sections,
      panelBodyText,
      panelBodyClasses: panelBody?.className || 'N/A',
      childCount: channel.children.length
    };
  });

  console.log('Panel structure:');
  console.log(JSON.stringify(panelStructure, null, 2));

  await browser.close();
})();
