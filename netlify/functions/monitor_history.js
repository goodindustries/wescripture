const { supaFetch, supaEnv } = require("./_supa.js");

exports.handler = async function () {
  try {
    const { url, serviceKey } = supaEnv();
    if (!url || !serviceKey) {
      return {
        statusCode: 200,
        headers: {
          "content-type": "application/json; charset=utf-8",
          "cache-control": "no-store",
          "access-control-allow-origin": "*",
        },
        body: JSON.stringify({ ok: false, configured: false, items: [] }),
      };
    }

    const items = await supaFetch("monitor_samples?select=ts,links,paragraphs,sources,verses_with_any&order=ts.asc&limit=180");
    return {
      statusCode: 200,
      headers: {
        "content-type": "application/json; charset=utf-8",
        "cache-control": "no-store",
        "access-control-allow-origin": "*",
      },
      body: JSON.stringify({ ok: true, configured: true, items: Array.isArray(items) ? items : [] }),
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

