# dd-cost-lens

dd-cost-lens is a read-only Python CLI that analyzes a scoped Datadog project/environment and produces a polished cost-optimization report with a headline recoverable monthly savings figure. It is designed for teams that want to quickly identify custom metric waste, unused telemetry, log retention drift, APM oversampling, host billing surprises, and owner-level savings opportunities without granting write access or storing credentials.

## Install

For a one-command installation from a checked-out release:

```bash
pipx install .
```

The public release target is `pipx install dd-cost-lens`; publishing that
package is a separate release action.

## Release Prerequisites

Before a public release, record written confirmation that test and sample data
is Fusionpact-internal or explicitly consented and anonymised. Run all tests,
publish a redacted synthetic sample report only, and publish the package before
advertising the public `pipx install dd-cost-lens` command.

For local development:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Quickstart

Use synthetic fixture data locally:

```bash
dd-cost-lens run --project checkout --env prod --redact
```

Run every environment for a project:

```bash
dd-cost-lens run --project checkout --env all --redact
```

Discover organization, project tags, and env tags before running a report:

```bash
dd-cost-lens discover
```

If your Datadog org uses another scope tag instead of `project`, discover and run with that tag:

```bash
dd-cost-lens discover --scope-tag service
dd-cost-lens run --scope-tag service --scope-value checkout --env all
```

Use Datadog credentials from environment variables:

```bash
export DD_API_KEY="..."
export DD_APP_KEY="..."
dd-cost-lens run --project checkout --env prod --datadog-site datadoghq.com --out reports/checkout-prod.md
```

Generate a self-contained HTML version suitable for internal sharing:

```bash
dd-cost-lens run --project checkout --env prod --redact --format html --out reports/checkout-prod.html
```

To calculate metric savings from your contract's effective monthly rate per
indexed timeseries, pass the rate explicitly:

```bash
dd-cost-lens run --scope-tag service --scope-value epc-api --env staging \
  --datadog-site us5.datadoghq.com \
  --metric-monthly-cost-per-timeseries 0.01
```

You can instead export `DD_COST_LENS_METRIC_TS_MONTHLY_RATE`. Without a rate,
the report still includes the complete scoped metric inventory, but does not
claim a monetary metric saving.

Credentials are read from environment variables or stdin only. The tool never writes credentials to disk and never uses Datadog write APIs.

Before using live credentials, confirm in writing that the selected Datadog
organization or sub-organization is Fusionpact-internal or that you have
written client consent. Do not use client telemetry in development, tests,
screenshots, or sample reports. Use `--redact` for every report that leaves
the organization.

## Datadog API Scope

| Endpoint | Method | Why |
| --- | --- | --- |
| `/api/v2/org` | GET | Fetch the Datadog organization name displayed in each report. |
| `/api/v1/org` | GET | Fallback organization lookup when v2 only returns a public ID. |
| `/api/v1/tags/hosts` | GET | Validate project/env tag existence and collect scoped host inventory. |
| `/api/v2/current_user` | GET | Confirm the organization associated with the supplied credentials. |
| `/api/v2/metrics` | GET | Discover scoped metrics, including every page of a paginated result. |
| `/api/v2/metrics/{metric_name}/all-tags` | GET | Estimate custom metric cardinality and identify high-cardinality tag drivers. |
| `/api/v1/dashboard` | GET | Determine whether ingested metrics are referenced by dashboards. |
| `/api/v1/monitor` | GET | Determine whether ingested metrics are referenced by monitors. |
| `/api/v1/notebooks` | GET | Determine whether ingested metrics are referenced by notebooks. |
| `/api/v1/logs/config/indexes` | GET | Read log index retention and filter configuration for retention recommendations. |
| `/api/v2/logs/analytics/aggregate` | POST | Read-only aggregate query for log volume, query lookback, and DEBUG-in-prod analysis. |
| `/api/v2/apm/services` | GET | Discover scoped APM services and sampling candidates. |
| `/api/v1/usage/hosts` | GET | Read host high-water mark and billing attribution inputs. |

All calls are scoped to `project:<project> AND env:<env>` where Datadog supports query scoping. The HTTP client refuses methods outside the explicit read-only allow-list.

## Output

Reports are written as self-contained Markdown by default, or HTML with
`--format html`. The first visible line is the recoverable `$/month` estimate,
followed by ranked offenders, a remediation plan, owner attribution, and
ready-to-apply Vector/Metrics Without Limits remediation snippets.

Every report also contains an `Updated Feature & Technical Scope` workflow and
a `Metric Inventory` table listing all metrics returned for the requested
scope and environment, including volume, tags, and detected readers.
