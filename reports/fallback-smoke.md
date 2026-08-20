# Recoverable savings: $5385.00/month

## Scope

| Field | Value |
| --- | --- |
| Organization | fusionpact |
| Scope tag | project |
| Scope value | checkout |
| Environment tag | env |
| Environment | prod |
| Datadog query scope | `project:checkout AND env:prod` |

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
| `app.checkout.cart_debug` |  | - | $900.00 | - | unread |
| `app.checkout.latency` |  | - | $1400.00 | - | dashboard:checkout-slo |

## Ranked Offenders

| Title | Module | Estimated monthly saving | Effort |
| --- | --- | ---: | --- |
| Shorten retention for checkout-main | Log volume and retention | $1288.00 | medium |
| Lower trace sampling for checkout-api | APM sampling | $990.00 | medium |
| Reduce cardinality on app.checkout.latency | Custom metric cardinality | $910.00 | medium |
| Stop ingesting unread metric app.checkout.cart_debug | Unqueried metrics | $720.00 | low |
| Drop DEBUG logs in prod for checkout-main | Log volume and retention | $620.00 | low |
| Reduce cardinality on app.checkout.cart_debug | Custom metric cardinality | $585.00 | medium |
| Reduce high-water mark impact from ci-runner-a | Host inventory | $162.00 | medium |
| Move non-prod host checkout-staging-worker off prod tier | Host inventory | $110.00 | low |

## Prioritized Remediation

1. **Shorten retention for checkout-main**: checkout-main retains logs for 30 days, but observed query lookback is 7 days. Owner: `team-web`. Estimated saving: $1288.00/month.
2. **Lower trace sampling for checkout-api**: checkout-api runs at 850 QPS with sampling rate 99%. Owner: `team-payments`. Estimated saving: $990.00/month.
3. **Reduce cardinality on app.checkout.latency**: app.checkout.latency has 85000 distinct timeseries; user_id is driving tag multiplication. Owner: `team-payments`. Estimated saving: $910.00/month.
4. **Stop ingesting unread metric app.checkout.cart_debug**: app.checkout.cart_debug is ingested but has no dashboard, monitor, or notebook readers. Owner: `team-web`. Estimated saving: $720.00/month.
5. **Drop DEBUG logs in prod for checkout-main**: checkout-main is ingesting 18 GB/day of DEBUG logs in the selected environment. Owner: `team-web`. Estimated saving: $620.00/month.
6. **Reduce cardinality on app.checkout.cart_debug**: app.checkout.cart_debug has 21000 distinct timeseries; request_id is driving tag multiplication. Owner: `team-web`. Estimated saving: $585.00/month.
7. **Reduce high-water mark impact from ci-runner-a**: ci-runner-a is ephemeral and contributes to a high-water mark of 26. Owner: `team-platform`. Estimated saving: $162.00/month.
8. **Move non-prod host checkout-staging-worker off prod tier**: checkout-staging-worker is tagged env:staging but billed at prod tier. Owner: `team-web`. Estimated saving: $110.00/month.

## Attribution Rollup

| Owner | Recoverable monthly saving |
| --- | ---: |
| team-web | $3323.00 |
| team-payments | $1900.00 |
| team-platform | $162.00 |

## Ready-To-Apply Remediations

### Lower trace sampling for checkout-api

```bash
# Apply to service checkout-api
DD_TRACE_SAMPLE_RATE=0.2
DD_TRACE_RATE_LIMIT=100

```
### Reduce cardinality on app.checkout.latency

```json
{
  "data": {
    "attributes": {
      "filter": "project:checkout,env:prod",
      "include_percentiles": false,
      "metric_type": "gauge",
      "tags": [
        "!session_id",
        "!user_id"
      ]
    },
    "id": "app.checkout.latency",
    "type": "manage_tags"
  }
}
```
### Stop ingesting unread metric app.checkout.cart_debug

```bash
# Remove the emission of app.checkout.cart_debug from the service instrumentation.
# Confirm no dashboards, monitors, notebooks, or SLOs depend on it first.
# Validated Datadog scope: project:checkout,env:prod

```

## Next Steps

Address low-effort findings first. Findings that require application or
platform changes should be reviewed with the owning service team before any
telemetry is removed.