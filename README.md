# dd-cost-lens

`dd-cost-lens` is a read-only Datadog cost-optimization CLI. It analyzes one service/project and environment, identifies telemetry-cost opportunities, and writes a Markdown or HTML report with prioritized remediations.

It does not change Datadog configuration. Credentials are read from environment variables and are never written to disk.

## Requirements

- Python 3.11 or later
- A Datadog API key and application key with read access, including `metrics_read`
- Authorization to access the Datadog organization

## Setup on Windows with Git Bash

Open Git Bash in the repository folder, then create and activate a virtual environment:

```bash
py -3.11 -m venv .venv
source .venv/Scripts/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

After setup, use the executable from the environment:

```bash
./.venv/Scripts/dd-cost-lens.exe --help
```

PowerShell equivalent:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

## Configure Datadog credentials

In Git Bash:

```bash
export DD_API_KEY="<your-api-key>"
export DD_APP_KEY="<your-application-key>"
export DD_SITE="us5.datadoghq.com"
```

In PowerShell:

```powershell
$env:DD_API_KEY = "<your-api-key>"
$env:DD_APP_KEY = "<your-application-key>"
$env:DD_SITE = "us5.datadoghq.com"
```

Do not put credentials in source code, reports, or Git commits.

## Step 1: Discover valid services and environments

Start by discovering the tag combinations Datadog can verify:

```bash
./.venv/Scripts/dd-cost-lens.exe discover \
  --scope-tag service \
  --env-tag env \
  --datadog-site us5.datadoghq.com
```

To check one known service:

```bash
./.venv/Scripts/dd-cost-lens.exe discover \
  --scope-tag service \
  --scope-value vercel.serverless-runtime \
  --env-tag env \
  --datadog-site us5.datadoghq.com
```

Use the exact environment tag key displayed by Datadog. For example, the Internal Developer Portal screenshot uses `env:production`, so use `--env-tag env`—not `--env-tag environment`.

## Step 2: Run a measured production report

Use this when Datadog returns metric volumes. Replace `0.05` with the effective monthly indexed-timeseries rate approved by Finance/FinOps for your organization.

```bash
./.venv/Scripts/dd-cost-lens.exe run \
  --scope-tag service \
  --scope-value vercel.serverless-runtime \
  --env-tag env \
  --env production \
  --datadog-site us5.datadoghq.com \
  --metric-monthly-cost-per-timeseries 0.05 \
  --redact \
  --out reports/vercel.serverless-runtime-production.md
```

If Datadog returns indexed volume, the tool calculates metric cost as:

```text
indexed volume × approved monthly rate
```

## Step 3: Run a test or Finance-allocation estimate

If Datadog does not return metric volumes, a dollar amount cannot be measured from Datadog. For a demonstration or a Finance-approved allocation, provide an explicit fallback. The report labels it as an estimate and does not present it as measured Datadog cost.

Example using a **test allocation of $100/month**:

```bash
./.venv/Scripts/dd-cost-lens.exe run \
  --scope-tag service \
  --scope-value vercel.serverless-runtime \
  --env-tag env \
  --env production \
  --datadog-site us5.datadoghq.com \
  --metric-monthly-cost-per-timeseries 0.05 \
  --fallback-monthly-cost 100 \
  --out reports/vercel.serverless-runtime-production.md
```

The fallback allocation is distributed across the scoped metric candidates. If an unread-metric finding is generated, the tool estimates up to 80% of that allocation as recoverable. Never describe this as confirmed Datadog savings.

You may also set it for the current session:

```bash
export DD_COST_LENS_FALLBACK_MONTHLY_COST=100
```

## Other useful commands

Synthetic local demo without Datadog credentials:

```bash
./.venv/Scripts/dd-cost-lens.exe run \
  --project checkout \
  --env prod \
  --fixture \
  --redact
```

All environments for one service:

```bash
./.venv/Scripts/dd-cost-lens.exe run \
  --scope-tag service \
  --scope-value vercel.serverless-runtime \
  --env-tag env \
  --env all \
  --out reports/
```

Self-contained HTML report:

```bash
./.venv/Scripts/dd-cost-lens.exe run \
  --scope-tag service \
  --scope-value vercel.serverless-runtime \
  --env-tag env \
  --env production \
  --format html \
  --redact \
  --out reports/vercel.serverless-runtime-production.html
```

Show command help:

```bash
./.venv/Scripts/dd-cost-lens.exe --help
./.venv/Scripts/dd-cost-lens.exe run --help
./.venv/Scripts/dd-cost-lens.exe discover --help
```

## Interpreting report results

| Result | Meaning |
| --- | --- |
| Dollar savings with `datadog_volume` | Derived from Datadog-returned indexed volume and the supplied contract rate. Reconcile with Usage/Billing before financial reporting. |
| `Recoverable savings: unavailable` | Datadog did not return indexed metric volume. A measured dollar estimate is not available. |
| Estimate notice | The command used `--fallback-monthly-cost`; it is a test or Finance allocation, not measured Datadog cost. |
| `$0.00/month` | No verified recoverable finding was generated. It does not mean the service has no Datadog cost. |

## Safety

- The tool uses an explicit read-only Datadog API allow-list.
- Review every remediation with the owning team before removing telemetry.
- Use `--redact` before reports leave the authorized organization.
- Do not use customer telemetry for development, screenshots, or sample reports without authorization.
