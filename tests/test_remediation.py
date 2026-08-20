import json

from dd_cost_lens.data import load_synthetic_data
from dd_cost_lens.modules import analyze_apm_sampling, analyze_custom_metric_cardinality, analyze_log_volume_and_retention, analyze_unqueried_metrics
from dd_cost_lens.remediation import generate_remediations, mwl_exclusion_filter, vector_debug_drop


def test_vector_config_is_directly_usable_toml_shape():
    snippet = vector_debug_drop("checkout", "prod")
    assert '[transforms.drop_debug_checkout_prod]' in snippet
    assert 'type = "filter"' in snippet
    assert '.level == "DEBUG"' in snippet


def test_mwl_exclusion_filter_is_valid_json():
    payload = json.loads(mwl_exclusion_filter("app.checkout.latency", ["user_id"], "project:checkout,env:prod"))
    assert payload["data"]["id"] == "app.checkout.latency"
    assert payload["data"]["attributes"]["tags"] == ["!user_id"]


def test_generates_top_three_remediation_types():
    data = load_synthetic_data()
    findings = []
    findings.extend(analyze_custom_metric_cardinality(data, "checkout", "prod"))
    findings.extend(analyze_log_volume_and_retention(data, "checkout", "prod"))
    findings.extend(analyze_apm_sampling(data, "checkout", "prod"))
    remediations = generate_remediations(findings)
    assert {item["kind"] for item in remediations} == {"mwl_json", "vector_toml", "datadog_apm_env"}


def test_unqueried_metric_remediation_requires_removing_instrumentation():
    findings = analyze_unqueried_metrics(load_synthetic_data(), "checkout", "prod")
    remediation = generate_remediations(findings)[0]

    assert remediation["kind"] == "bash"
    assert "Remove the emission" in remediation["content"]
