# dd-cost-lens

`dd-cost-lens` is a read-only Datadog telemetry-cost analysis CLI. It validates a `service`/environment scope, collects available Datadog telemetry metadata, identifies metrics with no detected readers, and creates a Markdown or HTML report.

It never changes Datadog configuration or removes telemetry.

## Docker quick start (recommended)

Use Docker for normal use. It removes the need to install Python, create a virtual environment, or export Datadog keys in the terminal.

### 1. Install and start Docker Desktop

Install Docker Desktop for Windows, start it, and wait until the Docker engine is running. In Git Bash, open the repository folder and verify Docker:

```bash
cd ~/
docker version
```

The output must contain both **Client** and **Server**. If Server is missing, Docker Desktop is not running yet.

### 2. Create the local credentials file

Copy the template once:

```bash
cp .env.example .env
```

Open `.env` and fill only these local values:

```dotenv
DD_API_KEY=your_datadog_api_key
DD_APP_KEY=your_datadog_application_key
DD_SITE=us5.datadoghq.com
```

Do not use `export DD_API_KEY=...`. Docker Compose reads `.env` automatically. Never commit, share, or paste `.env` values. The `.env` and `.venv` folders are ignored by Git and excluded from the Docker image.

### 3. Build and verify the application

```bash
docker compose build
docker compose run --rm dd-cost-lens --help
```

Build again only after changing source code, dependencies, `Dockerfile`, or `compose.yaml`.

### 4. Discover services and environments

```bash
docker compose run --rm dd-cost-lens discover \
  --scope-tag service \
  --env-tag env \
  --datadog-site us5.datadoghq.com
```

### 5. Generate an unredacted report

```bash
docker compose run --rm dd-cost-lens run \
  --scope-tag service \
  --scope-value epc-ws \
  --env-tag env \
  --env staging \
  --datadog-site us5.datadoghq.com \
  --out epc-ws-staging.md
```

The report is created at `reports/epc-ws-staging.md` on your laptop. Use a relative output filename as above; do not use `/reports/...` in Git Bash because it can rewrite that container path into an invalid Windows path.

### After closing Git Bash

No virtual environment is required. Open Docker Desktop, then run:

```bash
cd ~/ravneet
docker compose run --rm dd-cost-lens discover \
  --scope-tag service \
  --env-tag env \
  --datadog-site us5.datadoghq.com
```

## Optional local Python development

This section is only for developers who intentionally run the source without Docker. Normal users should follow the Docker quick start above and do not need Python.

```bash
py -3.11 --version
```

If this command is not found, install Python 3.11 from PowerShell, Command Prompt, or Git Bash:

```bash
winget install --id Python.Python.3.11 -e
```

Close and reopen the terminal after installation, then verify again:

```bash
py -3.11 --version
```

If `winget` is unavailable, install Python 3.11+ from [python.org](https://www.python.org/downloads/). Python is not needed only when a standalone packaged executable is distributed separately.

## Legacy local-Python runbook

This section is only for developers intentionally running the source without Docker. For demos and normal users, use the Docker commands above.

```bash
source .venv/Scripts/activate
```

### A. Discover the services and environments Datadog can validate

```bash
./.venv/Scripts/dd-cost-lens.exe discover \
  --scope-tag service \
  --env-tag env \
  --datadog-site us5.datadoghq.com
```

### B. Verify one service before generating a report

```bash
./.venv/Scripts/dd-cost-lens.exe discover \
  --scope-tag service \
  --scope-value vercel.serverless-runtime \
  --env-tag env \
  --datadog-site us5.datadoghq.com
```

### C. Generate the production analysis report

```bash
docker compose run --rm dd-cost-lens run \
  --scope-tag service \
  --scope-value vercel.serverless-runtime \
  --env-tag env \
  --env production \
  --datadog-site us5.datadoghq.com \
  --out reports/vercel.serverless-runtime-production.md
```

Expected outcome: the report is written. If Datadog does not return indexed metric volume, it correctly says `Recoverable savings: unavailable`.

### D. Optional: rate-based staging estimate

Run this only if Finance/FinOps has approved the rate and Datadog returns indexed volume for this scope:

```bash
./.venv/Scripts/dd-cost-lens.exe run \
  --scope-tag service \
  --scope-value epc-ws \
  --env-tag env \
  --env staging \
  --datadog-site us5.datadoghq.com \
  --metric-monthly-cost-per-timeseries 0.05 \
  --out reports/epc-ws-staging.md
```

Do not run `--fallback-monthly-cost 100` as an actual-cost demo. It is a manual planning estimate, not Datadog cost.

## What to say in a demo

> The tool discovers valid Datadog service and environment tags, analyzes the selected scope, and produces a prioritized telemetry review report. It only reports a measured rate-based amount when Datadog returns indexed metric volume. If volume is unavailable, it says so rather than inventing an actual cost.

## Docker demo runbook

Use this first in a presentation. Docker Compose reads keys from local `.env`; do not export or display credentials.

```bash
docker compose run --rm dd-cost-lens discover \
  --scope-tag service \
  --env-tag env \
  --datadog-site us5.datadoghq.com
```

To verify a known service and list its environments:

```bash
docker compose run --rm dd-cost-lens discover \
  --scope-tag service \
  --scope-value vercel.serverless-runtime \
  --env-tag env \
  --datadog-site us5.datadoghq.com
```

`service` is the scope-tag key and `env` is the environment-tag key. `production`, `preview`, and `staging` are values. A service appears with `env:staging` only when Datadog has received telemetry with both tags, for example `service:epc-ws AND env:staging`.

If you know a staging service, verify it directly:

```bash
docker compose run --rm dd-cost-lens discover \
  --scope-tag service \
  --scope-value epc-ws \
  --env-tag env \
  --datadog-site us5.datadoghq.com
```

## Generate an analysis report

This is the production analysis command for the Vercel runtime service:

```bash
docker compose run --rm dd-cost-lens run \
  --scope-tag service \
  --scope-value vercel.serverless-runtime \
  --env-tag env \
  --env production \
  --datadog-site us5.datadoghq.com \
  --out vercel.serverless-runtime-production.md
```

This fetches available Datadog telemetry metadata and creates the report. It does not guarantee that Datadog will return metric volume or billed cost.

## Rate-based estimate when metric volume is available

Add this only after Finance/FinOps has confirmed the effective contract rate and the report has Datadog-returned indexed volumes:

```bash
docker compose run --rm dd-cost-lens run \
  --scope-tag service \
  --scope-value epc-ws \
  --env-tag env \
  --env staging \
  --datadog-site us5.datadoghq.com \
  --metric-monthly-cost-per-timeseries 0.05 \
  --out epc-ws-staging-rate-estimate.md
```

`0.05` is a manually supplied rate. It is not fetched from Datadog and may not match the final invoice because of contract terms, allowances, discounts, and pricing model.

## Fallback allocation — demo/planning only

Use this only when Finance supplies a planning allocation or for a demo:

```bash
./.venv/Scripts/dd-cost-lens.exe run \
  --scope-tag service \
  --scope-value vercel.serverless-runtime \
  --env-tag env \
  --env production \
  --datadog-site us5.datadoghq.com \
  --fallback-monthly-cost 100 \
  --out vercel.serverless-runtime-production-fallback.md
```

`--fallback-monthly-cost 100` means “use a manual $100/month allocation if Datadog returns no metric volumes.” It is distributed across candidate metrics. It is **not** Datadog cost and must not be reported as actual savings or matched to a Datadog dashboard.

## Fetch authoritative Datadog cost into the report

For actual cost by service/environment, ask a Datadog administrator to grant your role:

```text
Metrics Read
Usage Read
Billing Read
```

They must also configure `service` and `env` as Usage/Cost Attribution tags in the parent/root Datadog organization.

Then use **Datadog → Organization Settings → Plan & Usage → Cost Details / Cost Attribution**, choose a completed billing month, and filter/group by:

```text
service:vercel.serverless-runtime
env:production
```

After those permissions are granted, add `--cost-attribution-month` to the
normal report command. The month must be complete and use `YYYY-MM`.

```bash
docker compose run --rm dd-cost-lens run \
  --scope-tag service \
  --scope-value vercel.serverless-runtime \
  --env-tag env \
  --env production \
  --datadog-site us5.datadoghq.com \
  --cost-attribution-month 2026-07 \
  --out vercel.serverless-runtime-production-attributed-cost.md
```

When Datadog authorizes the request and has matching attribution tags, the
report adds **Actual Datadog attributed cost** for the selected service and
environment. This value is scope-level billed cost and is deliberately kept
separate from metric-removal savings.

If the report says the actual cost is unavailable, no cost is fabricated. A
403 response means the key lacks `usage_read`/`billing_read` access, the
organization is not the parent billing organization, or the Datadog plan does
not include Cost Attribution. The current Startup plan does not provide this
billing data, so the report correctly shows actual attributed cost as unavailable.

You can also call the Cost Attribution API directly after those permissions
are granted:

```bash
curl -sS -X GET \
  "https://api.us5.datadoghq.com/api/v2/cost_by_tag/monthly_cost_attribution?start_month=2026-07&end_month=2026-07&fields=*&tag_breakdown_keys=service,env" \
  -H "Accept: application/json" \
  -H "DD-API-KEY: ${DD_API_KEY}" \
  -H "DD-APPLICATION-KEY: ${DD_APP_KEY}"
```

Use a completed month and replace `2026-07` with the billing month to inspect. A permission error means the required Datadog role access has not been granted.

## Report interpretation

| Report result | Meaning |
| --- | --- |
| `Recoverable savings: unavailable` | Datadog did not return indexed metric volume. No measured rate-based estimate is available. |
| Estimate notice | A fallback allocation was supplied. Any dollar amount is a manual planning estimate, not Datadog cost. |
| Dollar estimate with indexed volume | Rate-based estimate using Datadog-returned volume and a manually supplied approved rate. Reconcile it with Cost Attribution before financial reporting. |
| Actual Datadog attributed cost | A service/environment total returned by Datadog Cost Attribution for the selected completed month. It is not per-metric cost or guaranteed saving. |
| `$0.00/month` | No verified recoverable finding was generated; it does not mean the service has no Datadog cost. |

## Safety requirements

- Do not remove a metric merely because the report calls it `unread`.
- Review dashboards, monitors, notebooks, SLOs, and service-owner requirements first.
- Treat `datadog.*` and `trace.*` metrics as potentially platform-generated telemetry; do not remove them without Datadog/platform-owner confirmation.
- Use `--redact` before sharing a report outside the authorized team.
