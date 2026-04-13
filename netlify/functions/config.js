exports.handler = async function () {
  const url = process.env.SUPABASE_URL || "";
  const anonKey = process.env.SUPABASE_ANON_KEY || "";
  const authRedirect =
    process.env.AUTH_REDIRECT_URL ||
    process.env.PUBLIC_SITE_URL ||
    "";
  return {
    statusCode: 200,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
      "access-control-allow-origin": "*",
    },
    body: JSON.stringify({
      SUPABASE_URL: url,
      SUPABASE_ANON_KEY: anonKey,
      AUTH_REDIRECT_URL: authRedirect,
    }),
  };
};

