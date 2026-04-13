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

    const [verseDiscovery, sourceToc] = await Promise.all([fetchJson(verseDiscoveryUrl), fetchJson(sourceTocUrl)]);

    const { sources, paragraphs } = countSourcesAndParagraphs(sourceToc);
    const links = countLinks(verseDiscovery);
    const versesWithAny = countVersesWithAny(verseDiscovery);

    const payload = {
      ts: new Date().toISOString(),
      sources,
      paragraphs,
      links,
      verses_with_any: versesWithAny,
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

