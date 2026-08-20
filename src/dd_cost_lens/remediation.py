from __future__ import annotations

import json
from typing import Any

from .models import Finding


def generate_remediations(findings: list[Finding]) -> list[dict[str, Any]]:
    remediations: list[dict[str, Any]] = []
    used_types: set[str] = set()
    for finding in sorted(findings, key=lambda f: f.estimated_monthly_saving, reverse=True):
        if finding.remediation_type in used_types:
            continue
        snippet = _snippet_for(finding)
        if snippet:
            remediations.append(snippet)
            used_types.add(finding.remediation_type or "")
        if len(remediations) >= 3:
            break
    return remediations


def _snippet_for(finding: Finding) -> dict[str, Any] | None:
    if finding.remediation_type == "vector_debug_drop":
        return {
            "title": finding.title,
            "kind": "vector_toml",
            "content": vector_debug_drop(project=finding.metadata["project"], env=finding.metadata["env"]),
        }
    if finding.remediation_type == "mwl":
        return {
            "title": finding.title,
            "kind": "mwl_json",
            "content": mwl_exclusion_filter(
                metric=finding.metadata["metric"],
                exclude_tags=finding.metadata.get("exclude_tags", []),
                scope=finding.metadata.get("scope", ""),
            ),
        }
    if finding.remediation_type == "apm_sampling":
        return {
            "title": finding.title,
            "kind": "datadog_apm_env",
            "content": apm_sampling_env(finding.metadata["service"], finding.metadata["target_sampling_rate"]),
        }
    if finding.remediation_type == "remove_metric_instrumentation":
        return {
            "title": finding.title,
            "kind": "bash",
            "content": remove_metric_instrumentation(
                finding.metadata["metric"],
                finding.metadata["scope"],
            ),
        }
    return None


def vector_debug_drop(project: str, env: str) -> str:
    return f"""[transforms.drop_debug_{project}_{env}]
type = "filter"
inputs = ["in"]
condition = '!(.level == "DEBUG" && .project == "{project}" && .env == "{env}")'
"""


def mwl_exclusion_filter(metric: str, exclude_tags: list[str], scope: str) -> str:
    payload = {
        "data": {
            "type": "manage_tags",
            "id": metric,
            "attributes": {
                "metric_type": "gauge",
                "include_percentiles": False,
                "tags": [f"!{tag}" for tag in exclude_tags],
                "filter": scope,
            },
        }
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def apm_sampling_env(service: str, target_sampling_rate: float) -> str:
    return f"""# Apply to service {service}
DD_TRACE_SAMPLE_RATE={target_sampling_rate}
DD_TRACE_RATE_LIMIT=100
"""


def remove_metric_instrumentation(metric: str, scope: str) -> str:
    return f"""# Remove the emission of {metric} from the service instrumentation.
# Confirm no dashboards, monitors, notebooks, or SLOs depend on it first.
# Validated Datadog scope: {scope}
"""
