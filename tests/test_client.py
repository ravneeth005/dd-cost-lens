from dd_cost_lens.client import DatadogClient, normalize_site


def test_normalize_datadog_site_from_markdown_link():
    assert normalize_site("[us5.datadoghq.com](http://us5.datadoghq.com/)") == "us5.datadoghq.com"


def test_normalize_datadog_site_from_url():
    assert normalize_site("https://api.us5.datadoghq.com/") == "us5.datadoghq.com"


def test_client_uses_normalized_site_for_base_url():
    client = DatadogClient(site="https://us5.datadoghq.com/", api_key="api", app_key="app")
    assert client.site == "us5.datadoghq.com"
    assert client.base_url == "https://api.us5.datadoghq.com"
