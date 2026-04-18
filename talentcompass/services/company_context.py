"""Map company research output to Role Analysis form fields."""

SIZE_OPTIONS = ("Startup", "SME", "Mid-Market", "Enterprise")


def inferred_size_to_company_size(inferred: str) -> str:
    """Map free-text inferred_size from Claude to a fixed company size bucket."""
    if not inferred or not str(inferred).strip():
        return "SME"
    t = str(inferred).lower()
    if any(k in t for k in ("startup", "start-up", "boutique", "early-stage", "small firm")):
        return "Startup"
    if any(
        k in t
        for k in (
            "large enterprise",
            "enterprise",
            "multinational",
            "global",
            "major bank",
            "fortune",
            "big four",
            "big 4",
            "megabank",
        )
    ):
        return "Enterprise"
    if any(
        k in t
        for k in (
            "mid-market",
            "mid market",
            "mid-sized",
            "midsize",
            "mid size",
            "medium-sized",
            "regional",
        )
    ):
        return "Mid-Market"
    if any(k in t for k in ("sme", "small and medium", "small to medium")):
        return "SME"
    if "large" in t or "major" in t:
        return "Enterprise"
    if "small" in t:
        return "Startup"
    return "SME"
