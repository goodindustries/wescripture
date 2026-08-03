const puppeteer = require('puppeteer');
(async () => {
  const b = await puppeteer.launch({ headless: 'new' });
  const p = await b.newPage();
  await p.setViewport({ width: 1440, height: 900 });
  await p.setCacheEnabled(false);
  let bad = 0; const fail = m => { console.log('FAIL: ' + m); bad = 1; };

  await p.goto((process.env.WS_BASE || 'http://localhost:8091') + '/library/', { waitUntil: 'networkidle2' });
  await p.evaluate(() => jumpTo('1_chronicles_15', 25));
  await p.waitForFunction(() => window.currentChapter === '1_chronicles_15', { timeout: 20000 });
  await new Promise(r => setTimeout(r, 1500));

  // The user's complaint: a commentary card that just repeats the next verse.
  await p.evaluate(() => openVerseDiscovery('1 Chronicles 15:25'));
  await new Promise(r => setTimeout(r, 1800));

  const res = await p.evaluate(() => {
    const norm = s => (s || '').toLowerCase().replace(/[^a-z0-9]+/g, '');
    const block = document.getElementById('ch-1_chronicles_15');
    const v26 = block && block.querySelector('.verse[id="v26"] .verse-text');
    const verse26 = norm(v26 && v26.textContent);
    const commentary = [...document.querySelectorAll('#panel-body .comm-card .comm-text')].map(e => e.textContent);
    return {
      verse26Head: (v26 && v26.textContent || '').slice(0, 60),
      cards: commentary.length,
      echoes: commentary.filter(t => verse26 && norm(t).includes(verse26.slice(0, 80))).map(t => t.slice(0, 70)),
    };
  });
  console.log('VERSE 26 STARTS:', res.verse26Head);
  console.log('COMMENTARY CARDS:', res.cards);
  console.log('CARDS ECHOING VERSE 26:', JSON.stringify(res.echoes));
  if (res.echoes.length) fail(`${res.echoes.length} commentary card(s) just repeat verse 26`);

  console.log(bad ? 'RESULT: RED' : 'RESULT: GREEN');
  process.exitCode = bad;
  await b.close();
})();
