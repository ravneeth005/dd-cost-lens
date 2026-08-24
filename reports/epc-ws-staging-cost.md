# Recoverable savings: $0.00/month

## Actual Datadog attributed cost

Unavailable: Datadog denied Cost Attribution access. Use a parent-level organization and an application key with usage_read and billing_read.


## Scope

| Field | Value |
| --- | --- |
| Organization | Fusionpact Technologies Inc. |
| Scope tag | service |
| Scope value | epc-ws |
| Environment tag | env |
| Environment | staging |
| Datadog query scope | `service:epc-ws AND env:staging` |

## Updated Feature & Technical Scope

```text
                            [ User Terminal ]
                                     |
                     exports DD_API_KEY & DD_APP_KEY
                                     |
     dd-cost-lens run --scope-tag <tag> --scope-value <value> --env <env> [--redact]
                                     |
                           [ Validate Tags ]
                          /                \\
               [ Tag Exists ]          [ Tag Missing ]
                    |                       |
                    v                       v
       Fetch Datadog metrics, logs,   Return error: scope or environment
       hosts, and APM data             not found in Datadog telemetry
                    |
                    v
       Analyze cardinality, unread metrics, retention, APM, and hosts
                    |
                    v
       Generate this report and ready-to-apply remediation configs
```

## Metric Inventory

Metric usage is shown below. Set `--metric-monthly-cost-per-timeseries` (or `DD_COST_LENS_METRIC_TS_MONTHLY_RATE`) to turn metric usage into monetary savings estimates.

| Metric | Indexed volume | Ingested volume | Estimated monthly cost | Indexed tags | Readers |
| --- | ---: | ---: | ---: | --- | --- |
| `api.request.count` | 46 | - | $0.00 | - | monitor |
| `api.response.time` | 47 | - | $0.00 | - | monitor |
| `ws.active_connections` | 1 | - | $0.00 | - | monitor |
| `ws.connection.count` | 1 | - | $0.00 | - | unread |
| `ws.disconnection.count` | 1 | - | $0.00 | - | unread |

## Ranked Offenders

| Title | Module | Estimated monthly saving | Effort |
| --- | --- | ---: | --- |

## Prioritized Remediation


## Attribution Rollup

| Owner | Recoverable monthly saving |
| --- | ---: |

## Ready-To-Apply Remediations


## Next Steps

Address low-effort findings first. Findings that require application or
platform changes should be reviewed with the owning service team before any
telemetry is removed.