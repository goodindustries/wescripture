async function fetchJson(url) {
  const r = await fetch(url, { headers: { "cache-control": "no-store" } });
  if (!r.ok) throw new Error(`fetch_failed ${r.status} ${url}`);
  return await r.json();
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

function countVersesWithAny(verseDiscovery) {
  let withAny = 0;
  for (const k of Object.keys(verseDiscovery || {})) {
    const arr = verseDiscovery[k];
    if (Array.isArray(arr) && arr.length) withAny += 1;
  }
  return withAny;
}

function countLinkedFromSourceLinks(sourceLinks) {
  let linkedDocs = 0;
  let linkedParas = 0;
  for (const docId of Object.keys(sourceLinks || {})) {
    const paras = sourceLinks[docId];
    if (!paras || typeof paras !== "object") continue;
    const paraKeys = Object.keys(paras);
    if (!paraKeys.length) continue;
    let docHas = false;
    for (const pk of paraKeys) {
      const refs = paras[pk];
      if (Array.isArray(refs) && refs.length) {
        linkedParas += 1;
        docHas = true;
      }
    }
    if (docHas) linkedDocs += 1;
  }
  return { linked_docs: linkedDocs, linked_paragraphs: linkedParas };
}

function siteBaseUrl() {
  const u = (process.env.DEPLOY_PRIME_URL || process.env.URL || "").trim();
  return u.replace(/\/$/, "");
}

exports.handler = async function () {
  try {
    const base = siteBaseUrl();
    if (!base) throw new Error("missing_site_url_env");

    const verseDiscoveryUrl = base + "/library/verse_discovery.json";
    const sourceTocUrl = base + "/library/source_toc.json";
    const sourceLinksUrl = base + "/library/source_links.json";

    const [verseDiscovery, sourceToc, sourceLinks] = await Promise.all([
      fetchJson(verseDiscoveryUrl),
      fetchJson(sourceTocUrl),
      fetchJson(sourceLinksUrl),
    ]);

    const { sources, paragraphs } = countSourcesAndParagraphs(sourceToc);
    const links = countLinks(verseDiscovery);
    const versesWithAny = countVersesWithAny(verseDiscovery);
    const { linked_docs, linked_paragraphs } = countLinkedFromSourceLinks(sourceLinks);

    const payload = {
      ts: new Date().toISOString(),
      sources,
      paragraphs,
      links,
      verses_with_any: versesWithAny,
      linked_docs,
      linked_paragraphs,
      version: 2,
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

