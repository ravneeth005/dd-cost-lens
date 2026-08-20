# Recoverable savings: $0.08/month

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

Metric savings use the supplied effective rate of $0.050000 per indexed timeseries/month.

| Metric | Indexed volume | Ingested volume | Estimated monthly cost | Indexed tags | Readers |
| --- | ---: | ---: | ---: | --- | --- |
| `api.request.count` | 0 | - | $0.00 | - | monitor |
| `api.response.time` | 0 | - | $0.00 | - | monitor |
| `ws.active_connections` | 1 | - | $0.05 | - | monitor |
| `ws.broadcast.count` | 0 | - | $0.00 | - | unread |
| `ws.broadcast.recipients` | 0 | - | $0.00 | - | unread |
| `ws.connection.count` | 1 | - | $0.05 | - | unread |
| `ws.disconnection.count` | 1 | - | $0.05 | - | unread |

## Ranked Offenders

| Title | Module | Estimated monthly saving | Effort |
| --- | --- | ---: | --- |
| Stop ingesting unread metric ws.connection.count | Unqueried metrics | $0.04 | low |
| Stop ingesting unread metric ws.disconnection.count | Unqueried metrics | $0.04 | low |

## Prioritized Remediation

1. **Stop ingesting unread metric ws.connection.count**: ws.connection.count is ingested but has no dashboard, monitor, or notebook readers. Owner: `service:epc-ws`. Estimated saving: $0.04/month.
2. **Stop ingesting unread metric ws.disconnection.count**: ws.disconnection.count is ingested but has no dashboard, monitor, or notebook readers. Owner: `service:epc-ws`. Estimated saving: $0.04/month.

## Attribution Rollup

| Owner | Recoverable monthly saving |
| --- | ---: |
| service:epc-ws | $0.08 |

## Ready-To-Apply Remediations

### Stop ingesting unread metric ws.connection.count

```bash
# Remove the emission of ws.connection.count from the service instrumentation.
# Confirm no dashboards, monitors, notebooks, or SLOs depend on it first.
# Validated Datadog scope: service:epc-ws,env:staging

```

## Next Steps

Address low-effort findings first. Findings that require application or
platform changes should be reviewed with the owning service team before any
telemetry is removed.