"""Read-only analysis service used by the browser interface."""

from __future__ import annotations

import os
from dataclasses import dataclass

from tenacity import RetryError

from ..client import DatadogClient
from ..data import collect_live_data, discover_live_metadata
from ..models import ReportData
from ..modules import (
    analyze_apm_sampling,
    analyze_custom_metric_cardinality,
    analyze_host_inventory,
    analyze_log_volume_and_retention,
    analyze_unqueried_metrics,
    rollup_by_owner,
)
from ..remediation import generate_remediations
from ..report import build_report_data
from ..validators import ValidationError, validate_scope


class AnalysisError(RuntimeError):
    """A safe message that can be displayed by the web interface."""


@dataclass(frozen=True)
class BatchAnalysisResult:
    """Completed and failed scope analyses from one discovery run."""

    reports: list[ReportData]
    failures: list[tuple[str, str, str]]


def discover_scopes(
    scope_tag: str = "service",
    env_tag: str = "env",
    site: str | None = None,
) -> dict[str, object]:
    """Return scope/environment pairs available to configured credentials."""
    client = _client(site)
    try:
        metadata = discover_live_metadata(client, scope_tag, None, env_tag)
    except RetryError as error:
        raise AnalysisError("Datadog discovery failed. Please try again.") from error

    return {
        "organization": metadata.organization,
        "scopes": {
            scope: sorted(environments)
            for scope, environments in sorted(metadata.envs.items())
            if environments
        },
    }


def analyze_scope(
    scope_value: str,
    environment: str,
    scope_tag: str = "service",
    env_tag: str = "env",
    site: str | None = None,
) -> ReportData:
    """Return analysis results without writing a report or printing output."""
    scope_value = scope_value.strip()
    environment = environment.strip()
    if not scope_value or not environment:
        raise AnalysisError("Service and environment are required.")

    client = _client(site)
    try:
        data = collect_live_data(
            client,
            scope_value,
            environment,
            scope_tag,
            env_tag,
            _configured_rate(),
        )
    except RetryError as error:
        raise AnalysisError("Datadog analysis failed. Please try again.") from error

    try:
        validate_scope(data, scope_tag, scope_value, env_tag, environment)
    except ValidationError as error:
        raise AnalysisError(error.message) from error

    findings = []
    findings.extend(analyze_custom_metric_cardinality(data, scope_value, environment))
    findings.extend(analyze_unqueried_metrics(data, scope_value, environment))
    findings.extend(analyze_log_volume_and_retention(data, scope_value, environment))
    findings.extend(analyze_apm_sampling(data, scope_value, environment))
    findings.extend(analyze_host_inventory(data, scope_value, environment))

    return build_report_data(
        os.getenv("DD_ORG_NAME") or data.organization,
        scope_tag,
        env_tag,
        scope_value,
        environment,
        data.metrics,
        findings,
        rollup_by_owner(findings),
        generate_remediations(findings),
        _configured_rate(),
        data.cost_attribution,
        data.analysis_status,
    )


def analyze_all_discovered_scopes(
    scope_tag: str = "service",
    env_tag: str = "env",
    site: str | None = None,
) -> BatchAnalysisResult:
    """Analyze every scope/environment pair returned by Datadog discovery.

    Each scope is processed independently. One unavailable scope therefore
    appears as a failure in the browser without discarding completed reports.
    """
    discovery = discover_scopes(scope_tag, env_tag, site)
    reports: list[ReportData] = []
    failures: list[tuple[str, str, str]] = []

    for scope_value, environments in discovery["scopes"].items():
        for environment in environments:
            try:
                reports.append(
                    analyze_scope(
                        scope_value,
                        environment,
                        scope_tag,
                        env_tag,
                        site,
                    )
                )
            except AnalysisError as error:
                failures.append((scope_value, environment, str(error)))

    return BatchAnalysisResult(reports=reports, failures=failures)


def _client(site: str | None) -> DatadogClient:
    client = DatadogClient(site=site)
    if not client.has_credentials:
        raise AnalysisError("Datadog credentials are missing from the server environment.")
    return client


def _configured_rate() -> float:
    value = os.getenv("DD_COST_LENS_METRIC_TS_MONTHLY_RATE", "0")
    try:
        rate = float(value)
    except ValueError as error:
        raise AnalysisError("DD_COST_LENS_METRIC_TS_MONTHLY_RATE must be a number.") from error
    if rate < 0:
        raise AnalysisError("DD_COST_LENS_METRIC_TS_MONTHLY_RATE cannot be negative.")
    return rate
