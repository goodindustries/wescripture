const { supaFetch, supaEnv } = require("./_supa.js");

function json(statusCode, payload) {
  return {
    statusCode,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
      "access-control-allow-origin": "*",
    },
    body: JSON.stringify(payload),
  };
}

function safeParseJsonBody(event) {
  try {
    return event && event.body ? JSON.parse(event.body) : {};
  } catch (e) {
    return null;
  }
}

exports.handler = async function (event) {
  try {
    const method = String((event && event.httpMethod) || "GET").toUpperCase();
    const { url, serviceKey } = supaEnv();
    if (!url || !serviceKey) return json(200, { ok: false, configured: false, items: [] });

    if (method === "GET") {
      const items = await supaFetch(
        "corpus_backlog?select=id,title,author,canonical_url,license,status,priority,needs,notes,created_at,updated_at&order=priority.desc,updated_at.desc&limit=250"
      );
      return json(200, { ok: true, configured: true, items: Array.isArray(items) ? items : [] });
    }

    const body = safeParseJsonBody(event);
    if (body === null) return json(400, { ok: false, error: "bad_json" });

    if (method === "POST") {
      const row = {
        title: String(body.title || "").trim(),
        author: String(body.author || "").trim(),
        canonical_url: String(body.canonical_url || "").trim(),
        license: String(body.license || "").trim(),
        status: String(body.status || "todo").trim() || "todo",
        priority: Number(body.priority) || 0,
        needs: body.needs && typeof body.needs === "object" ? body.needs : { pull: true, encode: true, correlate: true },
        notes: String(body.notes || "").trim(),
      };
      if (!row.title) return json(400, { ok: false, error: "missing_title" });
      const out = await supaFetch("corpus_backlog", {
        method: "POST",
        body: [row],
        headers: { Prefer: "return=representation" },
      });
      return json(200, { ok: true, item: Array.isArray(out) ? out[0] : null });
    }

    if (method === "PATCH") {
      const id = String(body.id || "").trim();
      if (!id) return json(400, { ok: false, error: "missing_id" });
      const patch = {};
      if (body.title != null) patch.title = String(body.title || "").trim();
      if (body.author != null) patch.author = String(body.author || "").trim();
      if (body.canonical_url != null) patch.canonical_url = String(body.canonical_url || "").trim();
      if (body.license != null) patch.license = String(body.license || "").trim();
      if (body.status != null) patch.status = String(body.status || "").trim();
      if (body.priority != null) patch.priority = Number(body.priority) || 0;
      if (body.needs != null && typeof body.needs === "object") patch.needs = body.needs;
      if (body.notes != null) patch.notes = String(body.notes || "").trim();
      patch.updated_at = new Date().toISOString();

      const out = await supaFetch(`corpus_backlog?id=eq.${encodeURIComponent(id)}`, {
        method: "PATCH",
        body: patch,
        headers: { Prefer: "return=representation" },
      });
      return json(200, { ok: true, item: Array.isArray(out) ? out[0] : null });
    }

    if (method === "DELETE") {
      const id = String(body.id || "").trim();
      if (!id) return json(400, { ok: false, error: "missing_id" });
      await supaFetch(`corpus_backlog?id=eq.${encodeURIComponent(id)}`, { method: "DELETE" });
      return json(200, { ok: true });
    }

    return json(405, { ok: false, error: "method_not_allowed" });
  } catch (e) {
    return json(500, { ok: false, error: String(e && (e.stack || e.message || e)) });
  }
};
