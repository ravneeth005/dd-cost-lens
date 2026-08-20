from __future__ import annotations

from dd_cost_lens.models import Finding, OrgData


def analyze_log_volume_and_retention(data: OrgData, project: str, env: str) -> list[Finding]:
    findings: list[Finding] = []
    for index in data.log_indexes:
        if index.get("project") != project or index.get("env") != env:
            continue
        retention = int(index.get("retention_days", 0))
        lookback = int(index.get("observed_query_lookback_days", 0))
        if retention >= lookback * 2 and retention - lookback >= 7:
            ratio = (retention - max(lookback, 1)) / max(retention, 1)
            findings.append(
                Finding(
                    module="Log volume and retention",
                    title=f"Shorten retention for {index['name']}",
                    estimated_monthly_saving=round(float(index.get("monthly_cost", 0)) * ratio * 0.7, 2),
                    effort="medium",
                    detail=f"{index['name']} retains logs for {retention} days, but observed query lookback is {lookback} days.",
                    owner_tag=index.get("owner", "unknown"),
                    remediation_type="retention",
                    metadata={"index": index["name"], "recommended_retention_days": max(lookback, 1)},
                )
            )
        if env == "prod" and float(index.get("debug_gb_per_day", 0)) > 0:
            findings.append(
                Finding(
                    module="Log volume and retention",
                    title=f"Drop DEBUG logs in prod for {index['name']}",
                    estimated_monthly_saving=round(float(index.get("debug_monthly_cost", 0)), 2),
                    effort="low",
                    detail=f"{index['name']} is ingesting {index['debug_gb_per_day']} GB/day of DEBUG logs in the selected environment.",
                    owner_tag=index.get("owner", "unknown"),
                    remediation_type="vector_debug_drop",
                    metadata={"index": index["name"], "project": project, "env": env},
                )
            )
    return findings
