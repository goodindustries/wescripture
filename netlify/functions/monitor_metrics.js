const fs = require("fs");
const path = require("path");

function readJson(p) {
  return JSON.parse(fs.readFileSync(p, "utf8"));
}

function walkDocs(items, out) {
  (items || []).forEach((it) => {
    if (!it) return;
    if (it.type === "group") {
      walkDocs(it.items || [], out);
      return;
    }
    if (it.href) out.push(it);
  });
}

function countSourcesAndParagraphs(sourceToc) {
  const docs = [];
  (sourceToc || []).forEach((coll) => walkDocs(coll.items || [], docs));
  const sources = docs.length;
  const paragraphs = docs.reduce((acc, d) => acc + (Number(d.paragraphs) || 0), 0);
  return { sources, paragraphs };
}

function countLinks(verseDiscovery) {
  let links = 0;
  for (const k of Object.keys(verseDiscovery || {})) {
    const arr = verseDiscovery[k];
    if (Array.isArray(arr)) links += arr.length;
  }
  return links;
}

exports.handler = async function () {
  try {
    const repoRoot = process.cwd();
    const lib = path.join(repoRoot, "library");
    const verseDiscoveryPath = path.join(lib, "verse_discovery.json");
    const sourceTocPath = path.join(lib, "source_toc.json");

    const verseDiscovery = fs.existsSync(verseDiscoveryPath) ? readJson(verseDiscoveryPath) : {};
    const sourceToc = fs.existsSync(sourceTocPath) ? readJson(sourceTocPath) : [];

    const { sources, paragraphs } = countSourcesAndParagraphs(sourceToc);
    const links = countLinks(verseDiscovery);
    const verses = verseDiscovery && typeof verseDiscovery === "object" ? Object.keys(verseDiscovery).length : 0;

    const payload = {
      ts: new Date().toISOString(),
      sources,
      paragraphs,
      links,
      verses_with_any: verses,
      version: 1,
    };

    return {
      statusCode: 200,
      headers: {
        "content-type": "application/json; charset=utf-8",
        "cache-control": "no-store",
        "access-control-allow-origin": "*",
      },
      body: JSON.stringify(payload),
    };
  } catch (e) {
    return {
      statusCode: 500,
      headers: {
        "content-type": "application/json; charset=utf-8",
        "cache-control": "no-store",
        "access-control-allow-origin": "*",
      },
      body: JSON.stringify({ ok: false, error: String(e && (e.stack || e.message || e)) }),
    };
  }
};

