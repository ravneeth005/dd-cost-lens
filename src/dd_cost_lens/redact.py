from __future__ import annotations

from dataclasses import replace
import re
from typing import Any

from .models import Finding, ReportData

SENSITIVE_TAG_NAMES = {"user_id", "container_id", "request_id", "session_id", "trace_id"}


class Redactor:
    def __init__(self) -> None:
        self._maps: dict[str, dict[str, str]] = {
            "organization": {},
            "owner": {},
            "metric": {},
            "service": {},
            "host": {},
            "index": {},
            "project": {},
            "env": {},
        }

    def _alias(self, kind: str, value: Any) -> Any:
        if not isinstance(value, str) or value in {"unknown", ""}:
            return value
        bucket = self._maps[kind]
        if value not in bucket:
            bucket[value] = f"{kind}-{len(bucket) + 1}"
        return bucket[value]

    def redact_report(self, report: ReportData) -> ReportData:
        findings = [self._redact_finding(finding) for finding in report.findings]
        metrics = [self._walk(metric) for metric in report.metrics]
        owner_rollup = {self._alias("owner", owner): amount for owner, amount in report.owner_rollup.items()}
        remediations = [self._walk(remediation) for remediation in report.remediations]
        return ReportData(
            organization=self._alias("organization", report.organization),
            scope_tag=report.scope_tag,
            env_tag=report.env_tag,
            project=self._alias("project", report.project),
            env=self._alias("env", report.env),
            metrics=metrics,
            findings=findings,
            owner_rollup=owner_rollup,
            remediations=remediations,
            metric_monthly_cost_per_timeseries=(
                report.metric_monthly_cost_per_timeseries
            ),
        )

    def _redact_finding(self, finding: Finding) -> Finding:
        metadata = self._walk(finding.metadata)
        title = self._replace_known(finding.title)
        detail = self._replace_known(finding.detail)
        return replace(finding, title=title, detail=detail, owner_tag=self._alias("owner", finding.owner_tag), metadata=metadata)

    def _walk(self, value: Any) -> Any:
        if isinstance(value, dict):
            redacted: dict[str, Any] = {}
            for key, item in value.items():
                if key in self._maps:
                    redacted[key] = self._alias(key, item)
                elif key == "exclude_tags":
                    redacted[key] = ["high_cardinality_tag" for _ in item]
                else:
                    redacted[key] = self._walk(item)
            return redacted
        if isinstance(value, list):
            return [self._walk(item) for item in value]
        if isinstance(value, str):
            return self._replace_known(value)
        return value

    def _replace_known(self, text: str) -> str:
        result = text
        for kind, mapping in self._maps.items():
            for original, alias in sorted(mapping.items(), key=lambda item: len(item[0]), reverse=True):
                result = re.sub(rf"(?<![A-Za-z0-9]){re.escape(original)}(?![A-Za-z0-9])", alias, result)
        for tag in SENSITIVE_TAG_NAMES:
            result = re.sub(rf"(?<![A-Za-z0-9_]){re.escape(tag)}(?![A-Za-z0-9_])", "high_cardinality_tag", result)
        return result
