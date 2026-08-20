from dd_cost_lens.models import OrgData
from dd_cost_lens.data import load_synthetic_data
from dd_cost_lens.modules import (
    analyze_apm_sampling,
    analyze_custom_metric_cardinality,
    analyze_host_inventory,
    analyze_log_volume_and_retention,
    analyze_unqueried_metrics,
    rollup_by_owner,
)


def test_cardinality_finding_and_estimate():
    findings = analyze_custom_metric_cardinality(load_synthetic_data(), "checkout", "prod")
    assert findings[0].title == "Reduce cardinality on app.checkout.latency"
    assert findings[0].estimated_monthly_saving == 910
    assert findings[0].effort == "medium"


def test_unqueried_metric_finding():
    findings = analyze_unqueried_metrics(load_synthetic_data(), "checkout", "prod")
    assert len(findings) == 1
    assert findings[0].estimated_monthly_saving == 720
    assert findings[0].effort == "low"
    assert findings[0].remediation_type == "remove_metric_instrumentation"


def test_cardinality_remediation_uses_runtime_service_scope():
    data = load_synthetic_data()
    metric = data.metrics[0]
    metric["scope_tag"] = "service"
    metric["env_tag"] = "environment"
    metric["service"] = "checkout"

    finding = analyze_custom_metric_cardinality(data, "checkout", "prod")[0]

    assert finding.metadata["scope"] == "service:checkout,environment:prod"


def test_log_retention_and_debug_findings():
    findings = analyze_log_volume_and_retention(load_synthetic_data(), "checkout", "prod")
    titles = {finding.title for finding in findings}
    assert "Shorten retention for checkout-main" in titles
    assert "Drop DEBUG logs in prod for checkout-main" in titles
    assert sum(f.estimated_monthly_saving for f in findings) == 1908


def test_apm_sampling_finding():
    findings = analyze_apm_sampling(load_synthetic_data(), "checkout", "prod")
    assert findings[0].title == "Lower trace sampling for checkout-api"
    assert findings[0].estimated_monthly_saving == 990


def test_host_inventory_flags_ephemeral_and_nonprod_prod_tier():
    findings = analyze_host_inventory(load_synthetic_data(), "checkout", "prod")
    assert {finding.estimated_monthly_saving for finding in findings} == {162, 110}


def test_usage_attribution_rollup():
    data = load_synthetic_data()
    findings = []
    findings.extend(analyze_custom_metric_cardinality(data, "checkout", "prod"))
    findings.extend(analyze_apm_sampling(data, "checkout", "prod"))
    rollup = rollup_by_owner(findings)
    assert rollup["team-payments"] == 1900


def test_unqueried_metric_skips_unavailable_cost():
    data = OrgData(
        organization="test",
        projects=["service-a"],
        envs={"service-a": ["production"]},
        metrics=[{
            "name": "metric.without.volume",
            "project": "service-a",
            "env": "production",
            "monthly_cost": None,
            "readers": [],
        }],
        metric_readers={},
        log_indexes=[],
        apm_services=[],
        hosts=[],
    )

    assert analyze_unqueried_metrics(data, "service-a", "production") == []
