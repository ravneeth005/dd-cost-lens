from __future__ import annotations

import os
import re
import sys
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)


class UnsafeDatadogMethod(RuntimeError):
    """
    Raised when dd-cost-lens attempts a Datadog API request
    that is not explicitly approved in the read-only allowlist.
    """


# ============================================================
# APPROVED DATADOG API OPERATIONS
# ============================================================
#
# Keep this list explicit.
#
# Do NOT replace this with:
#
#     allow all GET requests
#
# The project is intended to remain read-only and to document
# exactly which Datadog endpoints it uses.
# ============================================================

_ALLOWED_REQUESTS: set[tuple[str, str]] = {
    # --------------------------------------------------------
    # Current authenticated user / organization
    # --------------------------------------------------------
    (
        "GET",
        "/api/v2/current_user",
    ),

    # --------------------------------------------------------
    # Organization
    # --------------------------------------------------------
    (
        "GET",
        "/api/v2/org",
    ),
    (
        "GET",
        "/api/v1/org",
    ),

    # --------------------------------------------------------
    # Host tags / host usage
    # --------------------------------------------------------
    (
        "GET",
        "/api/v1/tags/hosts",
    ),
    (
        "GET",
        "/api/v1/usage/hosts",
    ),

    # --------------------------------------------------------
    # Metrics
    # --------------------------------------------------------
    (
        "GET",
        "/api/v1/metrics",
    ),
    (
        "GET",
        "/api/v2/metrics",
    ),

    # Metric tag information
    (
        "GET",
        "/api/v2/metrics/{metric_name}/all-tags",
    ),

    # Metric indexed / ingested volume
    (
        "GET",
        "/api/v2/metrics/{metric_name}/volumes",
    ),

    # Cost Attribution. This is read-only and is available only to
    # authorised parent-level Datadog organisations.
    (
        "GET",
        "/api/v2/cost_by_tag/monthly_cost_attribution",
    ),

    # --------------------------------------------------------
    # Dashboards / monitors / notebooks
    # --------------------------------------------------------
    (
        "GET",
        "/api/v1/dashboard",
    ),
    (
        "GET",
        "/api/v1/monitor",
    ),
    (
        "GET",
        "/api/v1/notebooks",
    ),

    # --------------------------------------------------------
    # Logs
    # --------------------------------------------------------
    (
        "GET",
        "/api/v1/logs/config/indexes",
    ),

    # This POST performs a read-only analytics query.
    # It does not change Datadog configuration.
    (
        "POST",
        "/api/v2/logs/analytics/aggregate",
    ),

    # --------------------------------------------------------
    # APM
    # --------------------------------------------------------
    (
        "GET",
        "/api/v2/apm/services",
    ),
}


# ============================================================
# RETRY SETTINGS
# ============================================================

_RETRYABLE_STATUS_CODES = {
    429,
    500,
    502,
    503,
    504,
}


def _should_retry(
    exception: BaseException,
) -> bool:
    """
    Retry only temporary network / Datadog errors.

    Do not retry:
        400
        401
        403
        404
        UnsafeDatadogMethod
    """

    if isinstance(
        exception,
        UnsafeDatadogMethod,
    ):
        return False

    if isinstance(
        exception,
        (
            httpx.TimeoutException,
            httpx.NetworkError,
        ),
    ):
        return True

    if isinstance(
        exception,
        httpx.HTTPStatusError,
    ):
        return (
            exception.response.status_code
            in _RETRYABLE_STATUS_CODES
        )

    return False


# ============================================================
# DATADOG CLIENT
# ============================================================

class DatadogClient:
    """
    Small read-focused Datadog REST API client.

    Credentials are taken from:

        DD_API_KEY
        DD_APP_KEY

    unless explicitly provided to the constructor.

    Credentials are never persisted by this class.
    """

    def __init__(
        self,
        site: str | None = None,
        api_key: str | None = None,
        app_key: str | None = None,
    ) -> None:
        self.site = normalize_site(
            site
            or os.getenv("DD_SITE")
            or "datadoghq.com"
        )

        self.api_key = (
            api_key
            or os.getenv("DD_API_KEY")
        )

        self.app_key = (
            app_key
            or os.getenv("DD_APP_KEY")
        )

        self.base_url = (
            f"https://api.{self.site}"
        )

    @property
    def has_credentials(
        self,
    ) -> bool:
        """
        True when both Datadog credentials are available.
        """

        return bool(
            self.api_key
            and self.app_key
        )

    def _headers(
        self,
    ) -> dict[str, str]:
        """
        Build Datadog request headers.
        """

        headers: dict[str, str] = {
            "Accept": "application/json",
        }

        if self.api_key:
            headers[
                "DD-API-KEY"
            ] = self.api_key

        if self.app_key:
            headers[
                "DD-APPLICATION-KEY"
            ] = self.app_key

        return headers

    def _assert_allowed(
        self,
        method: str,
        endpoint_template: str,
    ) -> None:
        """
        Reject API operations that are not explicitly
        approved in _ALLOWED_REQUESTS.
        """

        normalized_method = (
            method.upper()
        )

        request_key = (
            normalized_method,
            endpoint_template,
        )

        if (
            request_key
            not in _ALLOWED_REQUESTS
        ):
            raise UnsafeDatadogMethod(
                "Refusing unsafe or undocumented "
                "Datadog call: "
                f"{normalized_method} "
                f"{endpoint_template}"
            )

    @retry(
        retry=retry_if_exception(
            _should_retry
        ),
        stop=stop_after_attempt(
            3
        ),
        wait=wait_exponential(
            multiplier=1,
            min=1,
            max=8,
        ),
    )
    def request(
        self,
        method: str,
        endpoint_template: str,
        endpoint: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """
        Perform an approved Datadog REST API request.

        endpoint_template
        -----------------
        The safe template checked against the allowlist.

        Example:

            /api/v2/metrics/{metric_name}/volumes

        endpoint
        --------
        Optional concrete path containing the runtime metric.

        Example:

            /api/v2/metrics/api.request.count/volumes

        Example call:

            client.request(
                "GET",
                "/api/v2/metrics/{metric_name}/volumes",
                endpoint=(
                    "/api/v2/metrics/"
                    "api.request.count/volumes"
                ),
            )
        """

        normalized_method = (
            method.upper()
        )

        # ----------------------------------------------------
        # Safety check
        # ----------------------------------------------------

        self._assert_allowed(
            normalized_method,
            endpoint_template,
        )

        # ----------------------------------------------------
        # Credentials
        # ----------------------------------------------------

        if not self.has_credentials:
            raise RuntimeError(
                "DD_API_KEY and DD_APP_KEY "
                "are required."
            )

        # ----------------------------------------------------
        # Concrete endpoint
        # ----------------------------------------------------

        request_endpoint = (
            endpoint
            or endpoint_template
        )

        if not request_endpoint.startswith(
            "/"
        ):
            request_endpoint = (
                "/"
                + request_endpoint
            )

        url = (
            self.base_url
            + request_endpoint
        )

        # ----------------------------------------------------
        # HTTP request
        # ----------------------------------------------------

        response = httpx.request(
            method=normalized_method,
            url=url,
            headers=self._headers(),
            timeout=30.0,
            **kwargs,
        )

        # Raises HTTPStatusError for 4xx / 5xx.
        response.raise_for_status()

        # Some Datadog endpoints can return no body.
        if not response.content:
            return {}

        return response.json()


# ============================================================
# SITE NORMALIZATION
# ============================================================

def normalize_site(
    site: str,
) -> str:
    """
    Normalize Datadog site input.

    Examples:

        us5.datadoghq.com
            ->
        us5.datadoghq.com

        https://us5.datadoghq.com
            ->
        us5.datadoghq.com

        https://api.us5.datadoghq.com
            ->
        us5.datadoghq.com

        api.us5.datadoghq.com
            ->
        us5.datadoghq.com
    """

    normalized = (
        site
        .strip()
        .lower()
    )

    markdown_link = re.fullmatch(
        r"\[[^\]]*\]\(([^)]+)\)",
        normalized,
    )

    if markdown_link:
        normalized = markdown_link.group(1)

    if normalized.startswith(
        "https://"
    ):
        normalized = normalized[
            len("https://") :
        ]

    elif normalized.startswith(
        "http://"
    ):
        normalized = normalized[
            len("http://") :
        ]

    normalized = (
        normalized
        .strip("/")
    )

    if normalized.startswith(
        "api."
    ):
        normalized = normalized[
            len("api.") :
        ]

    return normalized


# ============================================================
# OPTIONAL STDIN SECRET HELPER
# ============================================================

def _read_stdin_secret() -> str | None:
    """
    Read a secret from piped stdin.

    Nothing is written to disk.

    Returns None when stdin is interactive or empty.
    """

    if sys.stdin is None:
        return None

    if sys.stdin.isatty():
        return None

    value = (
        sys.stdin
        .readline()
        .strip()
    )

    return (
        value
        or None
    )
