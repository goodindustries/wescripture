#!/usr/bin/env node
/**
 * Smoke: root index.html loads; nav element present (home page nav is not fixed — layout is intentional).
 * Run: node test-nav-fixed.js
 */
const http = require('http');
const fs = require('fs');
const path = require('path');
const { launchBrowser } = require('./tools/puppeteer_launch.js');

const PORT = 9876;
const htmlPath = path.join(__dirname, 'index.html');

const server = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/html' });
  res.end(fs.readFileSync(htmlPath));
});

server.listen(PORT, async () => {
  try {
    const browser = await launchBrowser();
    const page = await browser.newPage();
    await page.setViewport({ width: 1280, height: 800 });
    await page.goto(`http://localhost:${PORT}`, { waitUntil: 'networkidle0', timeout: 15000 });

    const ok = await page.evaluate(() => !!document.querySelector('nav.home-nav'));
    await browser.close();
    server.close();
    if (!ok) {
      console.error('Missing nav.home-nav');
      process.exit(1);
    }
    console.log('✓ Root index nav present');
    process.exit(0);
  } catch (e) {
    server.close();
    console.error('Browser test failed:', e.message);
    process.exit(1);
  }
});
