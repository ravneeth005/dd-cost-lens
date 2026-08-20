from __future__ import annotations

from dd_cost_lens.models import Finding, OrgData


def analyze_apm_sampling(data: OrgData, project: str, env: str) -> list[Finding]:
    findings: list[Finding] = []
    for service in data.apm_services:
        if service.get("project") != project or service.get("env") != env:
            continue
        if float(service.get("qps", 0)) >= 250 and float(service.get("sampling_rate", 0)) >= 0.95:
            findings.append(
                Finding(
                    module="APM sampling",
                    title=f"Lower trace sampling for {service['service']}",
                    estimated_monthly_saving=round(float(service.get("monthly_cost", 0)) * 0.55, 2),
                    effort="medium",
                    detail=f"{service['service']} runs at {service['qps']} QPS with sampling rate {service['sampling_rate']:.0%}.",
                    owner_tag=service.get("owner", "unknown"),
                    remediation_type="apm_sampling",
                    metadata={"service": service["service"], "target_sampling_rate": 0.2},
                )
            )
    return findings
