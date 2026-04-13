const { handler: metricsHandler } = require("./monitor_metrics.js");
const { supaFetch, supaEnv } = require("./_supa.js");

function todayKey(isoTs) {
  return String(isoTs || "").slice(0, 10);
}

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
        body: JSON.stringify({ ok: false, configured: false }),
      };
    }

    const resp = await metricsHandler();
    if (!resp || resp.statusCode !== 200) {
      return resp || { statusCode: 500, body: JSON.stringify({ ok: false, error: "metrics_failed" }) };
    }
    const sample = JSON.parse(resp.body || "{}");
    if (!sample || !sample.ts) throw new Error("bad_sample");

    // Dedupe: keep one row per day (UTC). Store at midnight UTC.
    const day = todayKey(sample.ts);
    const ts = day + "T00:00:00.000Z";

    const row = {
      ts,
      links: Number(sample.links) || 0,
      paragraphs: Number(sample.paragraphs) || 0,
      sources: Number(sample.sources) || 0,
      verses_with_any: Number(sample.verses_with_any) || 0,
    };

    await supaFetch("monitor_samples?on_conflict=ts", {
      method: "POST",
      body: [row],
      headers: {
        Prefer: "resolution=merge-duplicates,return=minimal",
      },
    });

    return {
      statusCode: 200,
      headers: {
        "content-type": "application/json; charset=utf-8",
        "cache-control": "no-store",
        "access-control-allow-origin": "*",
      },
      body: JSON.stringify({ ok: true, row }),
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

