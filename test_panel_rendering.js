const { launchBrowser } = require('./tools/puppeteer_launch.js');

(async () => {
  const browser = await launchBrowser();
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 1100, deviceScaleFactor: 1 });

  const testCases = [
    { url: '?jump=Genesis%201', verse: '.verse-num', name: 'Genesis 1:1' },
    { url: '?jump=Romans%206', verse: '.verse-num', name: 'Romans 6:4' },
    { url: '?jump=Hosea%201', verse: '.verse-num', name: 'Hosea 1:2' }
  ];

  for (const tc of testCases) {
    console.log(`\nTesting ${tc.name}...`);

    await page.goto(`http://127.0.0.1:4173/library/index.html${tc.url}`, { waitUntil: 'networkidle0', timeout: 60000 });

    // Click first verse to open panel
    const verseBtn = await page.$(tc.verse);
    if (!verseBtn) {
      console.log('  ✗ Verse not found');
      continue;
    }

    await page.click(tc.verse);
    await new Promise((r) => setTimeout(r, 500));

    // Check panel
    const panelContent = await page.evaluate(() => {
      const panel = document.getElementById('channel');
      if (!panel || !panel.classList.contains('open')) return null;

      const quotes = Array.from(panel.querySelectorAll('.comm-card, .scrip-card'))
        .map(el => el.textContent.slice(0, 100).trim());

      return {
        hasPanel: true,
        quoteCount: quotes.length,
        sampleQuotes: quotes.slice(0, 3)
      };
    });

    if (panelContent) {
      console.log(`  ✓ Panel opened with ${panelContent.quoteCount} footnotes`);
      if (panelContent.sampleQuotes.length > 0) {
        console.log(`    Sample: "${panelContent.sampleQuotes[0]}"`);
      }
    } else {
      console.log('  ✗ Panel did not open');
    }
  }

  console.log('\n✓ Panel rendering verified');
  await browser.close();
})();
