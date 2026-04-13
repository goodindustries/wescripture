#!/usr/bin/env node
/**
 * Smoke: root index.html loads; nav element present (home page nav is not fixed — layout is intentional).
 * Run: node test-nav-fixed.js
 */
const fs = require('fs');
const path = require('path');
const { launchBrowser } = require('./tools/puppeteer_launch.js');

const htmlPath = path.join(__dirname, 'index.html');
const html = fs.readFileSync(htmlPath, 'utf8');

(async () => {
  try {
    const browser = await launchBrowser();
    const page = await browser.newPage();
    await page.setViewport({ width: 1280, height: 800 });
    await page.setContent(html, { waitUntil: 'domcontentloaded' });

    const ok = await page.evaluate(() => !!document.querySelector('nav.home-nav'));
    await browser.close();
    if (!ok) {
      console.error('Missing nav.home-nav');
      process.exit(1);
    }
    console.log('✓ Root index nav present');
    process.exit(0);
  } catch (e) {
    console.error('Browser test failed:', e.message);
    process.exit(1);
  }
})();
