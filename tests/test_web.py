from fastapi.testclient import TestClient

from dd_cost_lens.models import ReportData
from dd_cost_lens.services.analysis import BatchAnalysisResult
from dd_cost_lens.web import app
import dd_cost_lens.web as web


def test_home_displays_discovered_service(monkeypatch):
    monkeypatch.setattr(
        web,
        "discover_scopes",
        lambda: {
            "organization": "Example Org",
            "scopes": {"epc-ws": ["staging"]},
        },
    )

    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert "epc-ws" in response.text
    assert "Example Org" in response.text


def test_analyze_renders_report(monkeypatch):
    report = ReportData(
        organization="Example Org",
        scope_tag="service",
        env_tag="env",
        project="epc-ws",
        env="staging",
        metrics=[],
        findings=[],
        owner_rollup={},
        remediations=[],
        analysis_status={"host_inventory": "No scoped hosts found."},
    )
    monkeypatch.setattr(web, "analyze_scope", lambda service, environment: report)

    response = TestClient(app).post(
        "/analyze",
        data={"scope_value": "epc-ws", "environment": "staging"},
    )

    assert response.status_code == 200
    assert "Telemetry cost review" in response.text
    assert "epc-ws" in response.text


def test_analyze_all_renders_completed_scopes(monkeypatch):
    report = ReportData(
        organization="Example Org",
        scope_tag="service",
        env_tag="env",
        project="epc-ws",
        env="staging",
        metrics=[],
        findings=[],
        owner_rollup={},
        remediations=[],
    )
    monkeypatch.setattr(
        web,
        "analyze_all_discovered_scopes",
        lambda: BatchAnalysisResult(reports=[report], failures=[]),
    )

    response = TestClient(app).post("/analyze-all")

    assert response.status_code == 200
    assert "Scope summary" in response.text
    assert "epc-ws" in response.text
