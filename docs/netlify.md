# Deploying: Netlify for the site, Render for the API

Netlify is a static host with serverless functions. This project's backend is a
long-lived FastAPI process (`uvicorn`), which Netlify cannot run. Deploying the
repo to Netlify alone gives you pages whose every `/api/*` call 404s.

So the deploy is split in two. It takes about ten minutes and both halves
auto-deploy on every push to `main`.

## 1. The API on Render

1. <https://render.com> → **New → Web Service** → connect `cds208-vernacular-web`.
2. Build command: `pip install -r requirements.txt`
3. Start command: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
4. Environment variables: `SARVAM_API_KEY` (optional), `VE_PROVIDER=auto`
5. Deploy, then check `https://<your-api>.onrender.com/api/health` returns `{"status":"ok",...}`.

The corpus is not in the repo (licence unverified), so the Hindi→Mundari bridge
answers tier 4 on a fresh deploy until you either add the corpus to the Render
disk or leave it out of the demo. The five-language matrix does not need it.

## 2. The site on Netlify

1. <https://app.netlify.com> → **Add new site → Import an existing project** →
   GitHub → `cds208-vernacular-web`.
2. Build command: leave empty. Publish directory: `web`.
   (`web/netlify.toml` already sets this, so the defaults are fine.)
3. Deploy. You get `https://<your-site>.netlify.app`.

## 3. Point the site at the API

In each HTML file in `web/`, set the meta tag to your Render URL:

```html
<meta name="ve-api" content="https://your-api.onrender.com" />
```

One line per page. `web/assets/app.js` and the inline scripts read it, so every
`fetch` follows it — no other code changes.

Then allow the origin on the API: `api/main.py` already uses
`CORSMiddleware(allow_origins=["*"])`, which is fine for a coursework demo and
should be narrowed to your Netlify domain before anything real.

## 4. The landing page

`eta_pro_sarvam` is pure static — no API, no build. Import it into Netlify as a
separate site with publish directory `/`. Its `netlify.toml` handles headers,
caching and the single-page fallback.

## What to check after deploying

- `https://<site>.netlify.app/matrix.html` → type a sentence → a translation comes
  back with a provider chip. If it says "API is not reachable", the meta tag is
  wrong or Render is asleep (free tier sleeps after 15 minutes idle — the first
  request takes ~30s to wake).
- `https://<site>.netlify.app/bridge-preview.html` → works with no API at all.
- `https://<api>.onrender.com/docs` → FastAPI's own docs, useful in the viva.
