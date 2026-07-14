const fs = require('fs');
const path = require('path');

const samples = JSON.parse(fs.readFileSync('./diagnostics/sample-verses.json', 'utf-8'));
const footnotesDir = './library/footnotes';

const review = [];
const issues = { truncated: 0, noAttribution: 0, irrelevant: 0, garbled: 0 };

samples.forEach(sample => {
  const file = path.join(footnotesDir, `${sample.book}_${sample.chapter}.json`);
  try {
    const data = JSON.parse(fs.readFileSync(file, 'utf-8'));
    const entry = data[sample.verse];

    if (!entry) {
      review.push({
        ref: sample.ref,
        status: 'MISSING_ENTRY',
        details: 'No footnote entry found'
      });
      return;
    }

    const quotes = entry.quotes || [];
    const notes = entry.notes || [];

    // Check for issues
    let issues_found = [];

    // Check for attribution
    if (quotes.length > 0) {
      quotes.forEach(q => {
        if (!q.source && !q.author && !q.speaker) {
          issues_found.push('NO_ATTRIBUTION');
        }
        if (!q.text || q.text.length < 5) {
          issues_found.push('EMPTY_TEXT');
        }
        if (q.text && q.text.endsWith('...')) {
          issues_found.push('TRUNCATED');
        }
      });
    }

    // Sample output: first quote/note
    let sample_text = '';
    if (quotes.length > 0) {
      const q = quotes[0];
      sample_text = `"${(q.text || '').slice(0, 100)}..." (${q.author || q.speaker || 'Unknown'})`;
    } else if (notes.length > 0) {
      sample_text = `NOTE: ${(notes[0] || '').slice(0, 100)}...`;
    }

    review.push({
      ref: sample.ref,
      section: sample.section,
      quoteCount: quotes.length,
      noteCount: notes.length,
      status: issues_found.length > 0 ? 'ISSUES' : 'OK',
      issues: issues_found,
      sample: sample_text
    });

    issues_found.forEach(i => issues[i.toLowerCase()] = (issues[i.toLowerCase()] || 0) + 1);
  } catch (e) {
    review.push({
      ref: sample.ref,
      status: 'ERROR',
      details: e.message
    });
  }
});

// Generate report
let report = '# Footnote Quality Review\n\n';
report += `Reviewed ${review.length} verses\n\n`;

const summary = {
  OK: review.filter(r => r.status === 'OK').length,
  ISSUES: review.filter(r => r.status === 'ISSUES').length,
  MISSING: review.filter(r => r.status === 'MISSING_ENTRY').length,
  ERROR: review.filter(r => r.status === 'ERROR').length
};

report += `## Summary\n`;
report += `- OK: ${summary.OK}/${review.length} (${(summary.OK/review.length*100).toFixed(1)}%)\n`;
report += `- Issues found: ${summary.ISSUES}\n`;
report += `- Missing entries: ${summary.MISSING}\n`;
report += `- Errors: ${summary.ERROR}\n\n`;

if (summary.ISSUES > 0) {
  report += `## Issues Breakdown\n`;
  report += `- Truncated (ending with ...): ${issues['truncated'] || 0}\n`;
  report += `- Missing attribution: ${issues['no_attribution'] || 0}\n`;
  report += `- Empty/short text: ${issues['empty_text'] || 0}\n`;
  report += `- Garbled content: ${issues['garbled'] || 0}\n\n`;

  report += `## Verses with Issues\n\n`;
  review.filter(r => r.status === 'ISSUES').forEach(r => {
    report += `### ${r.ref}\n`;
    report += `Issues: ${r.issues.join(', ')}\n`;
    report += `Sample: ${r.sample.slice(0, 200)}\n\n`;
  });
}

report += `## Sample Verses (OK)\n\n`;
review.filter(r => r.status === 'OK').slice(0, 10).forEach(r => {
  report += `- ${r.ref}: ${r.quoteCount} quotes, ${r.noteCount} notes\n`;
  report += `  ${r.sample.slice(0, 150)}\n\n`;
});

fs.writeFileSync('./diagnostics/footnote-quality-review.md', report);
console.log(report);
console.log('Full report: diagnostics/footnote-quality-review.md');
