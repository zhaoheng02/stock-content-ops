# Data Source Module Completion Audit

## Deliverables

- Backend data source module: implemented in `content_ops/data_sources.py`.
- Local CLI: implemented in `content_ops/cli.py` under `sources`.
- Local HTTP API: implemented in `content_ops/server.py`.
- Supabase repository adapter: implemented as `SupabaseDataSourceRepository`.
- Supabase project: created as `stock-content-ops`, project ref `iwrcxnybgjfodcmicsbx`.
- Supabase schema: executed successfully from `docs/supabase_schema.sql`.
- Supabase seed SQL: available in `docs/supabase_seed_sources.sql`.
- Airtap account discovery: seed contains `levelsio`, `lennysan`, `Patticus`, `marc_louvion`, `tdinh_me`.
- Frontend integration: `web/src/pages/sources.jsx` reads local API data and triggers runs.
- Frontend source creation: `web/src/components/app/modals.jsx` posts new sources to the local API.
- Frontend run mode control: `web/src/pages/sources.jsx` exposes Sample and Live modes.

## Verified

- `python3 -m unittest discover -s tests` passes.
- `npm run build` passes from `web/`.
- `python3 -m content_ops sources import --file config/data_sources.example.json` imports the Airtap-discovered source.
- `GET /api/sources` returns the seeded sources.
- `POST /api/source-runs` records a structured failed run when X credentials are missing.
- `POST /api/source-runs` with `mode=sample` records a successful run and writes deterministic sample posts without X credentials.
- The browser UI displays API-backed sources and refreshes run records after clicking run.
- The browser UI defaults to Sample mode for no-token local demos and can be switched to Live mode for X API collection.
- `POST /api/sources` creates a source that appears in `GET /api/sources`.
- `curl https://iwrcxnybgjfodcmicsbx.supabase.co/rest/v1/data_sources?select=id,name` reaches the project and returns `UNAUTHORIZED_MISSING_API_KEY`, confirming the project exists but no API key is configured locally.

## Remaining Live Verification Blockers

- `X_BEARER_TOKEN` is missing from `/Users/bytedance/personal.config`, so live X API collection cannot be verified. Sample-mode collection is verified.
- `SUPABASE_URL` is not set in the local environment or `/Users/bytedance/personal.config`.
- `SUPABASE_SERVICE_ROLE_KEY` is not set in the local environment or `/Users/bytedance/personal.config`.
- Supabase dashboard API settings access is blocked by hCaptcha during login, so the service role key was not retrieved through browser automation.

Run this diagnostic any time:

```bash
python3 -m content_ops sources doctor
```

Expected completion state:

```text
X_BEARER_TOKEN=present
SUPABASE_URL=present
SUPABASE_SERVICE_ROLE_KEY=present
```

After those are present:

```bash
python3 -m content_ops sources --repo supabase import --file config/data_sources.example.json
python3 -m content_ops sources --repo supabase list
python3 -m content_ops sources --repo supabase run x-growth-ai --out data/inbox
```

For a no-token local smoke test:

```bash
python3 -m content_ops sources run x-growth-ai --out data/inbox --mode sample
```

`SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` may be provided either as environment variables or
as `KEY value` / `KEY=value` lines in `/Users/bytedance/personal.config`.
