from __future__ import annotations

from jinja2 import Environment, PackageLoader, select_autoescape

from .models import Finding, ReportData


def build_report_data(
    organization: str,
    scope_tag: str,
    env_tag: str,
    project: str,
    env: str,
    metrics: list[dict],
    findings: list[Finding],
    owner_rollup: dict[str, float],
    remediations: list[dict],
    metric_monthly_cost_per_timeseries: float = 0,
) -> ReportData:
    ranked = sorted(findings, key=lambda finding: finding.estimated_monthly_saving, reverse=True)
    scoped_metrics = [
        metric
        for metric in metrics
        if (
            metric.get("project") == project
            and metric.get("env") == env
        )
    ]
    return ReportData(
        organization=organization,
        scope_tag=scope_tag,
        env_tag=env_tag,
        project=project,
        env=env,
        metrics=sorted(scoped_metrics, key=lambda metric: metric.get("name", "")),
        findings=ranked,
        owner_rollup=owner_rollup,
        remediations=remediations,
        metric_monthly_cost_per_timeseries=metric_monthly_cost_per_timeseries,
    )


def render_markdown(report: ReportData) -> str:
    env = Environment(
        loader=PackageLoader("dd_cost_lens", "templates"),
        autoescape=select_autoescape(disabled_extensions=("md", "j2")),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("report.md.j2")
    return template.render(report=report)


def render_html(report: ReportData) -> str:
    env = Environment(
        loader=PackageLoader("dd_cost_lens", "templates"),
        autoescape=select_autoescape(default=True),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("report.html.j2")
    return template.render(report=report)
