"""Tests for services.company_context.inferred_size_to_company_size buckets."""

import pytest

from services.company_context import inferred_size_to_company_size


@pytest.mark.parametrize(
    "text,expected",
    [
        ("early-stage startup", "Startup"),
        ("small boutique", "Startup"),
        # NB: "enterprise" is matched before the SME branch, so the SME bucket is
        # reached via "sme" / "small to medium" wording rather than "...enterprise".
        ("an SME with steady growth", "SME"),
        ("a small to medium firm", "SME"),
        ("mid-sized regional firm", "Mid-Market"),
        ("large multinational bank", "Enterprise"),
        ("major", "Enterprise"),
    ],
)
def test_buckets(text, expected):
    assert inferred_size_to_company_size(text) == expected


@pytest.mark.parametrize("text", ["", "   ", None, "xyz"])
def test_fallback_to_sme(text):
    assert inferred_size_to_company_size(text) == "SME"
