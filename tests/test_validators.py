import pytest

from dd_cost_lens.data import load_synthetic_data
from dd_cost_lens.validators import ValidationError, validate_scope


def test_missing_project_message():
    with pytest.raises(ValidationError) as error:
        validate_scope(
            load_synthetic_data(),
            "project",
            "missing",
            "env",
            "prod",
        )

    assert "Project 'missing' not found" in str(error.value)


def test_missing_env_message():
    with pytest.raises(ValidationError) as error:
        validate_scope(
            load_synthetic_data(),
            "project",
            "checkout",
            "env",
            "qa",
        )

    assert "Environment 'qa'" in str(error.value)


def test_present_scope_passes():
    validate_scope(
        load_synthetic_data(),
        "project",
        "checkout",
        "env",
        "prod",
    )