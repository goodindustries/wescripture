const { launchBrowser } = require('./tools/puppeteer_launch.js');

(async () => {
  const browser = await launchBrowser();
  const page = await browser.newPage();

  await page.setViewport({ width: 1440, height: 1100, deviceScaleFactor: 1 });
  
  // Check what date the app thinks today is
  await page.goto('http://127.0.0.1:4173/library/index.html', { waitUntil: 'networkidle0', timeout: 60000 });

  // Get today's date from JS
  const todayInfo = await page.evaluate(() => {
    const today = new Date();
    const year = today.getFullYear();
    const month = String(today.getMonth() + 1).padStart(2, '0');
    const day = String(today.getDate()).padStart(2, '0');
    return {
      fullDate: today.toISOString().split('T')[0],
      display: today.toDateString(),
      ymd: `${year}-${month}-${day}`
    };
  });

  console.log('Today according to browser:', todayInfo);

  // Click Today button
  await page.click('#today-btn');
  await new Promise((r) => setTimeout(r, 500));

  // Check what got loaded
  const loadedChapter = await page.evaluate(() => {
    const header = document.querySelector('[data-current-chapter]');
    const title = document.querySelector('h2') || document.querySelector('h3');
    return {
      header: header?.textContent,
      title: title?.textContent,
      displayText: document.body.textContent.slice(0, 500)
    };
  });

  console.log('\nAfter clicking Today:');
  console.log('Loaded chapter:', loadedChapter.title);

  // Look in CFM_2026 to see what week this is
  const cfmData = await page.evaluate(() => {
    return JSON.parse(localStorage.getItem('CFM_2026') || '[]');
  }).catch(() => []);

  // Manually check the CFM_2026 data
  const cfmContent = require('fs').readFileSync('./library/cfm_2026.json', 'utf-8');
  const CFM_2026 = JSON.parse(cfmContent);
  
  const today = new Date('2026-07-13');
  let currentWeek = null;
  CFM_2026.forEach((week, idx) => {
    const startDate = new Date(week.start_date);
    const endDate = new Date(week.end_date);
    if (today >= startDate && today <= endDate) {
      currentWeek = { idx: idx + 1, week, startDate, endDate };
    }
  });

  console.log(`\nCFM_2026 Data for 2026-07-13:`);
  if (currentWeek) {
    console.log(`Week ${currentWeek.idx}: ${currentWeek.week.title}`);
    console.log(`Date range: ${currentWeek.startDate.toISOString().split('T')[0]} to ${currentWeek.endDate.toISOString().split('T')[0]}`);
    console.log(`References: ${currentWeek.week.refs.map(r => `${r.book} ${r.chapter_start}${r.chapter_start !== r.chapter_end ? '-' + r.chapter_end : ''}`).join(', ')}`);
  }

  console.log('\n✓ Today button verification complete');

  await browser.close();
})();
