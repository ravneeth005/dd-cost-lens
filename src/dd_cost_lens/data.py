from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
from tenacity import RetryError

from .client import DatadogClient
from .models import OrgData


FIXTURE_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "synthetic_org.json"
)

METRIC_LOOKBACK_SECONDS = 604800
METRICS_PAGE_SIZE = 1000


def _list_metrics(
    client: DatadogClient,
    params: dict[str, Any],
    page_size: int = METRICS_PAGE_SIZE,
    paginate: bool = True,
) -> dict[str, Any]:
    """Read every page returned by Datadog's paginated metrics endpoint."""

    request_params = {
        **params,
        "page[size]": page_size,
    }
    metrics: list[Any] = []

    while True:
        payload = client.request(
            "GET",
            "/api/v2/metrics",
            params=request_params,
        )
        if isinstance(payload, dict):
            page_metrics = payload.get("data", [])
            if isinstance(page_metrics, list):
                metrics.extend(page_metrics)

        next_cursor = (
            payload.get("meta", {})
            .get("pagination", {})
            .get("next_cursor")
            if isinstance(payload, dict)
            else None
        )
        if not next_cursor:
            break

        if not paginate:
            break

        request_params = {
            **params,
            "page[cursor]": next_cursor,
        }

    return {"data": metrics}


def load_synthetic_data() -> OrgData:
    """
    Load bundled synthetic fixture data.

    This is used only when --fixture is supplied.
    """

    payload = json.loads(
        FIXTURE_PATH.read_text(
            encoding="utf-8"
        )
    )

    return OrgData(**payload)


def collect_live_data(
    client: DatadogClient,
    project: str,
    env: str,
    scope_tag: str = "project",
    env_tag: str = "env",
    metric_monthly_cost_per_timeseries: float = 0,
) -> OrgData:
    """
    Collect live Datadog telemetry for one runtime scope.

    Example:

        scope_tag = "service"
        project = "epc-api"
        env_tag = "env"
        env = "staging"

    Datadog query:

        service:epc-api AND env:staging

    `project` remains the internal canonical scope-value field
    because the existing analysis modules use that field.

    The actual runtime Datadog scope is also stored using:

        scope_tag
        scope_value
    """

    query = (
        f"{scope_tag}:{project} "
        f"AND {env_tag}:{env}"
    )

    # =========================================================
    # METADATA
    # =========================================================

    metadata = discover_live_metadata(
        client,
        scope_tag=scope_tag,
        scope_value=project,
        env_tag=env_tag,
    )

    # =========================================================
    # REAL METRICS FOR THE SELECTED SCOPE
    # =========================================================

    metrics_payload = _list_metrics(
        client,
        {
            "filter[tags]": query,
            "window[seconds]": METRIC_LOOKBACK_SECONDS,
        },
    )

    metric_names = _metric_names(
        metrics_payload
    )

    # =========================================================
    # DATADOG OBJECTS USED TO DETECT READERS
    # =========================================================

    dashboards = _try_request(
        client,
        "GET",
        "/api/v1/dashboard",
    )

    monitors = _try_request(
        client,
        "GET",
        "/api/v1/monitor",
        params={
            "query": query,
        },
    )

    notebooks = _try_request(
        client,
        "GET",
        "/api/v1/notebooks",
        params={
            "query": query,
        },
    )

    # =========================================================
    # OPTIONAL LOG / APM / HOST DATA
    # =========================================================

    indexes = _try_request(
        client,
        "GET",
        "/api/v1/logs/config/indexes",
    )

    services = _try_request(
        client,
        "GET",
        "/api/v2/apm/services",
        params={
            "filter[env]": env,
        },
    )

    hosts_payload = _try_request(
        client,
        "GET",
        "/api/v1/tags/hosts",
        params={
            "filter": query,
        },
    )

    # Older Datadog organizations/sites may return 404.
    # Host usage must not stop the metrics report.
    usage_hosts = _try_request(
        client,
        "GET",
        "/api/v1/usage/hosts",
    )

    # =========================================================
    # BUILD METRIC ROWS
    # =========================================================

    metric_rows: list[
        dict[str, Any]
    ] = []

    metric_readers: dict[
        str,
        list[str],
    ] = {}

    for name in metric_names:

        # -----------------------------------------------------
        # REAL METRIC TAG INFORMATION
        # -----------------------------------------------------

        tags_payload = _try_request(
            client,
            "GET",
            (
                "/api/v2/metrics/"
                "{metric_name}/all-tags"
            ),
            endpoint=(
                f"/api/v2/metrics/"
                f"{name}/all-tags"
            ),
            params={
                "window[seconds]": (
                    METRIC_LOOKBACK_SECONDS
                ),
                "filter[tags]": query,
            },
        )

        # -----------------------------------------------------
        # REAL METRIC VOLUME
        # -----------------------------------------------------

        volume_payload = _try_request(
            client,
            "GET",
            (
                "/api/v2/metrics/"
                "{metric_name}/volumes"
            ),
            endpoint=(
                f"/api/v2/metrics/"
                f"{name}/volumes"
            ),
        )

        volume_attributes = (
            _data_attributes(
                volume_payload
            )
        )

        volume_available = (
            "indexed_volume" in volume_attributes
            and volume_attributes["indexed_volume"] is not None
        )

        indexed_volume = _as_number(volume_attributes["indexed_volume"], default=0) if volume_available else None

        ingested_volume = (
            volume_attributes.get(
                "ingested_volume"
            )
        )

        # -----------------------------------------------------
        # TAG SUMMARY
        # -----------------------------------------------------

        tag_summary = (
            _metric_tag_summary(
                tags_payload
            )
        )

        # -----------------------------------------------------
        # DASHBOARD / MONITOR / NOTEBOOK READERS
        # -----------------------------------------------------

        readers: list[str] = []

        if _payload_mentions_metric(
            dashboards,
            name,
        ):
            readers.append(
                "dashboard"
            )

        if _payload_mentions_metric(
            monitors,
            name,
        ):
            readers.append(
                "monitor"
            )

        if _payload_mentions_metric(
            notebooks,
            name,
        ):
            readers.append(
                "notebook"
            )

        metric_readers[
            name
        ] = readers

        # -----------------------------------------------------
        # CANONICAL METRIC ROW
        # -----------------------------------------------------

        row: dict[str, Any] = {
            "name": name,

            # Internal canonical scope.
            "project": project,
            "env": env,

            # Actual Datadog runtime scope.
            "scope_tag": scope_tag,
            "scope_value": project,
            "env_tag": env_tag,

            # A service is a valid cost owner when no team tag is available.
            "owner": f"{scope_tag}:{project}",

            # Datadog does not expose an invoice allocation per metric. The
            # caller supplies its effective contract rate when estimates are
            # required; otherwise this deliberately remains zero.
            "monthly_cost": (
                round(float(indexed_volume) * metric_monthly_cost_per_timeseries, 2)
                if volume_available
                else None
            ),

            # Existing cardinality analyzer expects timeseries.
            "timeseries": indexed_volume or 0,

            # Preserve Datadog volume values.
            "indexed_volume": indexed_volume,
            "volume_available": volume_available,
            "ingested_volume": ingested_volume,

            # Tag information.
            "top_tag": (
                tag_summary[
                    "top_tag"
                ]
            ),

            "tag_values": (
                tag_summary[
                    "tag_values"
                ]
            ),

            # IMPORTANT:
            # Must remain list[str].
            "offending_tags": (
                tag_summary[
                    "offending_tags"
                ]
            ),

            "tag_cardinalities": (
                tag_summary[
                    "tag_cardinalities"
                ]
            ),

            "indexed_tags": (
                tag_summary[
                    "indexed_tags"
                ]
            ),

            "ingested_tags": (
                tag_summary[
                    "ingested_tags"
                ]
            ),

            "readers": readers,
        }

        # Preserve actual runtime Datadog tag names.

        row[
            scope_tag
        ] = project

        row[
            env_tag
        ] = env

        metric_rows.append(
            row
        )

    # =========================================================
    # NORMALIZE METADATA
    # =========================================================

    projects = sorted(
        set(
            metadata.projects
        )
        | {
            project
        }
    )

    # Do not add a requested environment to discovery metadata. Validation
    # must be based on telemetry actually returned for this scope.
    envs = {
        key: list(values)
        for key, values in metadata.envs.items()
    }

    tag_values = {
        key: list(values)
        for key, values
        in metadata.tag_values.items()
    }

    scope_values = set(
        tag_values.get(
            scope_tag,
            [],
        )
    )

    scope_values.add(
        project
    )

    tag_values[
        scope_tag
    ] = sorted(
        scope_values
    )

    environment_values = set(
        tag_values.get(
            env_tag,
            [],
        )
    )

    environment_values.add(
        env
    )

    tag_values[
        env_tag
    ] = sorted(
        environment_values
    )

    # =========================================================
    # RETURN ORG DATA
    # =========================================================

    return OrgData(
        organization=(
            metadata.organization
        ),

        projects=projects,

        envs=envs,

        metrics=metric_rows,

        metric_readers=(
            metric_readers
        ),

        log_indexes=(
            _extract_live_rows(
                indexes,
                project,
                env,
                scope_tag,
                env_tag,
            )
        ),

        apm_services=(
            _extract_live_rows(
                services,
                project,
                env,
                scope_tag,
                env_tag,
            )
        ),

        hosts=(
            _extract_live_rows(
                {
                    "hosts": (
                        hosts_payload
                    ),
                    "usage": (
                        usage_hosts
                    ),
                },
                project,
                env,
                scope_tag,
                env_tag,
            )
        ),

        tag_values=tag_values,
    )


def discover_live_metadata(
    client: DatadogClient,
    scope_tag: str = "project",
    scope_value: str | None = None,
    env_tag: str = "env",
) -> OrgData:
    """
    Discover Datadog organization and scope metadata.

    IMPORTANT:

    /api/v2/current_user is tried first because it contains the
    human-readable Datadog organization name.

    Example:

        Fusionpact Technologies Inc.

    rather than only the organization UUID.
    """

    # =========================================================
    # ORGANIZATION NAME
    # =========================================================

    current_user_payload = _try_request(
        client,
        "GET",
        "/api/v2/current_user",
    )

    organization_name = _org_name(
        current_user_payload
    )

    # ---------------------------------------------------------
    # Fallback organization APIs
    # ---------------------------------------------------------

    if organization_name == "unknown":

        org_payload = _try_request(
            client,
            "GET",
            "/api/v2/org",
        )

        organization_name = _org_name(
            org_payload
        )

    if organization_name == "unknown":

        org_payload = _try_request(
            client,
            "GET",
            "/api/v1/org",
        )

        organization_name = _org_name(
            org_payload
        )

    # =========================================================
    # HOST TAG DISCOVERY
    # =========================================================

    host_tags_payload = _try_request(
        client,
        "GET",
        "/api/v1/tags/hosts",
    )

    tag_values = (
        _tag_values_from_host_tags(
            host_tags_payload
        )
    )

    projects, envs = (
        _scope_envs_from_host_tags(
            host_tags_payload,
            scope_tag,
            env_tag,
        )
    )

    # =========================================================
    # SERVICE DISCOVERY THROUGH APM
    # =========================================================

    if scope_tag == "service":

        apm_payload = _try_request(
            client,
            "GET",
            "/api/v2/apm/services",
            params={
                "filter[env]": "*",
            },
        )

        (
            service_values,
            service_envs,
        ) = (
            _service_envs_from_apm_services(
                apm_payload
            )
        )

        if service_values:

            tag_values[
                "service"
            ] = sorted(
                set(
                    tag_values.get(
                        "service",
                        [],
                    )
                )
                | set(
                    service_values
                )
            )

        projects = sorted(
            set(projects)
            | set(
                service_values
            )
        )

        for (
            service_name,
            values,
        ) in service_envs.items():

            existing = set(
                envs.get(
                    service_name,
                    [],
                )
            )

            existing.update(
                values
            )

            envs[
                service_name
            ] = sorted(
                existing
            )

    if scope_tag == "service" and not scope_value:
        for service_name in projects:
            metric_envs = _metric_environment_values_for_scope(
                client,
                scope_tag,
                service_name,
                env_tag,
            )

            if not metric_envs:
                continue

            envs[service_name] = sorted(
                set(envs.get(service_name, [])) | set(metric_envs)
            )

            discovered_env_values = set(
                tag_values.get(env_tag, [])
            )
            discovered_env_values.update(metric_envs)
            tag_values[env_tag] = sorted(
                discovered_env_values
            )

    # =========================================================
    # VERIFY EXPLICIT SCOPE THROUGH REAL METRICS
    # =========================================================

    if scope_value:

        scoped_metrics = _list_metrics(
            client,
            {
                "filter[tags]": (
                    f"{scope_tag}:"
                    f"{scope_value}"
                ),
                "window[seconds]": METRIC_LOOKBACK_SECONDS,
            },
        )

        scoped_metric_names = _metric_names(
            scoped_metrics
        )

        if scoped_metric_names:

            projects = sorted(
                set(projects)
                | {
                    scope_value
                }
            )

            discovered_values = set(
                tag_values.get(
                    scope_tag,
                    [],
                )
            )

            discovered_values.add(
                scope_value
            )

            tag_values[
                scope_tag
            ] = sorted(
                discovered_values
            )

            metric_envs = _environment_values_from_metrics(
                client,
                scoped_metric_names,
                scope_tag,
                scope_value,
                env_tag,
            )

            if metric_envs:
                envs[scope_value] = sorted(
                    set(envs.get(scope_value, [])) | set(metric_envs)
                )
                discovered_env_values = set(
                    tag_values.get(env_tag, [])
                )
                discovered_env_values.update(metric_envs)
                tag_values[env_tag] = sorted(
                    discovered_env_values
                )
            else:
                envs.setdefault(
                    scope_value,
                    [],
                )

        # A targeted discovery must not expose environment values from other
        # scopes. This is also the metadata used to validate `run`.
        if scope_value in projects:
            envs = {
                scope_value: envs.get(
                    scope_value,
                    [],
                )
            }
        else:
            envs = {}

    return OrgData(
        organization=(
            organization_name
        ),

        projects=projects,

        envs=envs,

        metrics=[],

        metric_readers={},

        log_indexes=[],

        apm_services=[],

        hosts=[],

        tag_values=tag_values,
    )


def _org_name(
    payload: Any,
) -> str:
    """
    Extract the human-readable Datadog organization name.

    For /api/v2/current_user, Datadog returns organization
    resources inside the `included` array:

        {
            "type": "orgs",
            "id": "...UUID...",
            "attributes": {
                "name": "Fusionpact Technologies Inc."
            }
        }

    The organization name is preferred over the UUID.
    """

    if not isinstance(
        payload,
        dict,
    ):
        return "unknown"

    # =========================================================
    # /api/v2/current_user
    # =========================================================

    included = payload.get(
        "included",
        [],
    )

    if isinstance(
        included,
        list,
    ):

        for item in included:

            if not isinstance(
                item,
                dict,
            ):
                continue

            if (
                item.get("type")
                != "orgs"
            ):
                continue

            attributes = (
                item.get(
                    "attributes",
                    {},
                )
            )

            if not isinstance(
                attributes,
                dict,
            ):
                continue

            name = (
                attributes.get(
                    "name"
                )
            )

            if (
                isinstance(
                    name,
                    str,
                )
                and name
            ):
                return name

    # =========================================================
    # DIRECT NAME
    # =========================================================

    name = payload.get(
        "name"
    )

    if (
        isinstance(
            name,
            str,
        )
        and name
    ):
        return name

    # =========================================================
    # V1 ORG RESPONSE
    # =========================================================

    org = payload.get(
        "org"
    )

    if isinstance(
        org,
        dict,
    ):

        name = org.get(
            "name"
        )

        if (
            isinstance(
                name,
                str,
            )
            and name
        ):
            return name

    # =========================================================
    # V2 SINGLE DATA OBJECT
    # =========================================================

    data = payload.get(
        "data"
    )

    if isinstance(
        data,
        dict,
    ):

        attributes = (
            data.get(
                "attributes",
                {},
            )
        )

        if isinstance(
            attributes,
            dict,
        ):

            name = attributes.get(
                "name"
            )

            if (
                isinstance(
                    name,
                    str,
                )
                and name
            ):
                return name

    # =========================================================
    # V2 DATA LIST
    # =========================================================

    if isinstance(
        data,
        list,
    ):

        for item in data:

            if not isinstance(
                item,
                dict,
            ):
                continue

            attributes = (
                item.get(
                    "attributes",
                    {},
                )
            )

            if not isinstance(
                attributes,
                dict,
            ):
                continue

            name = attributes.get(
                "name"
            )

            if (
                isinstance(
                    name,
                    str,
                )
                and name
            ):
                return name

    return "unknown"


def _metric_names(
    payload: Any,
) -> list[str]:
    """
    Extract metric names from Datadog v1 or v2 responses.
    """

    if not isinstance(
        payload,
        dict,
    ):
        return []

    names: set[str] = set()

    # V1 shape.
    metrics = payload.get(
        "metrics"
    )

    if isinstance(
        metrics,
        list,
    ):

        for item in metrics:

            if (
                isinstance(
                    item,
                    str,
                )
                and item
            ):
                names.add(
                    item
                )

    # V2 shape.
    data = payload.get(
        "data"
    )

    if isinstance(
        data,
        list,
    ):

        for item in data:

            if not isinstance(
                item,
                dict,
            ):
                continue

            metric_name = (
                item.get(
                    "id"
                )
            )

            if (
                isinstance(
                    metric_name,
                    str,
                )
                and metric_name
            ):
                names.add(
                    metric_name
                )

    return sorted(
        names
    )



def _environment_values_from_metrics(
    client: DatadogClient,
    metric_names: list[str],
    scope_tag: str,
    scope_value: str,
    env_tag: str,
) -> list[str]:
    """Discover environment values attached to a scoped metric.

    Host inventory is not a complete source of metric tags. Serverless and
    browser metrics can carry ``service`` and ``env`` without appearing on a
    host, so complete targeted discovery from Datadog metric tag metadata.
    """

    values: set[str] = set()
    scope_filter = f"{scope_tag}:{scope_value}"

    for metric_name in metric_names:
        payload = _try_request(
            client,
            "GET",
            "/api/v2/metrics/{metric_name}/all-tags",
            endpoint=(
                "/api/v2/metrics/"
                f"{metric_name}/all-tags"
            ),
            params={
                "window[seconds]": METRIC_LOOKBACK_SECONDS,
                "filter[tags]": scope_filter,
                "filter[match]": env_tag,
                "filter[include_tag_values]": True,
            },
        )
        values.update(_tag_values_for_key(payload, env_tag))

    active_environments: list[str] = []

    for environment in values:
        scoped_metrics = _list_metrics(
            client,
            {
                "filter[tags]": (
                    f"{scope_filter} AND "
                    f"{env_tag}:{environment}"
                ),
                "window[seconds]": METRIC_LOOKBACK_SECONDS,
            },
            page_size=1,
            paginate=False,
        )

        if _metric_names(scoped_metrics):
            active_environments.append(environment)

    return sorted(active_environments)



def _metric_environment_values_for_scope(
    client: DatadogClient,
    scope_tag: str,
    scope_value: str,
    env_tag: str,
) -> list[str]:
    """Return active environments for one service from metric metadata."""

    metrics = _list_metrics(
        client,
        {
            "filter[tags]": f"{scope_tag}:{scope_value}",
            "window[seconds]": METRIC_LOOKBACK_SECONDS,
        },
    )

    return _environment_values_from_metrics(
        client,
        _metric_names(metrics),
        scope_tag,
        scope_value,
        env_tag,
    )

def _tag_values_for_key(
    payload: Any,
    key: str,
) -> set[str]:
    """Return values for one tag key from an all-tags API response."""

    attributes = _data_attributes(payload)
    tags: list[str] = []

    for field in ("indexed_tags", "ingested_tags", "tags"):
        tags.extend(_string_list(attributes.get(field)))

    prefix = f"{key}:"
    return {
        tag.removeprefix(prefix)
        for tag in tags
        if tag.startswith(prefix) and tag.removeprefix(prefix)
    }

def _metric_tag_summary(
    payload: Any,
) -> dict[str, Any]:
    """
    Normalize Datadog indexed and ingested tag keys.

    IMPORTANT:

    offending_tags MUST be list[str].

    The existing cardinality analyzer performs set
    intersection against this value.
    """

    attributes = (
        _data_attributes(
            payload
        )
    )

    indexed_tags = _string_list(
        attributes.get(
            "indexed_tags"
        )
    )

    ingested_tags = _string_list(
        attributes.get(
            "ingested_tags"
        )
    )

    all_tag_keys = sorted(
        set(
            indexed_tags
        )
        | set(
            ingested_tags
        )
    )

    return {
        # Per-tag distinct cardinality is not yet available
        # from the current source.
        "top_tag": "unknown",

        "tag_values": 0,

        # Must be strings.
        "offending_tags": (
            all_tag_keys
        ),

        # Keep empty until a genuine distinct-value
        # cardinality source is wired in.
        "tag_cardinalities": {},

        "indexed_tags": (
            indexed_tags
        ),

        "ingested_tags": (
            ingested_tags
        ),
    }


def _data_attributes(
    payload: Any,
) -> dict[str, Any]:
    """
    Safely return payload["data"]["attributes"].
    """

    if not isinstance(
        payload,
        dict,
    ):
        return {}

    data = payload.get(
        "data"
    )

    if not isinstance(
        data,
        dict,
    ):
        return {}

    attributes = data.get(
        "attributes"
    )

    if not isinstance(
        attributes,
        dict,
    ):
        return {}

    return attributes


def _string_list(
    value: Any,
) -> list[str]:
    """
    Convert a value into a clean sorted list of strings.
    """

    if not isinstance(
        value,
        list,
    ):
        return []

    return sorted(
        {
            item
            for item in value
            if (
                isinstance(
                    item,
                    str,
                )
                and item
            )
        }
    )


def _as_number(
    value: Any,
    default: int | float = 0,
) -> int | float:
    """
    Normalize an integer or float safely.
    """

    if isinstance(
        value,
        bool,
    ):
        return default

    if isinstance(
        value,
        (
            int,
            float,
        ),
    ):
        return value

    return default


def _payload_mentions_metric(
    payload: Any,
    metric_name: str,
) -> bool:
    """
    Check whether a Datadog object payload references
    a metric name.
    """

    if not payload:
        return False

    try:

        serialized = json.dumps(
            payload,
            sort_keys=True,
        )

    except (
        TypeError,
        ValueError,
    ):

        serialized = str(
            payload
        )

    return (
        metric_name
        in serialized
    )


def _extract_live_rows(
    payload: Any,
    project: str,
    env: str,
    scope_tag: str = "project",
    env_tag: str = "env",
) -> list[
    dict[str, Any]
]:
    """
    Return a minimal canonical row when optional telemetry exists.
    """

    if not payload:
        return []

    if (
        isinstance(
            payload,
            dict,
        )
        and payload
        and all(
            not value
            for value
            in payload.values()
        )
    ):
        return []

    if not _payload_contains_scope(
        payload,
        project,
        env,
        scope_tag,
        env_tag,
    ):
        return []

    row: dict[str, Any] = {
        "project": project,
        "env": env,

        "scope_tag": scope_tag,
        "scope_value": project,

        "owner": "unknown",

        "monthly_cost": 0,
    }

    row[
        scope_tag
    ] = project

    row[
        env_tag
    ] = env

    return [
        row
    ]


def _payload_contains_scope(
    payload: Any,
    scope_value: str,
    env: str,
    scope_tag: str,
    env_tag: str,
) -> bool:
    """Return whether an optional response contains the requested scope."""

    serialized = json.dumps(
        payload,
        separators=(",", ":"),
        default=str,
    )

    return (
        f"{scope_tag}:{scope_value}" in serialized
        and f"{env_tag}:{env}" in serialized
    ) or (
        f'"{scope_tag}":"{scope_value}"' in serialized
        and f'"{env_tag}":"{env}"' in serialized
    )


def _tag_values_from_host_tags(
    payload: Any,
) -> dict[
    str,
    list[str],
]:
    """
    Extract key:value host tags into a dictionary.
    """

    values: dict[
        str,
        set[str],
    ] = {}

    for tags in (
        _iter_host_tag_lists(
            payload
        )
    ):

        for tag in tags:

            if not isinstance(
                tag,
                str,
            ):
                continue

            if ":" not in tag:
                continue

            key, value = (
                tag.split(
                    ":",
                    1,
                )
            )

            key = key.strip()
            value = value.strip()

            if (
                not key
                or not value
            ):
                continue

            values.setdefault(
                key,
                set(),
            ).add(
                value
            )

    return {
        key: sorted(
            items
        )
        for key, items
        in sorted(
            values.items()
        )
    }


def _scope_envs_from_host_tags(
    payload: Any,
    scope_tag: str,
    env_tag: str = "env",
) -> tuple[
    list[str],
    dict[
        str,
        list[str],
    ],
]:
    """
    Discover scope/environment pairs from host tags.
    """

    pairs: set[
        tuple[
            str,
            str,
        ]
    ] = set()

    scope_values: set[
        str
    ] = set()

    for tags in (
        _iter_host_tag_lists(
            payload
        )
    ):

        scope_value = _tag_value(
            tags,
            scope_tag,
        )

        environment = _tag_value(
            tags,
            env_tag,
        )

        if scope_value:

            scope_values.add(
                scope_value
            )

        if (
            scope_value
            and environment
        ):

            pairs.add(
                (
                    scope_value,
                    environment,
                )
            )

    projects = sorted(
        scope_values
        | {
            scope_value
            for (
                scope_value,
                _,
            )
            in pairs
        }
    )

    envs = {
        scope_value: sorted(
            environment
            for (
                pair_scope,
                environment,
            )
            in pairs
            if (
                pair_scope
                == scope_value
            )
        )
        for scope_value
        in projects
    }

    return (
        projects,
        envs,
    )


def _iter_host_tag_lists(
    payload: Any,
):
    """
    Yield host-tag lists from Datadog response structures.
    """

    if not isinstance(
        payload,
        dict,
    ):
        return

    for host in payload.get(
        "host_tags",
        [],
    ):

        if not isinstance(
            host,
            dict,
        ):
            continue

        tags_by_source = host.get(
            "tags_by_source"
        )

        if isinstance(
            tags_by_source,
            dict,
        ):

            for tags in (
                tags_by_source.values()
            ):

                if isinstance(
                    tags,
                    list,
                ):
                    yield tags

        tags = host.get(
            "tags"
        )

        if isinstance(
            tags,
            list,
        ):
            yield tags

    tags_by_source = payload.get(
        "tags_by_source"
    )

    if isinstance(
        tags_by_source,
        dict,
    ):

        for tags in (
            tags_by_source.values()
        ):

            if isinstance(
                tags,
                list,
            ):
                yield tags


def _tag_value(
    tags: list[str],
    key: str,
) -> str | None:
    """
    Return one value from a key:value tag list.
    """

    prefix = f"{key}:"

    for tag in tags:

        if (
            isinstance(
                tag,
                str,
            )
            and tag.startswith(
                prefix
            )
        ):

            return tag.removeprefix(
                prefix
            )

    return None


def _service_envs_from_apm_services(
    payload: Any,
) -> tuple[
    list[str],
    dict[
        str,
        list[str],
    ],
]:
    """
    Discover service/environment pairs from APM service data.
    """

    services: set[
        str
    ] = set()

    pairs: set[
        tuple[
            str,
            str,
        ]
    ] = set()

    for item in (
        _iter_apm_service_items(
            payload
        )
    ):

        service = (
            _field_value(
                item,
                (
                    "service",
                    "name",
                ),
            )
            or (
                item
                if isinstance(
                    item,
                    str,
                )
                else None
            )
        )

        environment = _field_value(
            item,
            (
                "env",
                "environment",
            ),
        )

        if service:

            services.add(
                service
            )

        if (
            service
            and environment
        ):

            pairs.add(
                (
                    service,
                    environment,
                )
            )

    envs = {
        service: sorted(
            environment
            for (
                pair_service,
                environment,
            )
            in pairs
            if (
                pair_service
                == service
            )
        )
        for service
        in services
    }

    return (
        sorted(
            services
        ),
        envs,
    )


def _iter_apm_service_items(
    payload: Any,
):
    """
    Yield APM service items from supported response structures.
    """

    if isinstance(
        payload,
        list,
    ):

        yield from payload
        return

    if not isinstance(
        payload,
        dict,
    ):
        return

    data = payload.get(
        "data"
    )

    if isinstance(
        data,
        list,
    ):

        yield from data

    elif isinstance(
        data,
        dict,
    ):

        attributes = data.get(
            "attributes",
            {},
        )

        if isinstance(
            attributes,
            dict,
        ):

            services = (
                attributes.get(
                    "services"
                )
            )

            if isinstance(
                services,
                list,
            ):

                yield from services

            else:

                yield data

        else:

            yield data

    services = payload.get(
        "services"
    )

    if isinstance(
        services,
        list,
    ):

        yield from services


def _field_value(
    item: Any,
    names: tuple[
        str,
        ...,
    ],
) -> str | None:
    """
    Read a field directly or from item["attributes"].
    """

    if not isinstance(
        item,
        dict,
    ):
        return None

    sources = (
        item,
        item.get(
            "attributes",
            {},
        ),
    )

    for source in sources:

        if not isinstance(
            source,
            dict,
        ):
            continue

        for name in names:

            value = source.get(
                name
            )

            if (
                isinstance(
                    value,
                    str,
                )
                and value
            ):

                return value

    return None


def _ensure_requested_env(
    envs: dict[
        str,
        list[str],
    ],
    scope_value: str,
    env: str,
) -> dict[
    str,
    list[str],
]:
    """
    Ensure the explicitly requested environment is attached
    to the selected runtime scope.
    """

    updated = {
        key: list(values)
        for key, values
        in envs.items()
    }

    values = updated.setdefault(
        scope_value,
        [],
    )

    if env not in values:

        values.append(
            env
        )

    values.sort()

    return updated


def _try_request(
    client: DatadogClient,
    method: str,
    endpoint_template: str,
    **kwargs: Any,
) -> Any:
    """
    Run an optional Datadog request safely.

    400:
        optional query unsupported

    403:
        permission/product unavailable

    404:
        endpoint/product unavailable

    These optional failures must not prevent the main
    metric report.
    """

    try:

        return client.request(
            method,
            endpoint_template,
            **kwargs,
        )

    except RetryError:

        return {}

    except httpx.HTTPStatusError as error:

        if (
            error.response.status_code
            in {
                400,
                403,
                404,
            }
        ):

            return {}

        raise
