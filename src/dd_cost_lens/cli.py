from __future__ import annotations

import argparse
import os
from pathlib import Path

from rich.console import Console
from rich.table import Table
from tenacity import RetryError

from .client import DatadogClient, normalize_site
from .data import (
    collect_live_data,
    discover_live_metadata,
    load_synthetic_data,
)
from .modules import (
    analyze_apm_sampling,
    analyze_custom_metric_cardinality,
    analyze_host_inventory,
    analyze_log_volume_and_retention,
    analyze_unqueried_metrics,
    rollup_by_owner,
)
from .redact import Redactor
from .remediation import generate_remediations
from .report import build_report_data, render_html, render_markdown
from .validators import ValidationError, validate_scope


console = Console()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dd-cost-lens")

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    # ---------------------------------------------------------
    # RUN COMMAND
    # ---------------------------------------------------------

    run = subparsers.add_parser(
        "run",
        help="Analyze a scoped Datadog project/environment.",
    )

    run.add_argument(
        "--project",
        default=None,
        help=(
            "Backwards-compatible shortcut for "
            "--scope-tag project --scope-value <name>."
        ),
    )

    run.add_argument(
        "--scope-tag",
        default="project",
        help=(
            "Datadog tag key used to scope analysis, "
            "e.g. project, service, app, team."
        ),
    )

    run.add_argument(
        "--scope-value",
        default=None,
        help=(
            "Datadog tag value used to scope analysis, "
            "e.g. checkout for service:checkout."
        ),
    )

    run.add_argument(
        "--env",
        required=True,
        help=(
            "Datadog environment tag value, or 'all' "
            "to run every environment for the scope."
        ),
    )

    run.add_argument(
        "--env-tag",
        default="env",
        help=(
            "Datadog tag key used for environments, "
            "e.g. env or environment."
        ),
    )

    run.add_argument(
        "--organization",
        default=None,
        help=(
            "Organization name to print in the report. "
            "Defaults to DD_ORG_NAME or the Datadog site."
        ),
    )

    run.add_argument(
        "--redact",
        action="store_true",
    )

    run.add_argument(
        "--out",
        default=None,
    )

    run.add_argument(
        "--format",
        choices=("markdown", "html"),
        default="markdown",
        help="Report format. Defaults to markdown.",
    )

    run.add_argument(
        "--datadog-site",
        default=None,
        help=(
            "Datadog site, defaults to DD_SITE "
            "or datadoghq.com."
        ),
    )

    run.add_argument(
        "--metric-monthly-cost-per-timeseries",
        type=float,
        default=float(
            os.getenv(
                "DD_COST_LENS_METRIC_TS_MONTHLY_RATE",
                "0",
            )
        ),
        help=(
            "Effective monthly cost per indexed custom-metric "
            "timeseries. Defaults to DD_COST_LENS_METRIC_TS_MONTHLY_RATE "
            "or 0 when no contract rate is supplied."
        ),
    )

    run.add_argument(
        "--projects-file",
        default=None,
        help=(
            "Optional newline-delimited scope-value list "
            "for sequential batch runs."
        ),
    )

    run.add_argument(
        "--fixture",
        action="store_true",
        help="Force bundled synthetic fixture data.",
    )

    # ---------------------------------------------------------
    # DISCOVER COMMAND
    # ---------------------------------------------------------

    discover = subparsers.add_parser(
        "discover",
        help="Fetch organization, scope tags, and env tags from Datadog.",
    )

    discover.add_argument(
        "--project",
        default=None,
        help=(
            "Backwards-compatible shortcut for "
            "--scope-tag project --scope-value <name>."
        ),
    )

    discover.add_argument(
        "--scope-tag",
        default="project",
        help=(
            "Datadog tag key to discover, "
            "e.g. project, service, app, team."
        ),
    )

    discover.add_argument(
        "--scope-value",
        default=None,
        help="Optional tag value to filter environment discovery.",
    )

    discover.add_argument(
        "--env-tag",
        default="env",
        help=(
            "Datadog tag key used for environments, "
            "e.g. env or environment."
        ),
    )

    discover.add_argument(
        "--datadog-site",
        default=None,
        help=(
            "Datadog site, defaults to DD_SITE "
            "or datadoghq.com."
        ),
    )

    discover.add_argument(
        "--fixture",
        action="store_true",
        help="Use bundled synthetic fixture data.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    # =========================================================
    # RUN
    # =========================================================

    if args.command == "run":
        scope_value = _scope_value(args)

        if not scope_value:
            console.print(
                "❌ Error: Provide --scope-value <value> "
                "or --project <name>."
            )
            return 2

        if args.metric_monthly_cost_per_timeseries < 0:
            console.print(
                "❌ Error: --metric-monthly-cost-per-timeseries "
                "must be zero or greater."
            )
            return 2

        projects = _projects(
            scope_value,
            args.projects_file,
        )

        status = 0
        client = None

        if args.fixture:
            metadata = load_synthetic_data()

        else:
            client = DatadogClient(
                site=args.datadog_site,
            )

            if not client.has_credentials:
                console.print(
                    "❌ Error: DD_API_KEY and DD_APP_KEY "
                    "are required unless --fixture is used."
                )
                return 2

            metadata = discover_live_metadata(
                client,
                args.scope_tag,
                scope_value,
                args.env_tag,
            )

        for project in projects:
            envs = _envs_for_project(
                metadata,
                project,
                args.env,
            )

            if not envs:
                scope_label = _scope_label(args.scope_tag)

                console.print(
                    f"❌ Error: {scope_label} '{project}' "
                    "not found in Datadog metrics."
                )

                status = max(status, 2)
                continue

            for env in envs:
                try:
                    if (
                        args.fixture
                        or client is None
                        or not client.has_credentials
                    ):
                        data = metadata

                    else:
                        data = collect_live_data(
                            client,
                            project,
                            env,
                            args.scope_tag,
                            args.env_tag,
                            args.metric_monthly_cost_per_timeseries,
                        )

                except RetryError as error:
                    console.print(
                        _datadog_error_message(error)
                    )

                    status = max(status, 2)
                    continue

                status = max(
                    status,
                    run_once(
                        project,
                        env,
                        args,
                        data,
                    ),
                )

        return status

    # =========================================================
    # DISCOVER
    # =========================================================

    if args.command == "discover":
        return discover(args)

    return 1


def discover(args: argparse.Namespace) -> int:
    scope_value = _scope_value(args)

    if args.fixture:
        metadata = load_synthetic_data()

    else:
        client = DatadogClient(
            site=args.datadog_site,
        )

        if not client.has_credentials:
            console.print(
                "❌ Error: DD_API_KEY and DD_APP_KEY "
                "are required unless --fixture is used."
            )
            return 2

        metadata = discover_live_metadata(
            client,
            args.scope_tag,
            scope_value,
            args.env_tag,
        )

    discovered_values = _discovered_scope_values(
        metadata,
        args.scope_tag,
    )

    projects = (
        [scope_value]
        if scope_value
        else discovered_values
    )

    projects = [
        project
        for project in projects
        if project in discovered_values
    ]

    if scope_value and not projects:
        scope_label = _scope_label(args.scope_tag)

        console.print(
            f"❌ Error: {scope_label} '{scope_value}' "
            "not found in Datadog metrics."
        )

        return 2

    console.print(
        f"Organization: {metadata.organization}"
    )

    if not projects:
        console.print(
            f"No `{args.scope_tag}:<value>` tags "
            "were found in Datadog discovery data."
        )

        _print_detected_tag_keys(metadata)
        return 0

    table = Table(
        title=(
            f"Datadog "
            f"{args.scope_tag}/Environment Tags"
        )
    )

    table.add_column("Scope tag")
    table.add_column("Environment tags")

    for project in projects:
        environment_values = metadata.envs.get(
            project,
            [],
        )

        environment_text = (
            ", ".join(
                f"{args.env_tag}:{env}"
                for env in environment_values
            )
            or "-"
        )

        table.add_row(
            f"{args.scope_tag}:{project}",
            environment_text,
        )

    console.print(table)

    if projects and not any(
        metadata.envs.get(project)
        for project in projects
    ):
        console.print(
            f"No `{args.env_tag}:<value>` tags "
            f"were paired with "
            f"`{args.scope_tag}:<value>`."
        )

        _print_detected_tag_keys(metadata)

    return 0


def run_once(
    project: str,
    env: str,
    args: argparse.Namespace,
    data=None,
) -> int:
    data = data or _load_data(
        args,
        project,
        env,
    )

    # ---------------------------------------------------------
    # IMPORTANT:
    # Generic scope validation.
    #
    # Example:
    #
    # scope_tag   = service
    # project     = epc-api
    # env_tag     = env
    # env         = staging
    #
    # This must NOT be hardcoded to "project".
    # ---------------------------------------------------------

    try:
        validate_scope(
            data,
            args.scope_tag,
            project,
            args.env_tag,
            env,
        )

    except ValidationError as error:
        console.print(
            _scope_error_message(
                error.message,
                args.scope_tag,
            )
        )

        return int(error.code)

    # ---------------------------------------------------------
    # ANALYSIS
    # ---------------------------------------------------------

    findings = []

    findings.extend(
        analyze_custom_metric_cardinality(
            data,
            project,
            env,
        )
    )

    findings.extend(
        analyze_unqueried_metrics(
            data,
            project,
            env,
        )
    )

    findings.extend(
        analyze_log_volume_and_retention(
            data,
            project,
            env,
        )
    )

    findings.extend(
        analyze_apm_sampling(
            data,
            project,
            env,
        )
    )

    findings.extend(
        analyze_host_inventory(
            data,
            project,
            env,
        )
    )

    # ---------------------------------------------------------
    # OWNER ROLLUP
    # ---------------------------------------------------------

    owner_rollup = rollup_by_owner(
        findings
    )

    # ---------------------------------------------------------
    # REPORT
    # ---------------------------------------------------------

    report = build_report_data(
        _organization_name(
            args,
            data,
        ),
        args.scope_tag,
        args.env_tag,
        project,
        env,
        data.metrics,
        findings,
        owner_rollup,
        generate_remediations(findings),
        args.metric_monthly_cost_per_timeseries,
    )

    if args.redact:
        report = Redactor().redact_report(
            report
        )

    rendered_report = (
        render_html(report)
        if args.format == "html"
        else render_markdown(report)
    )

    out = _output_path(
        args.out,
        project,
        env,
        args.env == "all",
        args.format,
    )

    out.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    out.write_text(
        rendered_report,
        encoding="utf-8",
    )

    console.print(
        f"Report written to {out}"
    )

    console.print(
        "Recoverable savings: "
        f"${report.headline_savings:.2f}/month"
    )

    return 0


def _load_data(
    args: argparse.Namespace,
    project: str,
    env: str,
):
    if args.fixture:
        return load_synthetic_data()

    client = DatadogClient(
        site=args.datadog_site,
    )

    if not client.has_credentials:
        raise RuntimeError(
            "DD_API_KEY and DD_APP_KEY are required "
            "unless --fixture is used."
        )

    return collect_live_data(
        client,
        project,
        env,
        args.scope_tag,
        args.env_tag,
    )


def _organization_name(
    args: argparse.Namespace,
    data,
) -> str:
    return (
        args.organization
        or os.getenv("DD_ORG_NAME")
        or data.organization
        or normalize_site(
            args.datadog_site
            or os.getenv("DD_SITE")
            or "datadoghq.com"
        )
    )


def _envs_for_project(
    data,
    project: str,
    env: str,
) -> list[str]:
    if env != "all":
        return [env]

    return list(
        data.envs.get(
            project,
            [],
        )
    )


def _output_path(
    out: str | None,
    project: str,
    env: str,
    multi_env: bool,
    report_format: str = "markdown",
) -> Path:
    suffix = ".html" if report_format == "html" else ".md"

    if not out:
        return (
            Path("reports")
            / f"{project}-{env}{suffix}"
        )

    path = Path(out)

    if multi_env or path.suffix == "":
        return (
            path
            / f"{project}-{env}{suffix}"
        )

    return path


def _projects(
    project: str,
    projects_file: str | None,
) -> list[str]:
    if not projects_file:
        return [project]

    items = [
        line.strip()
        for line in Path(
            projects_file
        ).read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    ]

    return items or [project]


def _scope_value(
    args: argparse.Namespace,
) -> str | None:
    return (
        args.scope_value
        or args.project
    )


def _scope_label(
    scope_tag: str,
) -> str:
    return (
        scope_tag
        .replace("_", " ")
        .strip()
        .capitalize()
    )


def _scope_error_message(
    message: str,
    scope_tag: str,
) -> str:
    if scope_tag == "project":
        return message

    scope_label = _scope_label(
        scope_tag
    )

    return (
        message
        .replace(
            "Project",
            scope_label,
        )
        .replace(
            "project",
            scope_tag,
        )
    )


def _print_detected_tag_keys(
    metadata,
) -> None:
    if not metadata.tag_values:
        console.print(
            "No tag values with key:value format "
            "were returned by Datadog."
        )
        return

    keys = ", ".join(
        metadata.tag_values.keys()
    )

    console.print(
        f"Detected host tag keys: {keys}"
    )


def _discovered_scope_values(
    metadata,
    scope_tag: str,
) -> list[str]:
    if scope_tag == "project":
        return metadata.projects

    return metadata.tag_values.get(
        scope_tag,
        [],
    )


def _datadog_error_message(
    error: RetryError,
) -> str:
    cause = error.last_attempt.exception()

    response = getattr(
        cause,
        "response",
        None,
    )

    if response is not None:
        detail = response.text.strip()

        return (
            "❌ Error: Datadog API returned "
            f"{response.status_code} "
            f"for {response.url}. "
            f"{detail}"
        )

    return (
        "❌ Error: Datadog API request failed: "
        f"{cause}"
    )


if __name__ == "__main__":
    raise SystemExit(main())
