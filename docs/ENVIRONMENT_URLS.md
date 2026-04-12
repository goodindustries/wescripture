# URL map: Netlify vs VPS (Docker + Caddy)

## Netlify (`publish = library` in [`netlify.toml`](../netlify.toml))

The deployed site root **is** the `library/` folder. Paths are:

| Path | File |
|------|------|
| `/` | [`library/index.html`](../library/index.html) (scripture reader) |
| `/index.html` | same reader (canonical **home**) |
| `/home.html` | redirects (302) to `/index.html`; stub file in repo for non-Netlify hosts |
| `/toc.json`, `/chapters/…`, `/entities/…` | under `library/` |

**Do not** assume `/library/index.html` exists on Netlify (that would be `library/library/index.html` in the repo).

Reader **Home** uses `SITE.homeUrl` → `./index.html` (same reader).

## VPS / Docker ([`Caddyfile`](../Caddyfile), [`DEPLOYMENT.md`](../DEPLOYMENT.md))

Static files are mounted at `/srv/static`:

| Path | Source |
|------|--------|
| `/` | repo [`index.html`](../index.html) (landing) |
| `/home.css` | repo [`home.css`](../home.css) |
| `/library/…` | repo [`library/`](../library/) tree |

Reader **Home** uses `SITE.homeUrl` → `../index.html` when the pathname starts with `/library/`.

## Prebuilt deploy (save Netlify build minutes)

**Canonical production deploy:** from repo root, with the site linked (`netlify link`) and CLI logged in:

```bash
npx netlify-cli deploy --prod --dir library
```

This uploads the existing `library/` tree; Netlify does not run a separate build command (`command = ""` in `netlify.toml`). Use this after merges or local changes—do not rely on an implicit Netlify Git build unless you have that wired up separately.
