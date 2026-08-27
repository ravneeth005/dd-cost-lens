# Recoverable savings: $0.32/month


## Scope

| Field | Value |
| --- | --- |
| Organization | Fusionpact Technologies Inc. |
| Scope tag | service |
| Scope value | epc-api |
| Environment tag | env |
| Environment | staging |
| Datadog query scope | `service:epc-api AND env:staging` |

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

Metric savings use the supplied effective rate of $0.050000 per indexed timeseries/month.

| Metric | Indexed volume | Ingested volume | Estimated monthly cost | Indexed tags | Readers |
| --- | ---: | ---: | ---: | --- | --- |
| `api.error.count` | 1 | - | $0.05 | - | monitor |
| `api.request.count` | 15 | - | $0.75 | - | monitor |
| `api.response.time` | 14 | - | $0.70 | - | monitor |
| `job.duration` | 5 | - | $0.25 | - | monitor |
| `job.failed` | 2 | - | $0.10 | - | monitor |
| `job.started` | 4 | - | $0.20 | - | unread |
| `job.succeeded` | 4 | - | $0.20 | - | unread |

## Analysis coverage

- **Metric cardinality:** Indexed volumes collected for 7 metrics; tag-cardinality details returned for 7.
- **Log retention:** 0 scoped log index configurations found. Query-history lookback is not exposed by this API, so no retention saving is calculated.
- **APM sampling:** 0 scoped APM services found. QPS and sampling-rate data were not returned, so no sampling saving is calculated.
- **Host inventory:** 0 scoped hosts found. Per-host billing allocation is unavailable, so no host saving is calculated.

## Ranked Offenders

| Title | Module | Estimated monthly saving | Effort |
| --- | --- | ---: | --- |
| Stop ingesting unread metric job.started | Unqueried metrics | $0.16 | low |
| Stop ingesting unread metric job.succeeded | Unqueried metrics | $0.16 | low |

## Prioritized Remediation

1. **Stop ingesting unread metric job.started**: job.started is ingested but has no dashboard, monitor, or notebook readers. Owner: `service:epc-api`. Estimated saving: $0.16/month.
2. **Stop ingesting unread metric job.succeeded**: job.succeeded is ingested but has no dashboard, monitor, or notebook readers. Owner: `service:epc-api`. Estimated saving: $0.16/month.

## Attribution Rollup

| Owner | Recoverable monthly saving |
| --- | ---: |
| service:epc-api | $0.32 |

## Ready-To-Apply Remediations

### Stop ingesting unread metric job.started

```bash
# Remove the emission of job.started from the service instrumentation.
# Confirm no dashboards, monitors, notebooks, or SLOs depend on it first.
# Validated Datadog scope: service:epc-api,env:staging

```

## Next Steps

Address low-effort findings first. Findings that require application or
platform changes should be reviewed with the owning service team before any
telemetry is removed.