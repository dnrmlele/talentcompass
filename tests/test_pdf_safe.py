"""Tests for services.pdf_export._safe Unicode normalisation."""

from services.pdf_export import _safe


def test_dashes():
    out = _safe("a—b–c")
    assert out == "a--b-c"
    assert isinstance(out, str)


def test_curly_quotes():
    out = _safe("‘’“”")
    assert out == "''\"\""


def test_ellipsis_bullet_nbsp_middot():
    assert _safe("…") == "..."
    assert _safe("•") == "-"
    assert _safe(" ") == " "
    assert _safe("·") == "."


def test_non_bmp_and_edge_inputs():
    # A non-BMP emoji is valid UTF-8, so _safe does not raise and returns a str.
    # (_safe only strips chars that fail UTF-8 round-trip; the emoji survives.)
    out = _safe("rocket \U0001f680 end")
    assert isinstance(out, str)
    assert out  # non-empty, no exception raised
    assert _safe(None) == ""
    assert _safe(42) == "42"
