from pathlib import Path

from dd_cost_lens.cli import main


def test_cli_writes_report_with_headline_first(tmp_path: Path):
    out = tmp_path / "report.md"
    assert main(["run", "--organization", "fusionpact", "--project", "checkout", "--env", "prod", "--fixture", "--out", str(out)]) == 0
    markdown = out.read_text()
    first_line = markdown.splitlines()[0]
    assert first_line == "# Recoverable savings: $5385.00/month"
    assert "| Organization | fusionpact |" in markdown
    assert "| Scope tag | project |" in markdown
    assert "| Scope value | checkout |" in markdown
    assert "| Environment tag | env |" in markdown
    assert "| Environment | prod |" in markdown
    assert "## Updated Feature & Technical Scope" in markdown
    assert "## Metric Inventory" in markdown
    assert "`app.checkout.latency`" in markdown
    assert "`app.catalog.cache`" not in markdown


def test_cli_fails_fast_for_missing_project(capsys):
    assert main(["run", "--project", "missing", "--env", "prod", "--fixture"]) == 2
    captured = capsys.readouterr()
    assert "Project 'missing' not found" in captured.out


def test_cli_runs_all_envs_for_project(tmp_path: Path):
    assert main(["run", "--project", "checkout", "--env", "all", "--fixture", "--out", str(tmp_path)]) == 0
    assert (tmp_path / "checkout-prod.md").exists()
    assert (tmp_path / "checkout-staging.md").exists()


def test_cli_requires_credentials_without_fixture(monkeypatch, capsys):
    monkeypatch.delenv("DD_API_KEY", raising=False)
    monkeypatch.delenv("DD_APP_KEY", raising=False)
    assert main(["run", "--project", "checkout", "--env", "prod"]) == 2
    captured = capsys.readouterr()
    assert "DD_API_KEY and DD_APP_KEY are required" in captured.out


def test_cli_discovers_fixture_project_and_env_tags(capsys):
    assert main(["discover", "--fixture"]) == 0
    captured = capsys.readouterr()
    assert "Organization: fusionpact" in captured.out
    assert "project:checkout" in captured.out
    assert "env:prod" in captured.out
    assert "env:staging" in captured.out


def test_cli_discovers_single_project(capsys):
    assert main(["discover", "--fixture", "--project", "catalog"]) == 0
    captured = capsys.readouterr()
    assert "project:catalog" in captured.out
    assert "project:checkout" not in captured.out


def test_cli_accepts_scope_tag_and_scope_value(tmp_path: Path):
    out = tmp_path / "report.md"
    assert main(["run", "--scope-tag", "project", "--scope-value", "checkout", "--env", "prod", "--fixture", "--out", str(out)]) == 0
    markdown = out.read_text()
    assert "| Scope tag | project |" in markdown
    assert "| Scope value | checkout |" in markdown


def test_cli_accepts_custom_env_tag(tmp_path: Path):
    out = tmp_path / "report.md"
    assert main([
        "run",
        "--scope-tag",
        "project",
        "--scope-value",
        "checkout",
        "--env-tag",
        "environment",
        "--env",
        "prod",
        "--fixture",
        "--out",
        str(out),
    ]) == 0
    markdown = out.read_text()
    assert "| Environment tag | environment |" in markdown
    assert "`project:checkout AND environment:prod`" in markdown


def test_cli_discover_reports_missing_scope_tag(capsys):
    assert main(["discover", "--fixture", "--scope-tag", "service"]) == 0
    captured = capsys.readouterr()
    assert "No `service:<value>` tags were found" in captured.out
    assert "Detected host tag keys:" in captured.out
