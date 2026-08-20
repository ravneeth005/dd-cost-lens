from __future__ import annotations

from dd_cost_lens.models import Finding, OrgData

OFFENDER_TAGS = {"user_id", "container_id", "request_id", "session_id", "trace_id"}


def analyze_custom_metric_cardinality(data: OrgData, project: str, env: str) -> list[Finding]:
    findings: list[Finding] = []
    for metric in data.metrics:
        if metric.get("project") != project or metric.get("env") != env:
            continue
        offending = OFFENDER_TAGS.intersection(metric.get("offending_tags", []))
        if metric.get("timeseries", 0) >= 20000 and offending:
            saving = round(float(metric.get("monthly_cost", 0)) * 0.65, 2)
            tag = metric.get("top_tag", sorted(offending)[0])
            findings.append(
                Finding(
                    module="Custom metric cardinality",
                    title=f"Reduce cardinality on {metric['name']}",
                    estimated_monthly_saving=saving,
                    effort="medium",
                    detail=f"{metric['name']} has {metric['timeseries']} distinct timeseries; {tag} is driving tag multiplication.",
                    owner_tag=metric.get("owner", "unknown"),
                    remediation_type="mwl",
                    metadata={
                        "metric": metric["name"],
                        "exclude_tags": sorted(offending),
                        "scope": _metric_scope(metric, project, env),
                    },
                )
            )
    return sorted(findings, key=lambda f: f.estimated_monthly_saving, reverse=True)


def _metric_scope(metric: dict, project: str, env: str) -> str:
    scope_tag = metric.get("scope_tag", "project")
    env_tag = metric.get("env_tag", "env")
    return f"{scope_tag}:{project},{env_tag}:{env}"
