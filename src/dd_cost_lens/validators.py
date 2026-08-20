from __future__ import annotations

from .models import OrgData


class ValidationError(SystemExit):
    def __init__(self, message: str):
        self.message = message
        super().__init__(2)

    def __str__(self) -> str:
        return self.message


def validate_scope(
    data: OrgData,
    scope_tag: str,
    scope_value: str,
    env_tag: str,
    env: str,
) -> None:
    """
    Validate the requested Datadog scope and environment.

    The CLI supports runtime scopes such as:

        project:checkout
        service:epc-api
        app:backend
        team:platform

    collect_live_data currently stores the selected scope value
    internally in the canonical field named "project", even when
    the external Datadog tag is service/app/team.

    Example:

        service:epc-api
        env:staging

    may be represented internally as:

        {
            "project": "epc-api",
            "env": "staging"
        }
    """

    scope_tag = scope_tag.strip()
    scope_value = scope_value.strip()
    env_tag = env_tag.strip()
    env = env.strip()

    if not scope_tag:
        raise ValidationError(
            "❌ Error: Scope tag cannot be empty."
        )

    if not scope_value:
        raise ValidationError(
            "❌ Error: Scope value cannot be empty."
        )

    if not env_tag:
        raise ValidationError(
            "❌ Error: Environment tag cannot be empty."
        )

    if not env:
        raise ValidationError(
            "❌ Error: Environment value cannot be empty."
        )

    collections = (
        data.metrics,
        data.log_indexes,
        data.apm_services,
        data.hosts,
    )

    def scope_matches(row: dict) -> bool:
        return (
            row.get(scope_tag) == scope_value
            or row.get("project") == scope_value
            or (
                row.get("scope_tag") == scope_tag
                and row.get("scope_value") == scope_value
            )
        )

    def env_matches(row: dict) -> bool:
        return (
            row.get(env_tag) == env
            or row.get("env") == env
            or row.get("environment") == env
        )

    scope_exists = (
        scope_value in data.envs
        or any(
            scope_matches(row)
            for collection in collections
            for row in collection
        )
    )

    if not scope_exists:
        scope_label = (
            scope_tag
            .replace("_", " ")
            .strip()
            .capitalize()
        )

        raise ValidationError(
            f"❌ Error: {scope_label} "
            f"'{scope_value}' not found in Datadog metrics."
        )

    recorded_envs = data.envs.get(
        scope_value,
        [],
    )

    env_recorded = env in recorded_envs

    has_telemetry = any(
        scope_matches(row)
        and env_matches(row)
        for collection in collections
        for row in collection
    )

    if not env_recorded and not has_telemetry:
        raise ValidationError(
            f"❌ Error: Environment '{env}' "
            f"has no recorded usage data for "
            f"{scope_tag} '{scope_value}'."
        )

    if not has_telemetry:
        raise ValidationError(
            f"❌ Error: Environment '{env}' "
            f"has no recorded telemetry for "
            f"{scope_tag} '{scope_value}'."
        )
