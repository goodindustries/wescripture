const { launchBrowser } = require('./tools/puppeteer_launch.js');

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

/** Leave source reader / year group / collection until TOC shows the Sources shelf. */
async function tocBackToSourcesShelf(page) {
  for (var step = 0; step < 10; step++) {
    const atShelf = await page.evaluate(() => {
      var t = document.querySelector('#toc-title');
      var s = document.querySelector('#toc-subtitle');
      return t && t.textContent.trim() === 'Sources' && s && s.textContent.trim() === 'Other Church Writings';
    });
    if (atShelf) return;
    const canBack = await page.evaluate(() => {
      var b = document.querySelector('#toc-back');
      return b && b.classList.contains('show');
    });
    if (!canBack) throw new Error('toc-back not visible before Sources shelf');
    await page.$eval('#toc-back', (el) => el.click());
    await page.waitForSelector('#toc-grid .toc-tile', { timeout: 10000 });
  }
  throw new Error('Could not reach Sources shelf (Other Church Writings)');
}

async function run() {
  const browser = await launchBrowser();

  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 1100, deviceScaleFactor: 1 });
  await page.goto('http://127.0.0.1:4173/library/index.html', {
    waitUntil: 'networkidle0',
    timeout: 60000,
  });

  await page.waitForSelector('#splash.gone', { timeout: 60000 });
  await page.waitForSelector('#toc:not(.hidden)', { timeout: 10000 });
  await page.waitForSelector('#toc-grid .toc-tile', { timeout: 10000 });

  let sourceTiles = await page.$$eval('#toc-grid .toc-tile .toc-tile-title', (els) =>
    els.map((el) => el.textContent.trim())
  );
  if (!sourceTiles.includes('General Conference')) {
    await page.$eval('.toc-tile[data-action="source-root"]', (el) => el.click());
    await page.waitForFunction(() =>
      document.querySelector('#toc-title')?.textContent === 'Sources' &&
      document.querySelector('#toc-subtitle')?.textContent === 'Other Church Writings'
    , { timeout: 10000 });
    sourceTiles = await page.$$eval('#toc-grid .toc-tile .toc-tile-title', (els) =>
      els.map((el) => el.textContent.trim())
    );
  }
  assert(sourceTiles.includes('History of the Church'), 'History of the Church missing from Sources shelf');
  assert(sourceTiles.includes('General Conference'), 'General Conference missing from Sources shelf');
  ['Journal of Discourses', 'Times and Seasons', 'Millennial Star'].forEach(function(label) {
    if (!sourceTiles.includes(label)) console.warn('Sources shelf: "' + label + '" not visible (scroll TOC if needed).');
  });

  await page.$eval('.toc-tile[data-action="source-collection"][data-collection="general_conference"]', (el) => el.click());
  await page.waitForFunction(() =>
    document.querySelector('#toc-title').textContent === 'Sources' &&
    document.querySelector('#toc-subtitle').textContent === 'General Conference'
  );
  await page.waitForSelector(
    '.toc-tile[data-action="source-group"][data-collection="general_conference"][data-group="general_conference:year_2007"]',
    { timeout: 20000 }
  );
  await page.$eval(
    '.toc-tile[data-action="source-group"][data-collection="general_conference"][data-group="general_conference:year_2007"]',
    (el) => el.click()
  );
  await page.waitForFunction(() =>
    document.querySelector('#toc-title').textContent === 'General Conference' &&
    document.querySelector('#toc-subtitle').textContent.trim() === '2007'
  );
  await page.$eval('.toc-tile[data-action="source-doc"][data-doc="general_conference:general_conference_2007_10_good_better_best"]', (el) => el.click());
  await page.waitForSelector('.source-doc .source-title', { timeout: 20000 });
  await page.waitForFunction(() => document.querySelectorAll('.source-doc span.w').length > 0, { timeout: 30000 });
  const gcState = await page.evaluate(() => ({
    title: document.querySelector('.source-doc .source-title')?.textContent.trim() || '',
    subtitle: document.querySelector('.source-doc .source-subtitle')?.textContent.trim() || '',
    activeMeta: document.querySelector('.toc-tile.active .toc-tile-meta')?.textContent.trim() || '',
    cwCount: document.querySelectorAll('.source-doc span.w').length,
    sample: Array.from(document.querySelectorAll('.source-doc span.w')).slice(0, 6).map((el) => el.textContent.trim()),
  }));
  assert(gcState.title === 'Good, Better, Best', 'General Conference talk did not load with its real title');
  assert(/Dallin H\. Oaks/.test(gcState.subtitle), 'General Conference subtitle did not include the speaker');
  assert(/October 2007/.test(gcState.activeMeta), 'General Conference TOC meta did not include the session');
  assert(gcState.cwCount > 0, 'General Conference talk did not render clickable words');
  await page.evaluate(() => {
    const target = Array.from(document.querySelectorAll('.source-doc span.w')).find((el) => /good|better|best/i.test(el.textContent || ''))
      || document.querySelector('.source-doc span.w');
    target?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
  });
  await page.waitForFunction(() => document.querySelector('#channel')?.classList.contains('open'), { timeout: 20000 });
  await page.waitForFunction(() => {
    const cards = document.querySelectorAll('#panel-body .ch-morsel');
    return cards.length > 0;
  }, { timeout: 20000 });
  const gcChannelState = await page.evaluate(() => ({
    resultCount: document.querySelectorAll('#panel-body .ch-morsel').length,
    firstText: document.querySelector('#panel-body .ch-morsel')?.innerText?.trim() || '',
    firstOpenLabel: document.querySelector('#panel-body .ch-open-context')?.textContent?.trim() || '',
  }));
  assert(gcChannelState.resultCount > 0, 'General Conference word click did not open any semantic results');
  assert(gcChannelState.firstOpenLabel === 'Read Source →', 'channel morsels did not render the Read Source action');
  await page.$eval('#panel-body .ch-open-context', (el) => el.click());
  await page.waitForFunction(() =>
    document.querySelector('.reader-card .source-title, .source-doc .source-title, #chapter-title')?.textContent?.trim().length > 0
  , { timeout: 20000 });
  await tocBackToSourcesShelf(page);

  await page.$eval('.toc-tile[data-action="source-collection"][data-collection="history_of_church"]', (el) => el.click());
  await page.waitForFunction(() =>
    document.querySelector('#toc-title').textContent === 'Sources' &&
    document.querySelector('#toc-subtitle').textContent === 'History of the Church'
  );
  await page.$eval('.toc-tile[data-action="source-doc"][data-doc="history_of_church:vol1"]', (el) => el.click());
  await page.waitForSelector('.source-doc .source-title', { timeout: 20000 });
  const hocState = await page.evaluate(() => ({
    title: document.querySelector('.source-doc .source-title')?.textContent.trim() || '',
    subtitle: document.querySelector('.source-doc .source-subtitle')?.textContent.trim() || '',
    location: document.getElementById('breadcrumbs')?.innerText.replace(/\s+/g, ' ').trim() || '',
  }));
  assert(hocState.title === 'Volume 1', 'History of the Church title did not load');
  assert(hocState.subtitle === 'History of the Church', 'History of the Church subtitle did not load');
  assert(
    /History of the Church/.test(hocState.location) && /Volume\s*1/.test(hocState.location),
    'History of the Church breadcrumbs did not reflect the open document'
  );
  await tocBackToSourcesShelf(page);

  await page.waitForSelector('.toc-tile[data-action="source-collection"][data-collection="times_and_seasons"]', { timeout: 10000 });
  await page.evaluate(() => document.querySelector('.toc-tile[data-action="source-collection"][data-collection="times_and_seasons"]')?.click());
  await page.waitForFunction(() =>
    document.querySelector('#toc-subtitle').textContent === 'Times and Seasons' &&
    document.querySelectorAll('.toc-tile[data-action="source-doc"]').length > 0
  );

  const timesState = await page.evaluate(() => {
    const first = document.querySelector('.toc-tile[data-action="source-doc"]');
    return {
      firstLabel: first?.querySelector('.toc-tile-title')?.textContent.trim() || '',
      firstMeta: first?.querySelector('.toc-tile-meta')?.textContent.trim() || '',
      docCount: document.querySelectorAll('.toc-tile[data-action="source-doc"]').length,
    };
  });

  assert(timesState.docCount >= 20, 'Times and Seasons did not split into issue-like source docs');
  assert(/^[A-Za-z]+\s+\d{4}$/.test(timesState.firstLabel), 'Times and Seasons issue titles did not render as clean date labels');
  assert(/Vol\.\s*\d+/.test(timesState.firstMeta) && /No\.\s*\d+/.test(timesState.firstMeta), 'Times and Seasons issue metadata did not render volume/number details');
  await tocBackToSourcesShelf(page);

  await page.waitForSelector('.toc-tile[data-action="source-collection"][data-collection="millennial_star"]', { timeout: 10000 });
  await page.evaluate(() => document.querySelector('.toc-tile[data-action="source-collection"][data-collection="millennial_star"]')?.click());
  await page.waitForFunction(() =>
    document.querySelector('#toc-subtitle').textContent === 'Millennial Star' &&
    document.querySelectorAll('.toc-tile[data-action="source-doc"]').length > 0
  );

  const starState = await page.evaluate(() => {
    const first = document.querySelector('.toc-tile[data-action="source-doc"]');
    return {
      firstLabel: first?.querySelector('.toc-tile-title')?.textContent.trim() || '',
      firstMeta: first?.querySelector('.toc-tile-meta')?.textContent.trim() || '',
      docCount: document.querySelectorAll('.toc-tile[data-action="source-doc"]').length,
    };
  });

  assert(starState.docCount >= 100, 'Millennial Star did not split into issue-like source docs');
  assert(/^[A-Za-z]+\s+\d{4}$/.test(starState.firstLabel), 'Millennial Star issue titles did not render as clean date labels');
  assert(/Vol\.\s*\d+/.test(starState.firstMeta) && /No\.\s*\d+/.test(starState.firstMeta), 'Millennial Star issue metadata did not render volume/number details');
  await tocBackToSourcesShelf(page);

  await page.$eval('.toc-tile[data-action="source-collection"][data-collection="ancient_texts"]', (el) => el.click());
  await page.waitForFunction(() =>
    document.querySelector('#toc-title').textContent === 'Sources' &&
    document.querySelector('#toc-subtitle').textContent === 'Ancient Texts'
  );
  await page.$eval('.toc-tile[data-action="source-doc"][data-doc="ancient_texts:enuma_elish"]', (el) => el.click());
  await page.waitForSelector('.source-doc .source-title', { timeout: 20000 });
  const enumaState = await page.evaluate(() => ({
    title: document.querySelector('.source-doc .source-title')?.textContent.trim() || '',
    first: document.querySelector('.source-doc .source-para')?.textContent.trim() || '',
    body: document.querySelector('.source-doc')?.innerText || '',
  }));
  assert(enumaState.title === 'Enuma Elish', 'Enuma Elish source title did not load');
  assert(/When the heavens above were yet unnamed/i.test(enumaState.first), 'Enuma Elish did not open on the core tablet translation');
  assert(!/[詩經氓黍離溱洧園有桃伐檀七月]/.test(enumaState.body), 'Enuma Elish still contains the old Chinese source text');
  await tocBackToSourcesShelf(page);

  await page.$eval('.toc-tile[data-action="source-collection"][data-collection="ancient_texts"]', (el) => el.click());
  await page.waitForFunction(() =>
    document.querySelector('#toc-title').textContent === 'Sources' &&
    document.querySelector('#toc-subtitle').textContent === 'Ancient Texts'
  );
  await page.$eval('.toc-tile[data-action="source-doc"][data-doc="ancient_texts:gilgamesh"]', (el) => el.click());
  await page.waitForSelector('.source-doc .source-title', { timeout: 20000 });
  const gilgameshState = await page.evaluate(() => ({
    title: document.querySelector('.source-doc .source-title')?.textContent.trim() || '',
    first: document.querySelector('.source-doc .source-para')?.textContent.trim() || '',
    body: document.querySelector('.source-doc')?.innerText || '',
  }));
  assert(gilgameshState.title === 'Gilgamesh', 'Gilgamesh source title did not load');
  assert(/Now the harlot urges Enkidu/i.test(gilgameshState.first), 'Gilgamesh still opens on Gutenberg boilerplate instead of the first narrative section');
  assert(!/Project Gutenberg eBook of The Epic of Gilgamish/i.test(gilgameshState.body), 'Gilgamesh still contains the old Gutenberg boilerplate opening');
  await tocBackToSourcesShelf(page);

  await page.$eval('.toc-tile[data-action="source-collection"][data-collection="ancient_texts"]', (el) => el.click());
  await page.waitForFunction(() =>
    document.querySelector('#toc-title').textContent === 'Sources' &&
    document.querySelector('#toc-subtitle').textContent === 'Ancient Texts'
  );
  await page.$eval('.toc-tile[data-action="source-doc"][data-doc="ancient_texts:book_of_enoch"]', (el) => el.click());
  await page.waitForSelector('.source-doc .source-title', { timeout: 20000 });
  const enochState = await page.evaluate(() => ({
    title: document.querySelector('.source-doc .source-title')?.textContent.trim() || '',
    first: document.querySelector('.source-doc .source-para')?.textContent.trim() || '',
  }));
  assert(enochState.title === 'Book Of Enoch', 'Book of Enoch source title did not load');
  assert(/The words of the blessing of Enoch/i.test(enochState.first), 'Book of Enoch still opens on front matter instead of the text');
  await tocBackToSourcesShelf(page);

  await page.$eval('.toc-tile[data-action="source-collection"][data-collection="ancient_texts"]', (el) => el.click());
  await page.waitForFunction(() =>
    document.querySelector('#toc-title').textContent === 'Sources' &&
    document.querySelector('#toc-subtitle').textContent === 'Ancient Texts'
  );
  await page.$eval('.toc-tile[data-action="source-doc"][data-doc="ancient_texts:josephus_antiquities"]', (el) => el.click());
  await page.waitForSelector('.source-doc .source-title', { timeout: 20000 });
  const josephusState = await page.evaluate(() => ({
    title: document.querySelector('.source-doc .source-title')?.textContent.trim() || '',
    first: document.querySelector('.source-doc .source-para')?.textContent.trim() || '',
  }));
  assert(josephusState.title === 'Josephus Antiquities', 'Josephus source title did not load');
  assert(/^BOOK I\./i.test(josephusState.first), 'Josephus still opens on contents/front matter instead of Book I');
  await tocBackToSourcesShelf(page);

  await page.$eval('.toc-tile[data-action="source-collection"][data-collection="ancient_texts"]', (el) => el.click());
  await page.waitForFunction(() =>
    document.querySelector('#toc-title').textContent === 'Sources' &&
    document.querySelector('#toc-subtitle').textContent === 'Ancient Texts'
  );
  await page.$eval('.toc-tile[data-action="source-doc"][data-doc="ancient_texts:book_of_jubilees"]', (el) => el.click());
  await page.waitForSelector('.source-doc .source-title', { timeout: 20000 });
  const jubileesState = await page.evaluate(() => ({
    title: document.querySelector('.source-doc .source-title')?.textContent.trim() || '',
    first: document.querySelector('.source-doc .source-para')?.textContent.trim() || '',
    body: document.querySelector('.source-doc')?.innerText || '',
  }));
  assert(/Book Of Jubilees/i.test(jubileesState.title), 'Book of Jubilees source title did not load');
  assert(/And it came to pass in the first year/i.test(jubileesState.first), 'Book of Jubilees still opens on front matter instead of chapter I');
  assert(!/Louisa Pallant/i.test(jubileesState.body), 'Book of Jubilees still contains the old wrong Gutenberg source text');
  assert(!/Tables\. cd read|INTRODUCTION, NOTES, AND INDICES|Mesilla 19 b/i.test(jubileesState.body), 'Book of Jubilees still contains interleaved OCR notes/commentary');
  assert(!/INDEX II|Library Bureau Cat\\. No\\.|BS 1830 \\.J7 A3 1902/i.test(jubileesState.body), 'Book of Jubilees still contains trailing index/library apparatus');
  await tocBackToSourcesShelf(page);

  await page.$eval('.toc-tile[data-action="source-collection"][data-collection="ancient_texts"]', (el) => el.click());
  await page.waitForFunction(() =>
    document.querySelector('#toc-title').textContent === 'Sources' &&
    document.querySelector('#toc-subtitle').textContent === 'Ancient Texts'
  );
  await page.$eval('.toc-tile[data-action="source-doc"][data-doc="ancient_texts:testament_twelve_patriarchs"]', (el) => el.click());
  await page.waitForSelector('.source-doc .source-title', { timeout: 20000 });
  const patriarchsState = await page.evaluate(() => ({
    title: document.querySelector('.source-doc .source-title')?.textContent.trim() || '',
    first: document.querySelector('.source-doc .source-para')?.textContent.trim() || '',
    body: document.querySelector('.source-doc')?.innerText || '',
  }));
  assert(patriarchsState.title === 'Testament Twelve Patriarchs', 'Testament of the Twelve Patriarchs source title did not load');
  assert(/THE TESTAMENT OF REUBEN/i.test(patriarchsState.first), 'Testament of the Twelve Patriarchs still opens on introduction instead of Reuben');
  assert(!/U\\.S\\. Copyright Renewals/i.test(patriarchsState.body), 'Testament of the Twelve Patriarchs still contains the old wrong Gutenberg source text');
  assert(!/THE following twelve books are biographies written between 107 and 137 B\\.C\\.|Rutherford H\\. Platt/i.test(patriarchsState.body), 'Testament of the Twelve Patriarchs still contains editorial preface material instead of clean primary text');
  assert(!/TRANSLATIONS OF EARLY DOCUMENTS|SOCIETY FOR PROMOTING CHRISTIAN KNOWLEDGE|ALL BOOKSELLERS/i.test(patriarchsState.body), 'Testament of the Twelve Patriarchs still contains trailing publisher/series apparatus');
  await tocBackToSourcesShelf(page);

  await page.$eval('.toc-tile[data-action="source-collection"][data-collection="journal_of_discourses"]', (el) => el.click());
  await page.waitForFunction(() =>
    document.querySelector('#toc-title').textContent === 'Sources' &&
    document.querySelector('#toc-subtitle').textContent === 'Journal of Discourses'
  );

  await page.$eval('.toc-tile[data-action="source-doc"][data-doc="journal_of_discourses:vol_01"]', (el) => el.click());
  await page.waitForSelector('.source-doc .source-title', { timeout: 20000 });

  const sourceState = await page.evaluate(() => ({
    title: document.querySelector('.source-doc .source-title')?.textContent.trim(),
    subtitle: document.querySelector('.source-doc .source-subtitle')?.textContent.trim(),
    location: document.getElementById('breadcrumbs')?.innerText.replace(/\s+/g, ' ').trim() || '',
    activeTile: document.querySelector('.toc-tile.active .toc-tile-title')?.textContent.trim(),
    activeMeta: document.querySelector('.toc-tile.active .toc-tile-meta')?.textContent.trim(),
    paragraphs: document.querySelectorAll('.source-doc .source-para').length,
  }));

  assert(sourceState.title === 'Volume 1', 'source title did not load');
  assert(sourceState.subtitle === 'Journal of Discourses', 'source subtitle did not load');
  assert(
    /Journal of Discourses/i.test(sourceState.location) && /Volume\s*1/i.test(sourceState.location),
    'source breadcrumbs did not reflect Journal of Discourses Volume 1'
  );
  assert(sourceState.activeTile === 'Volume 1', 'source tile did not become active');
  assert(sourceState.activeMeta === 'Journal of Discourses', 'source tile meta did not render');
  assert(sourceState.paragraphs > 50, 'source document rendered too few paragraphs');

  await page.waitForSelector('.source-doc .source-para span.w', { timeout: 20000 });
  await page.$eval('.source-doc .source-para span.w', (el) => el.click());
  await page.waitForFunction(() => document.querySelector('#channel').classList.contains('open'), { timeout: 15000 });

  const jdWordState = await page.evaluate(() => ({
    word: document.querySelector('#ch-word')?.textContent.trim(),
    morsels: document.querySelectorAll('#panel-body .ch-morsel').length,
    firstSource: document.querySelector('#panel-body .ch-morsel .ch-src-name')?.textContent.trim(),
  }));

  assert(jdWordState.word, 'JD word click did not set channel word');
  assert(jdWordState.morsels > 0, 'JD word click opened an empty channel');
  assert(jdWordState.firstSource, 'JD word click did not render channel sources');
  await page.$eval('#ch-close', (el) => el.click());
  await page.waitForFunction(() => !document.querySelector('#channel').classList.contains('open'));

  await tocBackToSourcesShelf(page);

  await page.$eval('.toc-tile[data-action="source-collection"][data-collection="times_and_seasons"]', (el) => el.click());
  await page.waitForFunction(() =>
    document.querySelector('#toc-title').textContent === 'Sources' &&
    document.querySelector('#toc-subtitle').textContent === 'Times and Seasons'
  );
  await page.$eval('.toc-tile[data-action="source-doc"][data-doc="times_and_seasons:times_and_seasons_1839_1846_1839_july_vol_01_no_01"]', (el) => el.click());
  await page.waitForSelector('.source-doc .source-title', { timeout: 20000 });
  const tsState = await page.evaluate(() => ({
    title: document.querySelector('.source-doc .source-title')?.textContent.trim() || '',
    subtitle: document.querySelector('.source-doc .source-subtitle')?.textContent.trim() || '',
    activeTile: document.querySelector('.toc-tile.active .toc-tile-title')?.textContent.trim() || '',
    activeMeta: document.querySelector('.toc-tile.active .toc-tile-meta')?.textContent.trim() || '',
  }));
  assert(tsState.title === 'July 1839', 'Times and Seasons title did not become primary');
  assert(tsState.subtitle === 'Vol. 1 · No. 1', 'Times and Seasons metadata did not move into subtitle');
  assert(tsState.activeTile === 'July 1839', 'Times and Seasons tile title did not update');
  assert(tsState.activeMeta === 'Vol. 1 · No. 1', 'Times and Seasons tile meta did not update');
  await tocBackToSourcesShelf(page);
  await page.$eval('.toc-tile[data-action="source-collection"][data-collection="history_of_church"]', (el) => el.click());
  await page.waitForFunction(() =>
    document.querySelector('#toc-title').textContent === 'Sources' &&
    document.querySelector('#toc-subtitle').textContent === 'History of the Church'
  );

  await page.$eval('.toc-tile[data-action="source-doc"][data-doc="history_of_church:vol1"]', (el) => el.click());
  await page.waitForSelector('.source-doc .source-title', { timeout: 20000 });
  await page.waitForSelector('.source-doc .source-para span.w', { timeout: 20000 });
  await page.$eval('.source-doc .source-para span.w', (el) => el.click());
  await page.waitForFunction(() => document.querySelector('#channel').classList.contains('open'), { timeout: 15000 });

  const hocWordState = await page.evaluate(() => ({
    word: document.querySelector('#ch-word')?.textContent.trim(),
    morsels: document.querySelectorAll('#panel-body .ch-morsel').length,
    firstSource: document.querySelector('#panel-body .ch-morsel .ch-src-name')?.textContent.trim(),
    firstText: document.querySelector('#panel-body .ch-morsel .ch-morsel-text')?.textContent.trim() || '',
  }));

  assert(hocWordState.word, 'HoC word click did not set channel word');
  assert(hocWordState.morsels > 0, 'HoC word click opened an empty channel');
  assert(hocWordState.firstSource, 'HoC word click did not render channel sources');
  assert(!/Deutschland/i.test(hocWordState.firstText), 'HoC regression returned unrelated Gutenberg text');
  await page.$eval('#ch-close', (el) => el.click());
  await page.waitForFunction(() => !document.querySelector('#channel').classList.contains('open'));

  await tocBackToSourcesShelf(page);
  await page.$eval('.toc-tile[data-action="volume"][data-volume="New Testament"]', (el) => el.click());
  await page.$eval('.toc-tile[data-action="book"][data-book="John"]', (el) => el.click());
  await page.$eval('.toc-tile[data-action="chapter"][data-id="john_3"]', (el) => el.click());
  await page.waitForSelector('#ch-john_3', { timeout: 20000 });

  const scriptureState = await page.evaluate(() => ({
    sourceVisible: !!document.querySelector('.source-doc'),
    chapterVisible: !!document.querySelector('#ch-john_3'),
    location: document.getElementById('breadcrumbs')?.innerText.replace(/\s+/g, ' ').trim() || '',
    tocSubtitle: document.querySelector('#toc-subtitle')?.textContent.trim(),
  }));

  assert(!scriptureState.sourceVisible, 'source reader remained visible after returning to scripture');
  assert(scriptureState.chapterVisible, 'John 3 did not render after switching back from source');
  assert(
    /John/i.test(scriptureState.location) && /\b3\b/.test(scriptureState.location),
    'scripture breadcrumbs did not recover after source view'
  );
  assert(scriptureState.tocSubtitle === 'John', 'TOC did not return to scripture chapter view');

  await page.click('#v1');
  await page.waitForSelector('#v1 span.w', { timeout: 20000 });
  await page.evaluate(() => {
    const spans = Array.from(document.querySelectorAll('#v1 span.w'));
    const target = spans.find((el) => /pharisees?/i.test(el.textContent || '')) || spans[0];
    if (target) target.dispatchEvent(new MouseEvent('click', { bubbles: true }));
  });
  await page.waitForFunction(() => document.querySelector('#channel').classList.contains('open'), { timeout: 15000 });
  await page.waitForFunction(() => {
    return Array.from(document.querySelectorAll('#panel-body .ch-morsel .ch-src-name')).some((el) =>
      /Journal of Discourses|General Conference|History of the Church/i.test(el.textContent || '')
    );
  }, { timeout: 15000 });

  const sourceMorselIndex = await page.evaluate(() => {
    const morsels = Array.from(document.querySelectorAll('#panel-body .ch-morsel'));
    return morsels.findIndex((el) =>
      /Journal of Discourses|General Conference|History of the Church/i.test(
        el.querySelector('.ch-src-name')?.textContent || ''
      )
    );
  });
  assert(sourceMorselIndex >= 0, 'scripture word click did not surface a source morsel');

  await page.$eval(`#panel-body .ch-morsel[data-idx="${sourceMorselIndex}"]`, (el) => el.click());
  await page.waitForSelector('.source-doc .source-title', { timeout: 20000 });
  await page.waitForFunction(() => {
    const focused = document.querySelector('.source-para-focus');
    return !!(focused && (focused.textContent || '').trim().length > 80);
  }, { timeout: 15000 });

  const scriptureToSourceState = await page.evaluate(() => ({
    sourceTitle: document.querySelector('.source-doc .source-title')?.textContent.trim(),
    sourceSubtitle: document.querySelector('.source-doc .source-subtitle')?.textContent.trim(),
    location: document.getElementById('breadcrumbs')?.innerText.replace(/\s+/g, ' ').trim() || '',
    activeTile: document.querySelector('.toc-tile.active .toc-tile-title')?.textContent.trim(),
    activeMeta: document.querySelector('.toc-tile.active .toc-tile-meta')?.textContent.trim(),
    previewHidden: document.querySelector('#morsel-preview')?.hidden,
    focusedText: document.querySelector('.source-para-focus')?.textContent.trim() || '',
    focusBg: getComputedStyle(document.querySelector('.source-para-focus')).backgroundColor,
  }));

  assert(scriptureToSourceState.sourceTitle, 'source morsel click did not open a source doc');
  assert(scriptureToSourceState.sourceSubtitle, 'source morsel click did not preserve the source subtitle');
  assert(
    scriptureToSourceState.location.indexOf(scriptureToSourceState.sourceTitle) !== -1,
    'source morsel click did not preserve breadcrumbs for the opened document'
  );
  assert(scriptureToSourceState.activeTile === scriptureToSourceState.sourceTitle, 'source morsel click did not preserve the active source title tile');
  assert(scriptureToSourceState.activeMeta === scriptureToSourceState.sourceSubtitle, 'source morsel click did not preserve the active source meta tile');
  assert(scriptureToSourceState.previewHidden, 'source morsel click fell back to the preview card');
  assert(scriptureToSourceState.focusedText.length > 80, 'source morsel click did not focus a relevant paragraph');
  assert(scriptureToSourceState.focusBg !== 'rgba(0, 0, 0, 0)' && scriptureToSourceState.focusBg !== 'transparent', 'source morsel focus paragraph did not render a visible context highlight');

  await page.waitForSelector('.source-doc span.w', { timeout: 20000 });
  await page.evaluate(() => {
    const spans = Array.from(document.querySelectorAll('.source-doc span.w'));
    const target = spans.find((el) => /lord|children|gift|jesus/i.test(el.textContent || '')) || spans[0];
    if (target) target.dispatchEvent(new MouseEvent('click', { bubbles: true }));
  });
  await page.waitForFunction(() => document.querySelector('#channel').classList.contains('open'), { timeout: 15000 });
  const secondSourceMorselIndex = await page.evaluate(() => {
    const morsels = Array.from(document.querySelectorAll('#panel-body .ch-morsel'));
    return morsels.findIndex((el) =>
      /Journal of Discourses|History of the Church|General Conference/i.test(
        el.querySelector('.ch-src-name')?.textContent || ''
      )
    );
  });
  assert(secondSourceMorselIndex >= 0, 'source word click did not surface a second source morsel');
  await page.$eval(`#panel-body .ch-morsel[data-idx="${secondSourceMorselIndex}"]`, (el) => el.click());
  await page.waitForSelector('.source-doc .source-title', { timeout: 20000 });
  const sourceToSourceState = await page.evaluate(() => ({
    sourceTitle: document.querySelector('.source-doc .source-title')?.textContent.trim() || '',
    sourceSubtitle: document.querySelector('.source-doc .source-subtitle')?.textContent.trim() || '',
    location: document.getElementById('breadcrumbs')?.innerText.replace(/\s+/g, ' ').trim() || '',
    activeTile: document.querySelector('.toc-tile.active .toc-tile-title')?.textContent.trim() || '',
    activeMeta: document.querySelector('.toc-tile.active .toc-tile-meta')?.textContent.trim() || '',
    focusedText: document.querySelector('.source-para-focus')?.textContent.trim() || '',
  }));
  assert(sourceToSourceState.sourceTitle, 'second source morsel click did not open a source doc');
  assert(sourceToSourceState.sourceSubtitle, 'second source morsel click did not preserve the source subtitle');
  assert(
    sourceToSourceState.location.indexOf(sourceToSourceState.sourceTitle) !== -1,
    'second source morsel click did not preserve breadcrumbs for the opened document'
  );
  assert(sourceToSourceState.activeTile === sourceToSourceState.sourceTitle, 'second source morsel click did not preserve the active source title tile');
  assert(sourceToSourceState.activeMeta === sourceToSourceState.sourceSubtitle, 'second source morsel click did not preserve the active source meta tile');
  assert(sourceToSourceState.focusedText.length > 80, 'second source morsel click did not focus a relevant paragraph');

  await page.$eval('#toc-back', (el) => el.click());
  await page.$eval('.toc-tile[data-action="volume"][data-volume="New Testament"]', (el) => el.click());
  await page.$eval('.toc-tile[data-action="book"][data-book="John"]', (el) => el.click());
  await page.$eval('.toc-tile[data-action="chapter"][data-id="john_3"]', (el) => el.click());
  await page.waitForSelector('#ch-john_3', { timeout: 20000 });
  await page.click('#v1');
  await page.waitForSelector('#v1 span.w', { timeout: 20000 });
  await page.evaluate(() => {
    const spans = Array.from(document.querySelectorAll('#v1 span.w'));
    const target = spans.find((el) => /pharisees?/i.test(el.textContent || '')) || spans[0];
    if (target) target.dispatchEvent(new MouseEvent('click', { bubbles: true }));
  });
  await page.waitForFunction(() => document.querySelector('#channel').classList.contains('open'), { timeout: 15000 });

  const rankingState = await page.evaluate(() => ({
    word: document.querySelector('#ch-word')?.textContent.trim(),
    firstSource: document.querySelector('.ch-morsel .ch-src-name')?.textContent.trim() || '',
    morsels: Array.from(document.querySelectorAll('.ch-morsel')).slice(0, 3).map((el) => ({
      src: el.querySelector('.ch-src-name')?.textContent.trim() || '',
      text: el.querySelector('.ch-morsel-text')?.textContent.trim() || '',
    })),
  }));

  assert(rankingState.word === 'pharisee', 'ranking regression used the wrong scripture word');
  assert(rankingState.firstSource === 'Standard Works', 'scripture-first ranking regressed behind commentary/source results');
  assert(rankingState.morsels.every((m) => m.src === 'Standard Works'), 'scripture-first ranking no longer pins the first scripture tranche');

  await page.$eval('#ch-close', (el) => el.click());
  await page.click('#v16');
  await page.waitForSelector('#v16 span.w', { timeout: 20000 });
  await page.evaluate(() => {
    const target = Array.from(document.querySelectorAll('#v16 span.w')).find((el) => /god/i.test(el.textContent || ''));
    if (target) target.dispatchEvent(new MouseEvent('click', { bubbles: true }));
  });
  await page.waitForFunction(() => document.querySelector('#channel').classList.contains('open'), { timeout: 15000 });
  await page.waitForFunction(() => {
    const study = document.querySelector('#ch-study');
    return !!(study && !study.hidden && /theos|θε|deity|god|supreme/i.test(study.textContent || ''));
  }, { timeout: 15000 });

  const strongsState = await page.evaluate(() => ({
    word: document.querySelector('#ch-word')?.textContent.trim(),
    study: document.querySelector('#ch-study')?.textContent.trim() || '',
  }));

  assert(/god/i.test(strongsState.word), 'word-study regression used the wrong scripture word');
  assert(
    /theos|θε|deity|god|supreme/i.test(strongsState.study),
    'word study panel did not show Greek/lexical content for John 3:16 (concordance numbers are not shown)',
  );
  await page.$eval('#ch-close', (el) => el.click());
  await page.waitForFunction(() => !document.querySelector('#channel').classList.contains('open'));

  await page.evaluate(() => jumpTo('genesis_2'));
  await page.waitForSelector('#v6 .verse-text .w', { timeout: 20000 });
  await page.evaluate(() => {
    const target = Array.from(document.querySelectorAll('#v6 .verse-text .w')).find((el) => /mist/i.test(el.textContent || ''));
    if (target) target.dispatchEvent(new MouseEvent('click', { bubbles: true }));
  });
  await page.waitForFunction(() => document.querySelector('#channel').classList.contains('open'), { timeout: 15000 });
  const mistState = await page.evaluate(() => ({
    word: document.querySelector('#ch-word')?.textContent.trim(),
    firstSource: document.querySelector('.ch-morsel .ch-src-name')?.textContent.trim() || '',
  }));
  assert(/mist/i.test(mistState.word), 'scripture fallback regression used the wrong Genesis 2 word');
  assert(mistState.firstSource === 'Standard Works', 'Genesis 2 mist did not prioritize standard works fallback');
  await page.$eval('#ch-close', (el) => el.click());
  await page.waitForFunction(() => !document.querySelector('#channel').classList.contains('open'));

  const genesisCleanState = await page.evaluate(() => ({
    v6: document.querySelector('#v6 .verse-text')?.innerText || '',
    v7: document.querySelector('#v7 .verse-text')?.innerText || '',
    v7Html: document.querySelector('#v7 .verse-text')?.innerHTML || '',
  }));
  assert(/there went up a mist from the earth/i.test(genesisCleanState.v6), 'Genesis 2:6 did not restore full canonical verse text');
  assert(/breath of life; and man became a living soul/i.test(genesisCleanState.v7), 'Genesis 2:7 did not restore full canonical verse text');
  assert(!/&lt;span class=|&amp;quot;cw/i.test(genesisCleanState.v7Html), 'Genesis 2 still leaks escaped critical-word wrappers');

  await page.evaluate(() => jumpTo('john_3'));
  await page.waitForSelector('#v16 .verse-text .w', { timeout: 20000 });
  await page.evaluate(() => {
    const target = Array.from(document.querySelectorAll('#v16 .verse-text .w')).find((el) => /loved/i.test(el.textContent || ''));
    if (target) target.dispatchEvent(new MouseEvent('click', { bubbles: true }));
  });
  await page.waitForFunction(() => document.querySelector('#channel').classList.contains('open'), { timeout: 15000 });
  const loveState = await page.evaluate(() => ({
    word: document.querySelector('#ch-word')?.textContent.trim(),
    sources: Array.from(document.querySelectorAll('.ch-morsel .ch-src-name')).slice(0, 3).map((el) => el.textContent.trim()),
  }));
  assert(/lov/i.test(loveState.word), 'scripture fallback regression used the wrong John 3 word');
  assert(loveState.sources[0] === 'Standard Works', 'John 3 loved did not rank standard works first');
  await page.$eval('#ch-close', (el) => el.click());
  await page.waitForFunction(() => !document.querySelector('#channel').classList.contains('open'));

  await page.evaluate(() => jumpTo('john_1'));
  await page.waitForSelector('#v1 .verse-text', { timeout: 20000 });
  const johnCleanState = await page.evaluate(() => ({
    v1: document.querySelector('#v1 .verse-text')?.innerText || '',
    v17: document.querySelector('#v17 .verse-text')?.innerText || '',
    v1Html: document.querySelector('#v1 .verse-text')?.innerHTML || '',
  }));
  assert(/In the beginning was the Word/i.test(johnCleanState.v1), 'John 1:1 did not restore full canonical verse text');
  assert(/grace and truth came by Jesus Christ/i.test(johnCleanState.v17), 'John 1:17 did not restore full canonical verse text');
  assert(!/&lt;span class=|&amp;quot;cw/i.test(johnCleanState.v1Html), 'John 1 still leaks escaped critical-word wrappers');

  await page.evaluate(() => jumpTo('2_thessalonians_2'));
  await page.waitForSelector('#v1 .verse-text', { timeout: 20000 });
  const secondThessCleanState = await page.evaluate(() => ({
    v1: document.querySelector('#v1 .verse-text')?.innerText || '',
    v3: document.querySelector('#v3 .verse-text')?.innerText || '',
    v3Html: document.querySelector('#v3 .verse-text')?.innerHTML || '',
  }));
  assert(/Now we beseech you, brethren/i.test(secondThessCleanState.v1), '2 Thessalonians 2:1 did not restore full canonical verse text');
  assert(/that man of sin be revealed, the son of perdition/i.test(secondThessCleanState.v3), '2 Thessalonians 2:3 did not restore full canonical verse text');
  assert(!/&lt;span class=|&amp;quot;cw/i.test(secondThessCleanState.v3Html), '2 Thessalonians still leaks escaped critical-word wrappers');

  await page.evaluate(() => jumpTo('1_nephi_8'));
  await page.waitForSelector('#v23 .verse-text .w', { timeout: 20000 });
  await page.evaluate(() => {
    const target = Array.from(document.querySelectorAll('#v23 .verse-text .w')).find((el) => /mist/i.test(el.textContent || ''));
    if (target) target.dispatchEvent(new MouseEvent('click', { bubbles: true }));
  });
  await page.waitForFunction(() => document.querySelector('#channel').classList.contains('open'), { timeout: 15000 });
  const nephiMistState = await page.evaluate(() => ({
    word: document.querySelector('#ch-word')?.textContent.trim(),
    sources: Array.from(document.querySelectorAll('.ch-morsel .ch-src-name')).slice(0, 3).map((el) => el.textContent.trim()),
    texts: Array.from(document.querySelectorAll('.ch-morsel .ch-morsel-text')).slice(0, 3).map((el) => el.textContent.trim()),
  }));
  assert(/mist/i.test(nephiMistState.word), 'Book of Mormon fallback regression used the wrong 1 Nephi word');
  assert(nephiMistState.sources[0] === 'Standard Works', '1 Nephi mist did not rank standard works first');
  assert(nephiMistState.texts.some((text) => /mist of darkness|fell on him a mist/i.test(text)), '1 Nephi mist did not surface scripture fallback morsels');
  await page.$eval('#ch-close', (el) => el.click());
  await page.waitForFunction(() => !document.querySelector('#channel').classList.contains('open'));

  await page.evaluate(() => jumpTo('doctrine_and_covenants_121'));
  await page.waitForSelector('#v41 .verse-text .w', { timeout: 20000 });
  await page.evaluate(() => {
    const target = Array.from(document.querySelectorAll('#v41 .verse-text .w')).find((el) => /priesthood/i.test(el.textContent || ''));
    if (target) target.dispatchEvent(new MouseEvent('click', { bubbles: true }));
  });
  await page.waitForFunction(() => document.querySelector('#channel').classList.contains('open'), { timeout: 15000 });
  const dcPriesthoodState = await page.evaluate(() => ({
    word: document.querySelector('#ch-word')?.textContent.trim(),
    sources: Array.from(document.querySelectorAll('.ch-morsel .ch-src-name')).slice(0, 3).map((el) => el.textContent.trim()),
    texts: Array.from(document.querySelectorAll('.ch-morsel .ch-morsel-text')).slice(0, 3).map((el) => el.textContent.trim()),
  }));
  assert(/priesthood/i.test(dcPriesthoodState.word), 'D&C fallback regression used the wrong Doctrine and Covenants word');
  assert(dcPriesthoodState.sources[0] === 'Standard Works', 'Doctrine and Covenants priesthood did not rank standard works first');
  assert(dcPriesthoodState.texts.some((text) => /Priesthood of thy father|Melchizedek Priesthood|higher, or Melchizedek Priesthood/i.test(text)), 'Doctrine and Covenants priesthood did not surface scripture fallback morsels');
  await page.$eval('#ch-close', (el) => el.click());
  await page.waitForFunction(() => !document.querySelector('#channel').classList.contains('open'));

  await page.evaluate(() => {
    const target = Array.from(document.querySelectorAll('#v41 .verse-text .w')).find((el) => /^love$/i.test((el.textContent || '').trim()));
    if (target) target.dispatchEvent(new MouseEvent('click', { bubbles: true }));
  });
  await page.waitForFunction(() => document.querySelector('#channel').classList.contains('open'), { timeout: 15000 });
  const dcLoveCleanState = await page.evaluate(() => ({
    word: document.querySelector('#ch-word')?.textContent.trim(),
    sources: Array.from(document.querySelectorAll('.ch-morsel .ch-src-name')).slice(0, 3).map((el) => el.textContent.trim()),
    verseText: document.querySelector('#v41 .verse-text')?.innerText || '',
    verseHtml: document.querySelector('#v41 .verse-text')?.innerHTML || '',
  }));
  assert(/love/i.test(dcLoveCleanState.word), 'D&C clean re-annotation did not make love clickable');
  assert(dcLoveCleanState.sources[0] === 'Standard Works', 'Doctrine and Covenants love did not rank standard works first after re-annotation');
  assert(!/&lt;span class=|&amp;quot;cw/i.test(dcLoveCleanState.verseHtml), 'Doctrine and Covenants verse HTML still leaks escaped critical-word wrappers');
  await page.$eval('#ch-close', (el) => el.click());
  await page.waitForFunction(() => !document.querySelector('#channel').classList.contains('open'));

  console.log(JSON.stringify({ rootTiles, timesState, starState, enumaState, enochState, josephusState, sourceState, jdWordState, hocWordState, scriptureState, scriptureToSourceState, rankingState, strongsState, mistState, genesisCleanState, loveState, johnCleanState, secondThessCleanState, nephiMistState, dcPriesthoodState, dcLoveCleanState }, null, 2));
  await browser.close();
}

run().catch((error) => {
  console.error(error.stack || String(error));
  process.exit(1);
});
