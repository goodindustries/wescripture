const puppeteer = require('puppeteer');
const OUT = (process.env.WS_SHOTS || require('os').tmpdir());
(async () => {
  const b = await puppeteer.launch({ headless: 'new' });
  const p = await b.newPage();
  await p.setViewport({ width: 375, height: 812, isMobile: true, hasTouch: true });
  await p.setCacheEnabled(false);
  let bad = 0; const fail = m => { console.log('FAIL: ' + m); bad = 1; };
  await p.goto((process.env.WS_BASE || 'http://localhost:8091') + '/library/', { waitUntil: 'networkidle2' });
  await p.waitForFunction(() => { const e = document.getElementById('title-cfm'); return e && !e.hidden; }, { timeout: 20000 }).catch(() => fail('no home card on mobile'));
  const home = await p.evaluate(() => ({
    chipH: Math.round(document.querySelector('.cfm-card-chip').getBoundingClientRect().height),
    goH: Math.round(document.querySelector('.cfm-card-go').getBoundingClientRect().height),
    overflow: document.documentElement.scrollWidth > window.innerWidth,
  }));
  console.log('HOME MOBILE:', JSON.stringify(home));
  if (home.chipH < 44) fail("home chips under 44px: " + home.chipH);
  if (home.goH < 44) fail("home CTA under 44px: " + home.goH);
  if (home.overflow) fail('home page scrolls horizontally at 375px');
  await p.screenshot({ path: OUT + '/cfm-home-mobile.png' });

  await p.click('#title-cfm [data-cfm-start]');
  await p.waitForFunction(() => { const s = document.getElementById('cfm-strip'); return s && !s.hidden; }, { timeout: 20000 }).catch(() => fail('no strip on mobile'));
  await new Promise(r => setTimeout(r, 800));
  const strip = await p.evaluate(() => ({
    chapter: currentChapter,
    chipH: Math.round(document.querySelector('.cfm-chip').getBoundingClientRect().height),
    stepH: Math.round(document.querySelector('.cfm-step').getBoundingClientRect().height),
    overflow: document.documentElement.scrollWidth > window.innerWidth,
    stripH: Math.round(document.getElementById('cfm-strip').getBoundingClientRect().height),
  }));
  console.log('STRIP MOBILE:', JSON.stringify(strip));
  if (strip.chipH < 44) fail('strip chips under 44px: ' + strip.chipH);
  if (strip.stepH < 44) fail('strip steps under 44px: ' + strip.stepH);
  if (strip.overflow) fail('reader scrolls horizontally at 375px');
  await p.screenshot({ path: OUT + '/cfm-strip-mobile.png' });
  console.log(bad ? 'RESULT: RED' : 'RESULT: GREEN');
  process.exitCode = bad;
  await b.close();
})();
