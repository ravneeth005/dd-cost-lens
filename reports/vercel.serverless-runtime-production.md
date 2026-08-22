# Recoverable savings: unavailable

## Scope

| Field | Value |
| --- | --- |
| Organization | organization-1 |
| Scope tag | service |
| Scope value | project-1 |
| Environment tag | env |
| Environment | env-1 |
| Datadog query scope | `service:project-1 AND env:env-1` |

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

**Warning:** Datadog did not return indexed volume for one or more scoped metrics. Metric cost and savings are unavailable; this report must not be used as a cost estimate until volume access/data is available.

| Metric | Indexed volume | Ingested volume | Estimated monthly cost | Indexed tags | Readers |
| --- | ---: | ---: | ---: | --- | --- |
| `datadog.apm.hostname_issue` | unavailable | - | unavailable | - | unread |
| `datadog.estimated_usage.apm.ingested_bytes` | unavailable | - | unavailable | - | unread |
| `datadog.estimated_usage.apm.ingested_spans` | unavailable | - | unavailable | - | unread |
| `datadog.estimated_usage.apm.total_indexed_spans` | unavailable | - | unavailable | - | unread |
| `trace.http.client.request` | unavailable | - | unavailable | - | unread |
| `trace.http.client.request.apdex` | unavailable | - | unavailable | - | unread |
| `trace.http.client.request.hits` | unavailable | - | unavailable | - | unread |
| `trace.http.client.request.hits.by_http_status` | unavailable | - | unavailable | - | unread |
| `trace.server.request` | unavailable | - | unavailable | - | unread |
| `trace.server.request.apdex` | unavailable | - | unavailable | - | unread |
| `trace.server.request.hits` | unavailable | - | unavailable | - | unread |

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