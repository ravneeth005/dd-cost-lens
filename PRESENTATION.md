---
marp: true
title: dd-cost-lens
paginate: true
---

# dd-cost-lens

## Read-only Datadog cost optimization for a scoped service and environment

Find telemetry waste, assign ownership, and produce practical remediation guidance—without changing Datadog.

---

# The business problem

Datadog spend can grow through high-cardinality metrics, unused instrumentation, excessive log retention, trace oversampling, and host configuration.

- Raw usage data is difficult to turn into prioritized actions.
- A service owner needs findings for their service/environment, not organization-wide noise.
- Platform and FinOps teams need a repeatable, auditable review process.

**dd-cost-lens produces that scoped action plan.**

---

# What the code does

```text
DD_API_KEY + DD_APP_KEY
           |
dd-cost-lens run --scope-tag service --scope-value epc-api --env staging
           |
Validate scope and environment tags
           |
Read Datadog metrics, logs, APM services, hosts, and usage data
           |
Analyze -> rank findings -> assign owners -> generate remediation snippets
           |
Markdown/HTML report
```

If the scope or environment tag does not exist, it stops with an error instead of creating a misleading report.

---

# What it analyzes

| Area | What it identifies | Example action |
| --- | --- | --- |
| Metric cardinality | Expensive tag dimensions | Exclude unnecessary indexed tags |
| Unqueried metrics | Metrics with no detected reader | Remove unused instrumentation |
| Logs | Excess retention and DEBUG log volume | Reduce retention or filter logs |
| APM | Over-sampled services | Adjust trace sampling |
| Hosts | Ephemeral/over-tiered cost drivers | Right-size configuration |
| Attribution | Savings grouped by owner tag | Route work to the right team |

---

# What we can achieve

1. A headline recoverable monthly savings estimate.
2. A scoped metric inventory with volumes, tags, and detected readers.
3. Ranked findings by estimated impact and effort.
4. Owner-level savings rollups for accountability.
5. Ready-to-apply examples: Vector TOML, Metrics Without Limits JSON, APM settings, and instrumentation-removal guidance.

Metric savings are shown in currency only after supplying the organization's effective price per indexed timeseries.

---

# How it helps daily operations

- **FinOps / Platform:** replace manual dashboard checks with a consistent cost-hygiene review.
- **Service owners:** receive a focused action list for one service and environment.
- **Engineering:** get implementation-oriented remediation examples, not just a cost observation.
- **Leadership:** track the reported opportunity before and after approved changes.

Recommended rhythm: discover tags once, review key services weekly or monthly, apply approved fixes through normal change control, then rerun to validate progress.

---

# Safety model

- Read-only Datadog API allow-list; it never modifies Datadog configuration.
- Credentials come from environment variables and are not written to disk.
- Use `--redact` whenever a report leaves the authorized organization.
- Review recommendations with the owning team before removing telemetry.
- Use a least-privilege credential and only with an authorized Datadog organization.

---

# Install

```bash
# From this checked-out repository
pipx install .

# Or local development
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

---

# Set credentials

```bash
export DD_API_KEY="<api-key>"
export DD_APP_KEY="<application-key>"
export DD_SITE="us5.datadoghq.com" # optional; default: datadoghq.com
```

Windows PowerShell:

```powershell
$env:DD_API_KEY = "<api-key>"
$env:DD_APP_KEY = "<application-key>"
$env:DD_SITE = "us5.datadoghq.com" # optional
```

---

# Command: discover valid tags

Run this first to confirm the organization, scope tags, and environments available in Datadog.

```bash
dd-cost-lens discover
dd-cost-lens discover --scope-tag service
dd-cost-lens discover --scope-tag service --scope-value epc-api --env-tag env
```

Use synthetic data without credentials:

```bash
dd-cost-lens discover --fixture
```

---

# Command: EPC API staging analysis

```bash
dd-cost-lens run \
  --scope-tag service \
  --scope-value epc-api \
  --env staging \
  --datadog-site us5.datadoghq.com \
  --redact \
  --out reports/epc-api-staging.md
```

For the conventional `project` tag, use the compatible short form:

```bash
dd-cost-lens run --project epc-api --env staging --redact
```

---

# Command: accurate metric savings

Supply the effective monthly cost per indexed custom-metric timeseries agreed with FinOps.

```bash
dd-cost-lens run --scope-tag service --scope-value epc-api --env staging \
  --metric-monthly-cost-per-timeseries 0.01
```

Or use an environment variable:

```bash
export DD_COST_LENS_METRIC_TS_MONTHLY_RATE=0.01
dd-cost-lens run --scope-tag service --scope-value epc-api --env staging
```

---

# Commands: formats and coverage

```bash
# Every discovered environment for the service
dd-cost-lens run --scope-tag service --scope-value epc-api --env all --out reports/

# Self-contained HTML report
dd-cost-lens run --scope-tag service --scope-value epc-api --env staging \
  --redact --format html --out reports/epc-api-staging.html

# Organization uses `environment`, not `env`
dd-cost-lens run --scope-tag service --scope-value epc-api \
  --env-tag environment --env staging
```

---

# Commands: local demo, batch, help

```bash
# Synthetic data; safe for local demonstration
dd-cost-lens run --project checkout --env prod --fixture --redact

# Newline-delimited scope values in services.txt
dd-cost-lens run --scope-tag service --scope-value epc-api \
  --projects-file services.txt --env staging --out reports/

# All supported options
dd-cost-lens --help
dd-cost-lens run --help
dd-cost-lens discover --help
```

---

# Recommended rollout

1. Confirm authorization and configure a least-privilege read credential.
2. Run `discover --scope-tag service`; verify `service:epc-api` and its environments.
3. Generate a redacted staging report and review the ranked findings with the owner.
4. Agree the metric timeseries rate with FinOps before presenting metric-dollar savings.
5. Implement approved changes through normal change management.
6. Re-run the same command to validate reduced telemetry and track the trend.

---

# Success looks like

- Fewer indexed timeseries, unused metrics, and excessive DEBUG logs.
- Retention and trace sampling aligned with operational needs.
- Clear ownership for remaining savings opportunities.
- A lower recoverable-savings figure after verified changes.

## Outcome: controlled Datadog cost reduction while preserving useful observability.
