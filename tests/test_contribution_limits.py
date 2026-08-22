"""Tests for versioned annual contribution limits and form defaults."""

from datetime import date

import pytest

from app import app
from services.contribution_limits import (
    CONTRIBUTION_LIMITS_VERSION,
    get_contribution_limits,
    require_contribution_limits,
)


@pytest.mark.parametrize(
    (
        "year",
        "retirement_401k_employee",
        "hsa_individual",
        "hsa_family",
    ),
    [
        (2024, 23000, 4150, 8300),
        (2025, 23500, 4300, 8550),
        (2026, 24500, 4400, 8750),
    ],
)
def test_contribution_limits_are_versioned_by_year(
    year,
    retirement_401k_employee,
    hsa_individual,
    hsa_family,
):
    limits = get_contribution_limits(year)

    assert limits is not None
    assert limits.year == year
    assert limits.retirement_401k_employee == retirement_401k_employee
    assert limits.hsa_individual == hsa_individual
    assert limits.hsa_family == hsa_family
    assert limits.hsa_catch_up == 1000


def test_unknown_year_does_not_reuse_stale_limits():
    assert get_contribution_limits(2099) is None

    with pytest.raises(ValueError, match="No contribution limits configured for 2099"):
        require_contribution_limits(2099)


def test_401k_form_uses_current_year_schedule():
    current_year = date.today().year
    limits = get_contribution_limits(current_year)

    response = app.test_client().get("/templates/accounts/401k_form.html")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert f'data-limit-year="{current_year}"' in html
    assert f'data-limit-version="{CONTRIBUTION_LIMITS_VERSION}"' in html
    if limits:
        assert f'value="{limits.retirement_401k_employee}"' in html
    else:
        assert 'value=""' in html
        assert f"No IRS limit is configured for {current_year}" in html


def test_hsa_form_uses_current_year_schedule():
    current_year = date.today().year
    limits = get_contribution_limits(current_year)

    response = app.test_client().get("/templates/accounts/hsa_form.html")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert f'data-limit-year="{current_year}"' in html
    assert f'data-limit-version="{CONTRIBUTION_LIMITS_VERSION}"' in html
    if limits:
        assert f'value="{limits.hsa_individual}"' in html
        assert f"${limits.hsa_family}" in html
    else:
        assert 'value=""' in html
        assert f"No IRS limit is configured for {current_year}" in html
