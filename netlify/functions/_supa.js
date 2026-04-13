function supaEnv() {
  const url = (process.env.SUPABASE_URL || "").trim();
  const serviceKey = (process.env.SUPABASE_SERVICE_ROLE_KEY || "").trim();
  return { url, serviceKey };
}

async function supaFetch(path, { method = "GET", body = null, headers: extraHeaders = null } = {}) {
  const { url, serviceKey } = supaEnv();
  if (!url || !serviceKey) {
    const err = new Error("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY");
    err.code = "missing_env";
    throw err;
  }
  const u = url.replace(/\/$/, "") + "/rest/v1/" + String(path || "").replace(/^\//, "");
  const headers = {
    apikey: serviceKey,
    authorization: `Bearer ${serviceKey}`,
    "content-type": "application/json; charset=utf-8",
    accept: "application/json",
  };
  if (extraHeaders) Object.assign(headers, extraHeaders);
  const res = await fetch(u, { method, headers, body: body ? JSON.stringify(body) : null });
  const text = await res.text();
  let json = null;
  try {
    json = text ? JSON.parse(text) : null;
  } catch (e) {
    json = { raw: text };
  }
  if (!res.ok) {
    const err = new Error(`Supabase HTTP ${res.status}`);
    err.status = res.status;
    err.payload = json;
    throw err;
  }
  return json;
}

module.exports = { supaEnv, supaFetch };

