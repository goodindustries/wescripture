/**
 * Shared Puppeteer launch for root-level test-*.js scripts.
 * Set PUPPETEER_EXECUTABLE_PATH to override. Otherwise uses Puppeteer's downloaded Chrome when present,
 * else system Google Chrome on macOS if installed.
 */
const fs = require('fs');
const puppeteer = require('puppeteer');

function launchOptions() {
  const opts = {
    headless: process.env.PUPPETEER_HEADLESS === '0' ? false : 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
    protocolTimeout: 120000,
  };
  if (process.env.PUPPETEER_EXECUTABLE_PATH) {
    opts.executablePath = process.env.PUPPETEER_EXECUTABLE_PATH;
    return opts;
  }
  const macChrome = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
  if (process.platform === 'darwin' && fs.existsSync(macChrome)) {
    opts.executablePath = macChrome;
  }
  return opts;
}

async function launchBrowser() {
  return puppeteer.launch(launchOptions());
}

module.exports = { launchBrowser, launchOptions };
