# Recoverable savings: $79.97/month

## Scope

| Field | Value |
| --- | --- |
| Organization | Fusionpact Technologies Inc. |
| Scope tag | service |
| Scope value | vercel.serverless-runtime |
| Environment tag | env |
| Environment | production |
| Datadog query scope | `service:vercel.serverless-runtime AND env:production` |

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

**Estimate notice:** Datadog did not return indexed metric volumes. Metric costs and savings use the supplied fallback monthly allocation, distributed evenly across the scoped metrics. This is not measured Datadog cost.

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
| Stop ingesting unread metric datadog.apm.hostname_issue | Unqueried metrics | $7.27 | low |
| Stop ingesting unread metric datadog.estimated_usage.apm.ingested_bytes | Unqueried metrics | $7.27 | low |
| Stop ingesting unread metric datadog.estimated_usage.apm.ingested_spans | Unqueried metrics | $7.27 | low |
| Stop ingesting unread metric datadog.estimated_usage.apm.total_indexed_spans | Unqueried metrics | $7.27 | low |
| Stop ingesting unread metric trace.http.client.request | Unqueried metrics | $7.27 | low |
| Stop ingesting unread metric trace.http.client.request.apdex | Unqueried metrics | $7.27 | low |
| Stop ingesting unread metric trace.http.client.request.hits | Unqueried metrics | $7.27 | low |
| Stop ingesting unread metric trace.http.client.request.hits.by_http_status | Unqueried metrics | $7.27 | low |
| Stop ingesting unread metric trace.server.request | Unqueried metrics | $7.27 | low |
| Stop ingesting unread metric trace.server.request.apdex | Unqueried metrics | $7.27 | low |
| Stop ingesting unread metric trace.server.request.hits | Unqueried metrics | $7.27 | low |

## Prioritized Remediation

1. **Stop ingesting unread metric datadog.apm.hostname_issue**: datadog.apm.hostname_issue is ingested but has no dashboard, monitor, or notebook readers. Owner: `service:vercel.serverless-runtime`. Estimated saving: $7.27/month.
2. **Stop ingesting unread metric datadog.estimated_usage.apm.ingested_bytes**: datadog.estimated_usage.apm.ingested_bytes is ingested but has no dashboard, monitor, or notebook readers. Owner: `service:vercel.serverless-runtime`. Estimated saving: $7.27/month.
3. **Stop ingesting unread metric datadog.estimated_usage.apm.ingested_spans**: datadog.estimated_usage.apm.ingested_spans is ingested but has no dashboard, monitor, or notebook readers. Owner: `service:vercel.serverless-runtime`. Estimated saving: $7.27/month.
4. **Stop ingesting unread metric datadog.estimated_usage.apm.total_indexed_spans**: datadog.estimated_usage.apm.total_indexed_spans is ingested but has no dashboard, monitor, or notebook readers. Owner: `service:vercel.serverless-runtime`. Estimated saving: $7.27/month.
5. **Stop ingesting unread metric trace.http.client.request**: trace.http.client.request is ingested but has no dashboard, monitor, or notebook readers. Owner: `service:vercel.serverless-runtime`. Estimated saving: $7.27/month.
6. **Stop ingesting unread metric trace.http.client.request.apdex**: trace.http.client.request.apdex is ingested but has no dashboard, monitor, or notebook readers. Owner: `service:vercel.serverless-runtime`. Estimated saving: $7.27/month.
7. **Stop ingesting unread metric trace.http.client.request.hits**: trace.http.client.request.hits is ingested but has no dashboard, monitor, or notebook readers. Owner: `service:vercel.serverless-runtime`. Estimated saving: $7.27/month.
8. **Stop ingesting unread metric trace.http.client.request.hits.by_http_status**: trace.http.client.request.hits.by_http_status is ingested but has no dashboard, monitor, or notebook readers. Owner: `service:vercel.serverless-runtime`. Estimated saving: $7.27/month.
9. **Stop ingesting unread metric trace.server.request**: trace.server.request is ingested but has no dashboard, monitor, or notebook readers. Owner: `service:vercel.serverless-runtime`. Estimated saving: $7.27/month.
10. **Stop ingesting unread metric trace.server.request.apdex**: trace.server.request.apdex is ingested but has no dashboard, monitor, or notebook readers. Owner: `service:vercel.serverless-runtime`. Estimated saving: $7.27/month.
11. **Stop ingesting unread metric trace.server.request.hits**: trace.server.request.hits is ingested but has no dashboard, monitor, or notebook readers. Owner: `service:vercel.serverless-runtime`. Estimated saving: $7.27/month.

## Attribution Rollup

| Owner | Recoverable monthly saving |
| --- | ---: |
| service:vercel.serverless-runtime | $79.97 |

## Ready-To-Apply Remediations

### Stop ingesting unread metric datadog.apm.hostname_issue

```bash
# Remove the emission of datadog.apm.hostname_issue from the service instrumentation.
# Confirm no dashboards, monitors, notebooks, or SLOs depend on it first.
# Validated Datadog scope: service:vercel.serverless-runtime,env:production

```

## Next Steps

Address low-effort findings first. Findings that require application or
platform changes should be reviewed with the owning service team before any
telemetry is removed.