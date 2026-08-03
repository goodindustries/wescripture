const puppeteer = require('puppeteer');
(async () => {
  const b = await puppeteer.launch({ headless: 'new' });
  const p = await b.newPage();
  await p.setViewport({ width: 1440, height: 900 });
  await p.setCacheEnabled(false);
  let bad = 0; const fail = m => { console.log('FAIL: ' + m); bad = 1; };
  const requested = [];
  p.on('request', r => requested.push(r.url()));
  const failed404 = [];
  p.on('response', r => { if (r.status() === 404) failed404.push(r.url()); });

  await p.goto((process.env.WS_BASE || 'http://localhost:8091') + '/library/', { waitUntil: 'networkidle2' });
  // Feed must resolve to a real state within the timeout window, not hang.
  await new Promise(r => setTimeout(r, 11000));

  const feed = await p.evaluate(() => {
    const box = document.getElementById('title-feed-list');
    return box ? box.textContent.trim().slice(0, 80) : null;
  });
  console.log('FEED TEXT:', JSON.stringify(feed));
  if (feed && /Loading/i.test(feed)) fail('feed still says Loading after 11s');

  // The Netlify function is the real config source in production and cannot
  // exist on a static local server, so the expectation flips by environment.
  const isLocal = /^https?:\/\/(localhost|127\.0\.0\.1)/.test(process.env.WS_BASE || 'http://localhost:8091');
  const netlifyCalls = requested.filter(u => u.includes('/.netlify/functions/config'));
  console.log('NETLIFY CONFIG REQUESTS:', netlifyCalls.length, isLocal ? '(local: expect 0)' : '(prod: expected)');
  if (isLocal && netlifyCalls.length) fail('still requesting the Netlify function on localhost');
  if (!isLocal && !netlifyCalls.length) fail('production should read config from the Netlify function');

  const own404 = failed404.filter(u => u.includes('localhost:8091'));
  console.log('LOCAL 404s:', JSON.stringify(own404.slice(0, 5)), 'total', own404.length);

  console.log(bad ? 'RESULT: RED' : 'RESULT: GREEN');
  process.exitCode = bad;
  await b.close();
})();
