const fs = require('fs');
const path = require('path');

const footnotesDir = './library/footnotes';
const files = fs.readdirSync(footnotesDir).filter(f => f.endsWith('.json'));

// Group by scripture section
const sections = {
  OT: ['genesis', 'exodus', 'leviticus', 'numbers', 'deuteronomy', 'joshua', 'judges', 
       'samuel', 'kings', 'chronicles', 'ezra', 'nehemiah', 'esther', 'job', 'psalms', 
       'proverbs', 'ecclesiastes', 'song', 'isaiah', 'jeremiah', 'lamentations', 'ezekiel',
       'daniel', 'hosea', 'joel', 'amos', 'obadiah', 'jonah', 'micah', 'nahum', 'habakkuk',
       'zephaniah', 'haggai', 'zechariah', 'malachi'],
  NT: ['matthew', 'mark', 'luke', 'john', 'acts', 'romans', 'corinthians', 'galatians',
       'ephesians', 'philippians', 'colossians', 'thessalonians', 'timothy', 'titus',
       'philemon', 'hebrews', 'james', 'peter', 'john', 'jude', 'revelation'],
  BoM: ['nephi', 'jacob', 'enos', 'jarom', 'omni', 'mosiah', 'alma', 'helaman', 'mormon', 'ether', 'moroni'],
  DandC: ['dandc', 'moses', 'abraham']
};

// Get all unique books
const allBooks = new Set();
files.forEach(f => {
  const [book] = f.replace('.json', '').split('_');
  allBooks.add(book.toLowerCase());
});

// Sample books by section
const sample = [];
const samplePerSection = 10; // ~10 per section = ~40 total

for (const [section, bookPrefixes] of Object.entries(sections)) {
  const sectionBooks = Array.from(allBooks).filter(b => 
    bookPrefixes.some(p => b.includes(p))
  );
  
  if (sectionBooks.length === 0) continue;

  for (let i = 0; i < samplePerSection; i++) {
    // Random book
    const book = sectionBooks[Math.floor(Math.random() * sectionBooks.length)];
    
    // Get all files for this book
    const bookFiles = files.filter(f => f.startsWith(book + '_'));
    if (bookFiles.length === 0) continue;

    // Random chapter
    const file = bookFiles[Math.floor(Math.random() * bookFiles.length)];
    const [, chapter] = file.replace('.json', '').split('_');

    // Load and get random verse
    try {
      const data = JSON.parse(fs.readFileSync(path.join(footnotesDir, file), 'utf-8'));
      const verses = Object.keys(data);
      if (verses.length === 0) continue;

      const vNum = verses[Math.floor(Math.random() * verses.length)];
      const bookName = book.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
      
      sample.push({
        ref: `${bookName} ${chapter}:${vNum}`,
        book,
        chapter,
        verse: vNum,
        section
      });
    } catch (e) {
      console.error(`Error reading ${file}:`, e.message);
    }
  }
}

// Keep unique and shuffle
const unique = Array.from(new Map(sample.map(s => [s.ref, s])).values());
unique.sort(() => Math.random() - 0.5);

console.log(`\n# Quality Sample: ${unique.length} Verses\n`);
console.log('| Ref | Section | File |');
console.log('|---|---|---|');
unique.slice(0, 40).forEach(s => {
  console.log(`| ${s.ref} | ${s.section} | ${s.book}_${s.chapter}.json |`);
});

// Save to file for reference
fs.writeFileSync('./diagnostics/sample-verses.json', JSON.stringify(unique.slice(0, 40), null, 2));
console.log('\nSample saved to diagnostics/sample-verses.json');
