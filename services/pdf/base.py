"""Base PDF class, brand colours, Unicode safety, and low-level render helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fpdf import FPDF

DTT_GREEN = (134, 188, 37)
DTT_BLACK = (26, 26, 26)
DTT_GREY = (100, 100, 100)
DTT_HEADING = (74, 110, 30)

# This module now lives at services/pdf/base.py, so the repo root is three
# parents up (was two from the old services/pdf_export.py). Keep these resolving
# to the SAME absolute paths as before — the embedded fonts and logo are part of
# the PDF bytes, so any shift would change output.
_FONT_DIR = Path(__file__).resolve().parent.parent.parent / "assets" / "fonts"


def _root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _logo_path() -> Path | None:
    p = _root() / "Logo_of_Deloitte.svg.png"
    return p if p.is_file() else None


# -- Unicode safety -------------------------------------------------------------
def _safe(text: Any) -> str:
    """Normalise text to something DejaVu can always render."""
    if text is None:
        return ""
    text = str(text)
    replacements = {
        "—": "--",  # em dash
        "–": "-",  # en dash
        "‘": "'",  # left single quote
        "’": "'",  # right single quote
        "“": '"',  # left double quote
        "”": '"',  # right double quote
        "…": "...",  # ellipsis
        "•": "-",  # bullet
        " ": " ",  # non-breaking space
        "·": ".",  # middle dot
    }
    for char, repl in replacements.items():
        text = text.replace(char, repl)
    # Final fallback: drop anything outside BMP that DejaVu can't handle
    return text.encode("utf-8", errors="ignore").decode("utf-8")


# -- Base PDF class -------------------------------------------------------------
class _DeloittePDF(FPDF):
    def __init__(self, subtitle: str = ""):
        super().__init__(orientation="P", unit="mm", format="A4")
        # Register DejaVu -- full Unicode support
        self.add_font("DejaVu", "", str(_FONT_DIR / "DejaVuSans.ttf"))
        self.add_font("DejaVu", "B", str(_FONT_DIR / "DejaVuSans-Bold.ttf"))
        self._logo = _logo_path()
        self._subtitle = subtitle
        self.set_auto_page_break(auto=True, margin=14)
        self.set_margins(16, 32, 16)

    def header(self) -> None:
        self.set_fill_color(*DTT_GREEN)
        self.rect(0, 0, self.w, 22, style="F")
        self.set_xy(14, 5)
        self.set_font("DejaVu", "B", 15)
        self.set_text_color(255, 255, 255)
        self.cell(0, 7, _safe("TALENTCOMPASS"), ln=1)
        self.set_x(14)
        self.set_font("DejaVu", "", 9)
        line = "AI Workforce Intelligence  -  Deloitte Luxembourg"
        if self._subtitle:
            line = f"{line}  -  {self._subtitle}"
        self.cell(0, 5, _safe(line), ln=1)
        if self._logo:
            try:
                self.image(str(self._logo), x=self.w - 48, y=3, w=36)
            except Exception:
                pass
        self.set_text_color(*DTT_BLACK)

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("DejaVu", "", 8)
        self.set_text_color(*DTT_GREY)
        self.cell(
            0,
            4,
            _safe("Confidential  -  Deloitte Luxembourg  -  Session export"),
            align="C",
            ln=1,
        )
        self.cell(0, 4, _safe(f"Page {self.page_no()}"), align="C", ln=0)
        self.set_text_color(*DTT_BLACK)


# -- Timestamp ------------------------------------------------------------------
def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


# -- Low-level rendering helpers ------------------------------------------------
def _body(pdf: FPDF, text: Any, size: int = 10) -> None:
    if not text:
        return
    pdf.set_x(pdf.l_margin)
    pdf.set_font("DejaVu", "", size)
    pdf.set_text_color(*DTT_BLACK)
    pdf.multi_cell(0, 5.2, text=_safe(text))


def _h(pdf: FPDF, title: Any, size: int = 13) -> None:
    pdf.ln(3)
    pdf.set_x(pdf.l_margin)
    pdf.set_font("DejaVu", "B", size)
    pdf.set_text_color(*DTT_HEADING)
    pdf.multi_cell(0, 6, text=_safe(title))
    pdf.set_text_color(*DTT_BLACK)


def _subh(pdf: FPDF, title: Any) -> None:
    pdf.ln(1)
    pdf.set_x(pdf.l_margin)
    pdf.set_font("DejaVu", "B", 10)
    pdf.set_text_color(50, 50, 50)
    pdf.multi_cell(0, 5, text=_safe(title))
    pdf.set_text_color(*DTT_BLACK)


def _bullets(pdf: FPDF, items: list[str]) -> None:
    pdf.set_font("DejaVu", "", 9)
    for it in items:
        if not it:
            continue
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(0, 4.8, text=_safe(f"  -  {it}"))
