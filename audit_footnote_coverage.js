const fs = require('fs');
const path = require('path');

// Parse all footnotes files and generate coverage report
const footnotesDir = './library/footnotes';
const donaldsonDir = './library/donaldson';

const files = fs.readdirSync(footnotesDir).filter(f => f.endsWith('.json'));
console.log(`Found ${files.length} footnote files`);

// Structure: { bookName: { totalVerses, versesWithFootnotes, sourceBreakdown: {} } }
const coverage = {};
const allBooks = new Set();

files.forEach(file => {
  const [book, chapter] = file.replace('.json', '').split('_');
  if (!book) return;

  const bookName = book.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  allBooks.add(bookName);

  if (!coverage[bookName]) {
    coverage[bookName] = {
      totalVerses: 0,
      versesWithFootnotes: 0,
      versesWithDonaldson: 0,
      versesWithExtracted: 0,
      donaldsonOnly: 0,
      extractedOnly: 0,
      both: 0,
      gapVerses: []
    };
  }

  const footnotePath = path.join(footnotesDir, file);
  const donaldsonPath = path.join(donaldsonDir, file);

  let footnoteData = {};
  let donaldsonData = {};

  try {
    const content = fs.readFileSync(footnotePath, 'utf-8');
    footnoteData = JSON.parse(content);
  } catch (e) {
    console.error(`Error reading ${file}:`, e.message);
  }

  try {
    if (fs.existsSync(donaldsonPath)) {
      const content = fs.readFileSync(donaldsonPath, 'utf-8');
      donaldsonData = JSON.parse(content);
    }
  } catch (e) {}

  // Count verses in this chapter
  const verseNums = Object.keys(footnoteData);
  verseNums.forEach(vNum => {
    coverage[bookName].totalVerses++;
    const entry = footnoteData[vNum] || {};
    const hasFootnote = (entry.notes && entry.notes.length > 0) ||
                        (entry.quotes && entry.quotes.length > 0) ||
                        (entry.words && entry.words.length > 0);

    if (hasFootnote) {
      coverage[bookName].versesWithFootnotes++;
    } else {
      coverage[bookName].gapVerses.push(`${bookName} ${chapter}:${vNum}`);
    }

    const donaldsonEntry = donaldsonData[vNum] || {};
    const hasDonaldson = (donaldsonEntry.notes && donaldsonEntry.notes.length > 0) ||
                         (donaldsonEntry.quotes && donaldsonEntry.quotes.length > 0);
    const hasExtracted = (entry.quotes && entry.quotes.length > 0);

    if (hasDonaldson) coverage[bookName].versesWithDonaldson++;
    if (hasExtracted) coverage[bookName].versesWithExtracted++;

    if (hasDonaldson && hasExtracted) {
      coverage[bookName].both++;
    } else if (hasDonaldson) {
      coverage[bookName].donaldsonOnly++;
    } else if (hasExtracted) {
      coverage[bookName].extractedOnly++;
    }
  });
});

// Generate markdown report
let report = '# Footnote Coverage Report\n\n';
report += `Generated: ${new Date().toISOString()}\n`;
report += `Total books: ${allBooks.size}\n`;
report += `Total footnote files: ${files.length}\n\n`;

// Summary statistics
let totalVerses = 0;
let totalWithFootnotes = 0;
let totalWithDonaldson = 0;
let totalWithExtracted = 0;

Object.values(coverage).forEach(stats => {
  totalVerses += stats.totalVerses;
  totalWithFootnotes += stats.versesWithFootnotes;
  totalWithDonaldson += stats.versesWithDonaldson;
  totalWithExtracted += stats.versesWithExtracted;
});

report += `## Overall Statistics\n`;
report += `- Total verses: ${totalVerses.toLocaleString()}\n`;
report += `- Verses with ≥1 footnote: ${totalWithFootnotes.toLocaleString()} (${(totalWithFootnotes/totalVerses*100).toFixed(1)}%)\n`;
report += `- Donaldson commentary coverage: ${totalWithDonaldson.toLocaleString()} (${(totalWithDonaldson/totalVerses*100).toFixed(1)}%)\n`;
report += `- Extracted sources coverage: ${totalWithExtracted.toLocaleString()} (${(totalWithExtracted/totalVerses*100).toFixed(1)}%)\n`;
report += `- Both sources: ${Object.values(coverage).reduce((s,b) => s + b.both, 0)} (${(Object.values(coverage).reduce((s,b) => s + b.both, 0)/totalVerses*100).toFixed(1)}%)\n\n`;

report += `## Per-Book Breakdown\n\n`;
report += `| Book | Verses | With Footnotes | Coverage % | Donaldson | Extracted | Both | Gaps |\n`;
report += `|------|--------|---|---|---|---|---|---|\n`;

const sortedBooks = Array.from(allBooks).sort();
sortedBooks.forEach(book => {
  const stats = coverage[book];
  const coveragePercent = (stats.versesWithFootnotes / stats.totalVerses * 100).toFixed(1);
  const gaps = stats.gapVerses.length;
  report += `| ${book} | ${stats.totalVerses} | ${stats.versesWithFootnotes} | ${coveragePercent}% | ${stats.versesWithDonaldson} | ${stats.versesWithExtracted} | ${stats.both} | ${gaps} |\n`;
});

report += `\n## Books with Lowest Coverage\n\n`;
const lowestCoverage = sortedBooks
  .map(book => ({ book, coverage: coverage[book] }))
  .sort((a, b) => (a.coverage.versesWithFootnotes / a.coverage.totalVerses) - (b.coverage.versesWithFootnotes / b.coverage.totalVerses))
  .slice(0, 5);

lowestCoverage.forEach(({ book, coverage: stats }) => {
  const coveragePercent = (stats.versesWithFootnotes / stats.totalVerses * 100).toFixed(1);
  report += `- **${book}**: ${coveragePercent}% (${stats.versesWithFootnotes}/${stats.totalVerses} verses)\n`;
  if (stats.gapVerses.length > 0 && stats.gapVerses.length <= 10) {
    report += `  - Gaps: ${stats.gapVerses.join(', ')}\n`;
  } else if (stats.gapVerses.length > 10) {
    report += `  - ${stats.gapVerses.length} verses without footnotes\n`;
  }
});

// Write report
fs.writeFileSync('./diagnostics/footnote-coverage.md', report);
console.log('\nReport written to diagnostics/footnote-coverage.md');
console.log(`Overall coverage: ${(totalWithFootnotes/totalVerses*100).toFixed(1)}%`);
