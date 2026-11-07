# Deploying the FastAPI + static frontend

Streamlit Community Cloud cannot host this build — it expects a Streamlit script.
You need a host that runs a Python web process. Render's free tier is the shortest
path, and it deploys straight from GitHub.

## Render (free tier, ~10 minutes)

1. Push to GitHub (this repo).
2. <https://render.com> → **New → Web Service** → connect the repo.
3. Settings:
   - **Runtime**: Python 3
   - **Build command**: `pip install -r requirements.txt`
   - **Start command**: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
   - **Instance type**: Free
4. **Environment variables** (only if you want live mode):
   - `SARVAM_API_KEY` = your key
   - `VE_PROVIDER` = `auto` (or `mock` to force the offline demo)
5. Deploy. First build takes 2–4 minutes.

Health check URL: `https://<your-app>.onrender.com/api/health` — it should return
`{"status":"ok","mode":"mock",...}`.

## The one caveat, stated plainly

Render's free tier gives you an **ephemeral filesystem**. The SQLite file lives at
`data/app.db` and is recreated empty whenever the service restarts or idles out.
That means:

- The dashboard starts empty on a cold start.
- Visitor activity is real while the container lives, then gone.

Two acceptable responses:

**a. Seed after each deploy.** Add a one-off job, or hit an endpoint that runs
`scripts/seed_demo.py`. Simplest: open `/analytics.html` and click **Refresh export**
after clicking around for a minute — the numbers are real events you just created.

**b. Move to Postgres.** Supabase or Neon free tier. Only `core/db.py` changes:
`connect()` returns a Postgres connection and the `?` placeholders become `%s`.
Nothing above the data layer knows the difference — that is why the schema was
written Postgres-compatible from the start.

Say which one you did in the README so nobody discovers it by refreshing twice.

## Verify the deploy

In an incognito window, with no key configured:

1. Home renders dark, aurora background, glass hero, **Mock mode** pill.
2. Learn → switch the header language to తెలుగు → segments appear in Telugu, labelled mock.
3. Tap a term → gloss appears with a *translated* chip.
4. Tutor → ask "who won the cricket world cup?" → refusal, in Telugu.
5. Analytics → **Refresh export** → health chips show row counts.
6. Resize to 390 px → single column, nav scrolls horizontally, no overflow.

## Alternative hosts

- **Fly.io** — `fly launch`, same start command, add a volume at `/app/data` if you
  want SQLite to survive restarts.
- **Railway** — detects Python, set the start command as above.
- **A VPS** — `uvicorn` behind nginx; SQLite persists on disk, which is the simplest
  way to make the demo state stick.

## What to say about deployment in the viva

"The API and the frontend ship as one process, so there is no CORS configuration and
no second deploy to forget. The deployed link runs with no key configured and shows
labelled mock results rather than failing — that is deliberate, because a demo that
only works on my machine is not a demo. The database is ephemeral on the free tier,
which is documented, along with the single-file change to move to Postgres."
