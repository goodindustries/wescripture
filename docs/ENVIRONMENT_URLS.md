# URL map: Netlify vs VPS (Docker + Caddy)

## Netlify (`publish = "."` in [`netlify.toml`](../netlify.toml))

The deployed site root **is the repository root** (same URL layout as the Docker static mount). Paths are:

| Path | File |
|------|------|
| `/` | [`index.html`](../index.html) (landing / home) |
| `/library/index.html` | [`library/index.html`](../library/index.html) (scripture reader) |
| `/library/toc.json`, `/library/chapters/…`, `/library/entities/…` | under [`library/`](../library/) |
| `/home.html` | redirects (302) to `/index.html`; stub in repo for non-Netlify hosts |

Reader **Home** uses `SITE.homeUrl` → `../index.html` when the pathname starts with `/library/` (same as VPS).

## VPS / Docker ([`Caddyfile`](../Caddyfile), [`DEPLOYMENT.md`](../DEPLOYMENT.md))

Static files are mounted at `/srv/static`:

| Path | Source |
|------|--------|
| `/` | repo [`index.html`](../index.html) (landing) |
| `/home.css` | repo [`home.css`](../home.css) |
| `/library/…` | repo [`library/`](../library/) tree |

Reader **Home** uses `SITE.homeUrl` → `../index.html` when the pathname starts with `/library/`.

## Prebuilt deploy (save Netlify build minutes)

**Netlify static fallback:** from repo root, with the site linked (`netlify link`) and CLI logged in:

```bash
npx netlify-cli deploy --prod --dir .
```

This uploads the repo root; Netlify does not run a separate build command (`command = ""` in `netlify.toml`). Primary production is typically the VM/Docker stack—see [`DEPLOYMENT.md`](../DEPLOYMENT.md).
