from dd_cost_lens.data import _extract_live_rows, _list_metrics, discover_live_metadata


class FakeDatadogClient:
    def request(self, method, endpoint_template, **kwargs):
        if endpoint_template == "/api/v2/current_user":
            return {}
        if endpoint_template == "/api/v2/org":
            return {"data": [{"id": "org-abc", "attributes": {"name": "Acme Datadog"}}]}
        if endpoint_template in {"/api/v2/metrics", "/api/v2/apm/services"}:
            return {}
        if endpoint_template == "/api/v1/tags/hosts":
            return {
                "host_tags": [
                    {
                        "host_name": "host-a",
                        "tags_by_source": {
                            "Datadog": ["project:checkout", "env:prod", "team:web"],
                        },
                    },
                    {
                        "host_name": "host-b",
                        "tags_by_source": {
                            "Datadog": ["project:checkout", "env:staging", "team:web"],
                        },
                    },
                    {
                        "host_name": "host-c",
                        "tags_by_source": {
                            "Datadog": ["project:catalog", "env:prod", "team:catalog"],
                        },
                    },
                ]
            }
        raise AssertionError(f"unexpected request: {method} {endpoint_template}")


class FakeServiceDatadogClient(FakeDatadogClient):
    def request(self, method, endpoint_template, **kwargs):
        if endpoint_template == "/api/v2/apm/services":
            assert kwargs["params"] == {"filter[env]": "*"}
            return {
                "data": [
                    {"id": "checkout-api", "attributes": {"service": "checkout-api", "env": "prod"}},
                    {"id": "checkout-api", "attributes": {"service": "checkout-api", "env": "staging"}},
                    {"id": "billing-api", "attributes": {"service": "billing-api", "env": "prod"}},
                ]
            }
        return super().request(method, endpoint_template, **kwargs)


class FakeEnvironmentDatadogClient(FakeDatadogClient):
    def request(self, method, endpoint_template, **kwargs):
        if endpoint_template == "/api/v1/tags/hosts":
            return {
                "host_tags": [
                    {
                        "host_name": "host-a",
                        "tags_by_source": {
                            "Datadog": ["service:api", "environment:production"],
                        },
                    }
                ]
            }
        return super().request(method, endpoint_template, **kwargs)



class FakeMetricTaggedServiceClient(FakeDatadogClient):
    def request(self, method, endpoint_template, **kwargs):
        if endpoint_template == "/api/v1/tags/hosts":
            return {
                "host_tags": [
                    {
                        "host_name": "host-a",
                        "tags_by_source": {
                            "Datadog": ["service:epc-ws"],
                        },
                    }
                ]
            }
        if endpoint_template == "/api/v2/metrics":
            scope = kwargs["params"]["filter[tags]"]
            if scope == "service:epc-ws":
                return {
                    "data": [
                        {"id": "ws.active_connections"},
                        {"id": "ws.disconnection.count"},
                    ]
                }
            if scope == "service:epc-ws AND env:staging":
                return {"data": [{"id": "ws.active_connections"}]}
            if scope == "service:epc-ws AND env:production":
                return {"data": []}
            raise AssertionError(f"unexpected metric scope: {scope}")
        if endpoint_template == "/api/v2/metrics/{metric_name}/all-tags":
            assert kwargs["params"]["filter[tags]"] == "service:epc-ws"
            assert kwargs["params"]["filter[match]"] == "env"
            return {
                "data": {
                    "attributes": {
                        "ingested_tags": [
                            "env:production",
                            "env:staging",
                            "service:epc-ws",
                        ]
                    }
                }
            }
        return super().request(method, endpoint_template, **kwargs)


def test_discovers_organization_projects_and_envs_from_datadog_tags():
    metadata = discover_live_metadata(FakeDatadogClient())

    assert metadata.organization == "Acme Datadog"
    assert metadata.projects == ["catalog", "checkout"]
    assert metadata.envs == {
        "catalog": ["prod"],
        "checkout": ["prod", "staging"],
    }


def test_discovers_envs_for_requested_project_only():
    metadata = discover_live_metadata(FakeDatadogClient(), "project", "checkout")

    assert metadata.projects == ["catalog", "checkout"]
    assert metadata.envs == {"checkout": ["prod", "staging"]}


def test_does_not_add_missing_requested_scope_to_environment_metadata():
    metadata = discover_live_metadata(
        FakeDatadogClient(),
        "service",
        "nonexistent-demo-service-xyz",
    )

    assert "nonexistent-demo-service-xyz" not in metadata.envs


def test_ignores_unscoped_optional_live_data():
    rows = _extract_live_rows(
        {"indexes": [{"name": "main"}]},
        "nonexistent-demo-service-xyz",
        "staging",
        "service",
    )

    assert rows == []


def test_lists_every_metrics_page():
    class PaginatedClient:
        def request(self, method, endpoint_template, **kwargs):
            assert method == "GET"
            assert endpoint_template == "/api/v2/metrics"
            if "page[cursor]" not in kwargs["params"]:
                return {
                    "data": [{"id": "first.metric"}],
                    "meta": {"pagination": {"next_cursor": "page-2"}},
                }
            return {"data": [{"id": "second.metric"}]}

    payload = _list_metrics(PaginatedClient(), {"filter[tags]": "env:prod"})

    assert [item["id"] for item in payload["data"]] == [
        "first.metric",
        "second.metric",
    ]


def test_targeted_metric_lookup_does_not_follow_cursor():
    class CursorClient:
        def request(self, method, endpoint_template, **kwargs):
            return {
                "data": [{"id": "first.metric"}],
                "meta": {"pagination": {"next_cursor": "page-2"}},
            }

    payload = _list_metrics(
        CursorClient(),
        {"filter[tags]": "service:epc-api"},
        page_size=1,
        paginate=False,
    )

    assert [item["id"] for item in payload["data"]] == ["first.metric"]


def test_discovers_custom_scope_tag_values():
    metadata = discover_live_metadata(FakeDatadogClient(), "team")

    assert metadata.projects == ["catalog", "web"]
    assert metadata.envs == {
        "catalog": ["prod"],
        "web": ["prod", "staging"],
    }
    assert metadata.tag_values["project"] == ["catalog", "checkout"]
    assert metadata.tag_values["team"] == ["catalog", "web"]


def test_discovers_service_values_from_apm_when_not_host_tagged():
    metadata = discover_live_metadata(FakeServiceDatadogClient(), "service")

    assert metadata.projects == ["billing-api", "checkout-api"]
    assert metadata.envs == {
        "billing-api": ["prod"],
        "checkout-api": ["prod", "staging"],
    }
    assert metadata.tag_values["service"] == ["billing-api", "checkout-api"]


def test_discovers_custom_environment_tag_key():
    metadata = discover_live_metadata(FakeEnvironmentDatadogClient(), "service", env_tag="environment")

    assert metadata.projects == ["api"]
    assert metadata.envs == {"api": ["production"]}


def test_discovers_environment_from_metric_tags_when_host_tag_is_missing():
    metadata = discover_live_metadata(
        FakeMetricTaggedServiceClient(),
        "service",
        "epc-ws",
    )

    assert metadata.projects == ["epc-ws"]
    assert metadata.envs == {"epc-ws": ["staging"]}
    assert "staging" in metadata.tag_values["env"]


def test_discovers_unscoped_service_environment_from_metric_tags():
    metadata = discover_live_metadata(FakeMetricTaggedServiceClient(), "service")

    assert metadata.projects == ["epc-ws"]
    assert metadata.envs == {"epc-ws": ["staging"]}
