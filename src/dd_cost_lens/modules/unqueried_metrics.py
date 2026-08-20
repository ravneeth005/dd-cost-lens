from __future__ import annotations

from dd_cost_lens.models import Finding, OrgData


def analyze_unqueried_metrics(data: OrgData, project: str, env: str) -> list[Finding]:
    findings: list[Finding] = []
    for metric in data.metrics:
        if metric.get("project") != project or metric.get("env") != env:
            continue
        readers = data.metric_readers.get(metric["name"], metric.get("readers", []))
        monthly_cost = metric.get("monthly_cost")
        if (
            not readers
            and isinstance(monthly_cost, (int, float))
            and monthly_cost > 0
        ):
            saving = round(float(monthly_cost) * 0.8, 2)
            findings.append(
                Finding(
                    module="Unqueried metrics",
                    title=f"Stop ingesting unread metric {metric['name']}",
                    estimated_monthly_saving=saving,
                    effort="low",
                    detail=f"{metric['name']} is ingested but has no dashboard, monitor, or notebook readers.",
                    owner_tag=metric.get("owner", "unknown"),
                    remediation_type="remove_metric_instrumentation",
                    metadata={
                        "metric": metric["name"],
                        "scope": _metric_scope(metric, project, env),
                    },
                )
            )
    return findings


def _metric_scope(metric: dict, project: str, env: str) -> str:
    scope_tag = metric.get("scope_tag", "project")
    env_tag = metric.get("env_tag", "env")
    return f"{scope_tag}:{project},{env_tag}:{env}"
