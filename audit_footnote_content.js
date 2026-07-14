const fs = require('fs');
const path = require('path');

// Random sample with different seed
const seed = 42; // Different from coordinator's seed 99
Math.seedrandom = function(seed) {
  let x = Math.sin(seed++) * 10000;
  return x - Math.floor(x);
};

const footnotesDir = './library/footnotes';
const files = fs.readdirSync(footnotesDir).filter(f => f.endsWith('.json'));

// Deterministic shuffle with seed
function shuffleWithSeed(arr, seed) {
  let rng = seed;
  const result = [...arr];
  for (let i = result.length - 1; i > 0; i--) {
    rng = (rng * 9301 + 49297) % 233280;
    const j = Math.floor((rng / 233280) * (i + 1));
    [result[i], result[j]] = [result[j], result[i]];
  }
  return result;
}

// Sample books and verses
const allVerses = [];
files.forEach(file => {
  const [book, chapter] = file.replace('.json', '').split('_');
  try {
    const data = JSON.parse(fs.readFileSync(path.join(footnotesDir, file), 'utf-8'));
    Object.keys(data).forEach(vNum => {
      allVerses.push({
        file,
        book,
        chapter,
        verse: vNum,
        ref: `${book.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())} ${chapter}:${vNum}`
      });
    });
  } catch (e) {}
});

const sampled = shuffleWithSeed(allVerses, seed).slice(0, 40);

console.log(`Sampled ${sampled.length} verses\n`);

// Review for content defects
const defects = {
  orphaned_citation: [],      // Note starting with lowercase/citation pattern
  truncated_midsentence: [],  // Note ending mid-word or starting lowercase
  verse_text_leak: [],        // Note is the actual verse
  no_attribution: [],         // No source/author
  total_checked: 0,
  total_issues: 0
};

sampled.forEach(sample => {
  const file = path.join(footnotesDir, sample.file);
  try {
    const data = JSON.parse(fs.readFileSync(file, 'utf-8'));
    const entry = data[sample.verse];

    if (!entry) return;

    defects.total_checked++;

    const notes = entry.notes || [];
    const quotes = entry.quotes || [];

    // Check notes for defects
    notes.forEach(note => {
      if (!note) return;

      let note_issues = [];

      // Orphaned citation tail
      if (note[0] && note[0].match(/[a-z]/)) {
        note_issues.push('orphaned_citation');
      } else if (note.match(/^(or |and |cf\. |Bednar|Ensign|Conference|see )/i)) {
        note_issues.push('orphaned_citation');
      } else if (note.match(/^\([A-Z]/)) {
        note_issues.push('orphaned_citation');
      }

      // Mid-sentence truncation (ends with lowercase or word fragment)
      if (note.match(/[a-z]\s*$/) && !note.match(/[.!?\)]\s*$/)) {
        note_issues.push('truncated_midsentence');
      }

      // All lowercase start = fragment
      if (note[0] && note[0].match(/[a-z]/)) {
        note_issues.push('truncated_midsentence');
      }

      note_issues.forEach(issue => {
        defects[issue].push({
          ref: sample.ref,
          text: note.slice(0, 80)
        });
        defects.total_issues++;
      });
    });

    // Check quotes for attribution
    quotes.forEach(q => {
      if (!q.source && !q.attr && !q.author && !q.speaker) {
        defects.no_attribution.push({
          ref: sample.ref,
          text: (q.text || '').slice(0, 80)
        });
        defects.total_issues++;
      }
    });

  } catch (e) {
    console.error(`Error reading ${sample.file}:`, e.message);
  }
});

// Generate report
let report = '# Footnote Content Quality Re-Audit\n\n';
report += `Seed: ${seed} (different from coordinator's 99)\n`;
report += `Sampled: ${defects.total_checked} verses\n`;
report += `Issues found: ${defects.total_issues} (${(defects.total_issues / defects.total_checked * 100).toFixed(1)}%)\n\n`;

report += `## Defect Summary\n`;
report += `- Orphaned citation tails: ${defects.orphaned_citation.length} (${(defects.orphaned_citation.length / defects.total_checked * 100).toFixed(1)}%)\n`;
report += `- Mid-sentence truncation: ${defects.truncated_midsentence.length} (${(defects.truncated_midsentence.length / defects.total_checked * 100).toFixed(1)}%)\n`;
report += `- Missing attribution: ${defects.no_attribution.length} (${(defects.no_attribution.length / defects.total_checked * 100).toFixed(1)}%)\n\n`;

if (defects.orphaned_citation.length > 0) {
  report += `## Orphaned Citation Examples\n`;
  defects.orphaned_citation.slice(0, 5).forEach(d => {
    report += `- ${d.ref}: "${d.text}"\n`;
  });
  report += '\n';
}

if (defects.truncated_midsentence.length > 0) {
  report += `## Truncation Examples\n`;
  defects.truncated_midsentence.slice(0, 5).forEach(d => {
    report += `- ${d.ref}: "${d.text}"\n`;
  });
  report += '\n';
}

report += `## Sample Verses (OK)\n`;
const okVerses = sampled.filter(s => {
  const file = path.join(footnotesDir, s.file);
  const data = JSON.parse(fs.readFileSync(file, 'utf-8'));
  const entry = data[s.verse];
  const notes = entry.notes || [];
  return notes.length === 0 || !notes.some(n => n && (n[0].match(/[a-z]/) || n.match(/^(or |and )/)));
});

okVerses.slice(0, 10).forEach(s => {
  report += `- ${s.ref}\n`;
});

fs.writeFileSync('./diagnostics/footnote-content-audit.md', report);
console.log('\n' + report);
console.log('Full report: diagnostics/footnote-content-audit.md');
