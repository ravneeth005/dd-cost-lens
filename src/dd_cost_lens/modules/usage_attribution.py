from __future__ import annotations

from dd_cost_lens.models import Finding


def rollup_by_owner(findings: list[Finding]) -> dict[str, float]:
    owners: dict[str, float] = {}
    for finding in findings:
        owners[finding.owner_tag] = round(owners.get(finding.owner_tag, 0) + finding.estimated_monthly_saving, 2)
    return dict(sorted(owners.items(), key=lambda item: item[1], reverse=True))
