"""Versioned IRS contribution limits used by account forms and demo data."""

from dataclasses import dataclass
from datetime import date
from types import MappingProxyType
from typing import Mapping, Optional


CONTRIBUTION_LIMITS_VERSION = "2026.1"


@dataclass(frozen=True)
class ContributionLimits:
    """Annual employee contribution limits for supported account types."""

    year: int
    retirement_401k_employee: int
    hsa_individual: int
    hsa_family: int
    hsa_catch_up: int = 1000


_LIMITS_BY_YEAR = {
    2024: ContributionLimits(
        year=2024,
        retirement_401k_employee=23000,
        hsa_individual=4150,
        hsa_family=8300,
    ),
    2025: ContributionLimits(
        year=2025,
        retirement_401k_employee=23500,
        hsa_individual=4300,
        hsa_family=8550,
    ),
    2026: ContributionLimits(
        year=2026,
        retirement_401k_employee=24500,
        hsa_individual=4400,
        hsa_family=8750,
    ),
}

CONTRIBUTION_LIMITS_BY_YEAR: Mapping[int, ContributionLimits] = MappingProxyType(
    _LIMITS_BY_YEAR
)


def get_contribution_limits(year: Optional[int] = None) -> Optional[ContributionLimits]:
    """Return limits for a year, without carrying stale values into later years."""
    selected_year = date.today().year if year is None else year
    return CONTRIBUTION_LIMITS_BY_YEAR.get(selected_year)


def require_contribution_limits(year: Optional[int] = None) -> ContributionLimits:
    """Return limits for a year or fail with an actionable update message."""
    selected_year = date.today().year if year is None else year
    limits = get_contribution_limits(selected_year)
    if limits is None:
        raise ValueError(
            f"No contribution limits configured for {selected_year}. "
            "Update services/contribution_limits.py with published IRS limits."
        )
    return limits


__all__ = [
    "CONTRIBUTION_LIMITS_BY_YEAR",
    "CONTRIBUTION_LIMITS_VERSION",
    "ContributionLimits",
    "get_contribution_limits",
    "require_contribution_limits",
]
