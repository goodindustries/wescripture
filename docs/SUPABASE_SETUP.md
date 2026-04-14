# Supabase setup (WeScripture)

Goal: add **public activity** (for now), with **email magic-link login**, per-verse notes, morsels, and a global feed.

## 1) Create Supabase project
- Create a new project in Supabase.
- In **Authentication → URL Configuration**, set:
  - **Site URL**: your production origin (e.g. `https://wescripture.netlify.app`)
  - **Redirect URLs**: add every origin the reader uses, including:
    - `http://localhost:3000/**` (or your dev port)
    - `http://127.0.0.1:3000/**`
    - `https://wescripture.netlify.app/**`
  Magic links must redirect to a URL in this list or Supabase will reject the redirect.

### Local dev without Netlify Functions
The reader loads config from `/.netlify/functions/config` (Netlify only). For a plain static server (e.g. `python3 -m http.server 3000`):

1. Copy [`library/supabase-config.example.json`](../library/supabase-config.example.json) to `library/supabase-config.json` (gitignored).
2. Fill in `SUPABASE_URL`, `SUPABASE_ANON_KEY`, and set `AUTH_REDIRECT_URL` to the exact URL you use (e.g. `http://localhost:3000/library/index.html`).
3. Request a **new** magic link after saving — old links point at the wrong redirect.

Alternatively run **`npx netlify-cli dev`** from the repo root so `/.netlify/functions/config` exists locally.

## 2) Set Netlify environment variables
In Netlify site settings, add:
- **`SUPABASE_URL`**: your project URL
- **`SUPABASE_ANON_KEY`**: the anon public key

These are served to the static client via a Netlify Function at `/.netlify/functions/config`.

## 3) Apply schema + RLS SQL
In Supabase **SQL Editor**, run:
- [`supabase/schema.sql`](../supabase/schema.sql)

Notes:
- RLS is enabled on all tables.
- **Reads are public** (phase 0) and writes are **authenticated + own-row only**.
- Tightening to friends/private later means swapping policies, not rewriting the app.

## 4) Smoke test
1. Open `/library/index.html`.
2. Click the **account icon** (top-right).
3. Enter email → **Send link**.
4. After signing in, set a **@handle**.
5. Open any verse → **Your activity** → write a note → **Save note**.
6. Check:
   - **Feed** tab shows the event
   - **History** tab shows your events

## 5) Deploy notes
This repo publishes `.` (repo root) on Netlify; functions live under `netlify/functions/`.

Deploy (repo root):

```bash
git add -A
git commit -m "[social] supabase persistence"
git push
npx netlify-cli deploy --prod --dir .
```

