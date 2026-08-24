from dd_cost_lens.data import _attribution_total_cost, _attribution_tag_matches


def test_cost_attribution_matches_tag_values_and_sums_dimensions():
    assert _attribution_tag_matches(["epc-ws"], "epc-ws")
    assert _attribution_tag_matches("staging", "staging")
    assert not _attribution_tag_matches(["production"], "staging")
    assert _attribution_total_cost(
        {
            "custom_metric_total_cost": 1.25,
            "apm_total_cost": 2.75,
        }
    ) == 4.0


def test_cost_attribution_prefers_explicit_total_to_avoid_double_counting():
    assert _attribution_total_cost(
        {
            "total_cost": 10,
            "custom_metric_total_cost": 4,
            "apm_total_cost": 6,
        }
    ) == 10.0
