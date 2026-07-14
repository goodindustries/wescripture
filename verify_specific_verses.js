const fs = require('fs');

// Check the 3 specific verses coordinator found issues with
const testCases = [
  { file: 'library/footnotes/romans_6.json', verse: '4', name: 'Romans 6:4 (orphaned citation tail)' },
  { file: 'library/footnotes/hosea_1.json', verse: '2', name: 'Hosea 1:2 (truncation)' },
  { file: 'library/footnotes/hosea_1.json', verse: '11', name: 'Hosea 1:11 (verse-text leak)' }
];

testCases.forEach(tc => {
  console.log(`\n${tc.name}`);
  console.log('='.repeat(60));

  try {
    const data = JSON.parse(fs.readFileSync(tc.file, 'utf-8'));
    const entry = data[tc.verse];

    if (!entry) {
      console.log('  [No entry found]');
      return;
    }

    if (entry.notes && entry.notes.length > 0) {
      console.log(`  Notes (${entry.notes.length}):`);
      entry.notes.forEach((note, idx) => {
        console.log(`    ${idx + 1}. "${note.slice(0, 100)}${note.length > 100 ? '...' : ''}"`);
      });
    }

    if (entry.quotes && entry.quotes.length > 0) {
      console.log(`  Quotes (${entry.quotes.length}):`);
      entry.quotes.forEach((q, idx) => {
        console.log(`    ${idx + 1}. "${q.text.slice(0, 80)}${q.text.length > 80 ? '...' : ''}"`);
        console.log(`       Source: ${q.source || 'N/A'}`);
      });
    }

  } catch (e) {
    console.log(`  Error: ${e.message}`);
  }
});
