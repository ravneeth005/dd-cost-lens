from dd_cost_lens.data import load_synthetic_data
from dd_cost_lens.modules import (
    analyze_apm_sampling,
    analyze_custom_metric_cardinality,
    analyze_host_inventory,
    analyze_log_volume_and_retention,
    rollup_by_owner,
)
from dd_cost_lens.redact import Redactor
from dd_cost_lens.remediation import generate_remediations
from dd_cost_lens.report import build_report_data, render_html, render_markdown


def test_redact_removes_identifying_strings_from_report():
    data = load_synthetic_data()
    findings = []
    findings.extend(analyze_custom_metric_cardinality(data, "checkout", "prod"))
    findings.extend(analyze_log_volume_and_retention(data, "checkout", "prod"))
    findings.extend(analyze_apm_sampling(data, "checkout", "prod"))
    findings.extend(analyze_host_inventory(data, "checkout", "prod"))
    report = build_report_data("fusionpact", "project", "env", "checkout", "prod", data.metrics, findings, rollup_by_owner(findings), generate_remediations(findings))
    redacted = Redactor().redact_report(report)
    markdown = render_markdown(redacted)
    forbidden = [
        "checkout",
        "prod",
        "fusionpact",
        "team-payments",
        "team-web",
        "app.checkout.latency",
        "checkout-api",
        "checkout-main",
        "staging",
        "user_id",
        "session_id",
    ]
    for value in forbidden:
        assert value not in markdown
    assert "project-1" in markdown
    assert "env-1" in markdown
    assert "organization-1" in markdown


def test_html_report_is_self_contained_and_escaped():
    report = build_report_data(
        "<example-org>",
        "service",
        "env",
        "<example-service>",
        "prod",
        [],
        [],
        {},
        [],
    )

    html = render_html(report)

    assert "<!doctype html>" in html
    assert "&lt;example-org&gt;" in html
