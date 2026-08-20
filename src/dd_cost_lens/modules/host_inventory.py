from __future__ import annotations

from dd_cost_lens.models import Finding, OrgData


def analyze_host_inventory(data: OrgData, project: str, env: str) -> list[Finding]:
    findings: list[Finding] = []
    for host in data.hosts:
        if host.get("project") != project:
            continue
        if host.get("env") != env and host.get("tier") == "prod":
            findings.append(
                Finding(
                    module="Host inventory",
                    title=f"Move non-prod host {host['host']} off prod tier",
                    estimated_monthly_saving=round(float(host.get("monthly_cost", 0)) * 0.5, 2),
                    effort="low",
                    detail=f"{host['host']} is tagged env:{host.get('env')} but billed at prod tier.",
                    owner_tag=host.get("owner", "unknown"),
                    remediation_type="host_tagging",
                    metadata={"host": host["host"], "env": host.get("env"), "tier": host.get("tier")},
                )
            )
        if host.get("env") == env and host.get("ephemeral"):
            findings.append(
                Finding(
                    module="Host inventory",
                    title=f"Reduce high-water mark impact from {host['host']}",
                    estimated_monthly_saving=round(float(host.get("monthly_cost", 0)) * 0.45, 2),
                    effort="medium",
                    detail=f"{host['host']} is ephemeral and contributes to a high-water mark of {host.get('high_water_mark')}.",
                    owner_tag=host.get("owner", "unknown"),
                    remediation_type="host_inventory",
                    metadata={"host": host["host"], "env": host.get("env")},
                )
            )
    return findings
