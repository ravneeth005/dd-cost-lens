from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Effort = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class Finding:
    module: str
    title: str
    estimated_monthly_saving: float
    effort: Effort
    detail: str
    owner_tag: str
    remediation_type: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class OrgData:
    organization: str
    projects: list[str]
    envs: dict[str, list[str]]
    metrics: list[dict[str, Any]]
    metric_readers: dict[str, list[str]]
    log_indexes: list[dict[str, Any]]
    apm_services: list[dict[str, Any]]
    hosts: list[dict[str, Any]]
    tag_values: dict[str, list[str]] = field(default_factory=dict)
    cost_attribution: dict[str, Any] | None = None


@dataclass
class ReportData:
    organization: str
    scope_tag: str
    env_tag: str
    project: str
    env: str
    metrics: list[dict[str, Any]]
    findings: list[Finding]
    owner_rollup: dict[str, float]
    remediations: list[dict[str, Any]]
    metric_monthly_cost_per_timeseries: float = 0
    cost_attribution: dict[str, Any] | None = None

    @property
    def headline_savings(self) -> float:
        return round(sum(f.estimated_monthly_saving for f in self.findings), 2)

    @property
    def metric_volume_unavailable(self) -> bool:
        """Whether Datadog omitted indexed volume for any scoped metric."""
        return any(
            "volume_available" in metric
            and not metric["volume_available"]
            for metric in self.metrics
        )

    @property
    def fallback_cost_used(self) -> bool:
        return any(
            metric.get("cost_source") == "fallback_allocation"
            for metric in self.metrics
        )
