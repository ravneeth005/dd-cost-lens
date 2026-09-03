"""Internal read-only browser interface for dd-cost-lens."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Form, Request, status
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .services.analysis import (
    AnalysisError,
    analyze_all_discovered_scopes,
    analyze_scope,
    discover_scopes,
)


PACKAGE_ROOT = Path(__file__).resolve().parent
app = FastAPI(title="dd-cost-lens", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=PACKAGE_ROOT / "static"), name="static")
templates = Jinja2Templates(directory=PACKAGE_ROOT / "web_templates")


@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    """Show the scope selection form with available Datadog scopes."""
    try:
        discovery = discover_scopes()
        return _index_response(
            request,
            scopes=discovery["scopes"],
            organization=discovery["organization"],
        )
    except AnalysisError as error:
        return _index_response(
            request,
            error=str(error),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


@app.post("/analyze", response_class=HTMLResponse)
def analyze(
    request: Request,
    scope_value: str = Form(..., max_length=200),
    environment: str = Form(..., max_length=100),
) -> HTMLResponse:
    """Analyze the submitted read-only Datadog scope."""
    try:
        report = analyze_scope(scope_value, environment)
    except AnalysisError as error:
        return _index_response(
            request,
            error=str(error),
            selected_scope_value=scope_value,
            selected_environment=environment,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    return templates.TemplateResponse(
        request=request,
        name="report.html",
        context={"report": report},
    )


@app.post("/analyze-all", response_class=HTMLResponse)
def analyze_all(request: Request) -> HTMLResponse:
    """Generate browser results for every scope returned by discovery."""
    try:
        batch = analyze_all_discovered_scopes()
    except AnalysisError as error:
        return _index_response(
            request,
            error=str(error),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return templates.TemplateResponse(
        request=request,
        name="batch_report.html",
        context={"batch": batch},
    )


def _index_response(
    request: Request,
    *,
    scopes: object | None = None,
    organization: object | None = None,
    error: str | None = None,
    selected_scope_value: str = "",
    selected_environment: str = "",
    status_code: int = status.HTTP_200_OK,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "scopes": scopes or {},
            "organization": organization,
            "error": error,
            "selected_scope_value": selected_scope_value,
            "selected_environment": selected_environment,
        },
        status_code=status_code,
    )
