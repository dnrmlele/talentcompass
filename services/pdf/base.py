"""Base PDF class, brand colours, Unicode safety, and low-level render helpers.

This module also provides the *visual* toolkit used by the section writers:
KPI tiles, horizontal meter bars, horizontal bar charts and a donut gauge.
All of them are drawn with native fpdf2 vector primitives (rect / solid_arc /
circle), so output is crisp, lightweight and byte-deterministic -- no raster
images, no external charting dependency. That keeps the golden-file PDF tests
reproducible run-to-run.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fpdf import FPDF
from fpdf.enums import XPos, YPos

# -- Brand palette --------------------------------------------------------------
DTT_GREEN = (134, 188, 37)
DTT_BLACK = (26, 26, 26)
DTT_GREY = (100, 100, 100)
DTT_HEADING = (74, 110, 30)

# Supporting tones for the visual toolkit. Categorical chart colours come from
# the official Deloitte secondary palette: greens are the brand accent; blue/teal
# carry the second data category; cool grey is the neutral. No off-brand
# amber/magenta -- Deloitte data-viz stays green + blue + grey.
DTT_TRACK = (228, 230, 224)   # empty portion of meters / bars
DTT_TILE = (247, 249, 243)    # KPI tile inner core
DTT_TRAY = (238, 241, 232)    # KPI tile outer tray (double-bezel)
DTT_LINE = (216, 219, 211)    # hairline rules
DTT_GREENBG = (240, 247, 228)  # eyebrow pill fill
DTT_DARKGREEN = (4, 106, 56)   # Deloitte Green 7 #046A38 (net / emphasis)
DTT_BLUE = (0, 118, 168)       # Deloitte Blue #0076A8 (2nd data category)
DTT_TEAL = (0, 118, 128)       # Deloitte Teal #007680
DTT_SLATE = (117, 120, 123)    # Deloitte Cool Gray 9 #75787B (neutral / human)

# Back-compat: older call sites referenced DTT_AMBER. Map it to the on-brand
# blue so any stray import keeps working without reintroducing amber.
DTT_AMBER = DTT_BLUE

# This module now lives at services/pdf/base.py, so the repo root is three
# parents up (was two from the old services/pdf_export.py). Keep these resolving
# to the SAME absolute paths as before -- the embedded fonts and logo are part of
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
        "\xa0": " ",  # non-breaking space
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
        # Register Open Sans -- the Deloitte corporate digital typeface.
        self.add_font("OpenSans", "", str(_FONT_DIR / "OpenSans-Regular.ttf"))
        self.add_font("OpenSans", "B", str(_FONT_DIR / "OpenSans-Bold.ttf"))
        self._logo = _logo_path()
        self._subtitle = subtitle
        self.set_auto_page_break(auto=True, margin=16)
        self.set_margins(16, 32, 16)

    def header(self) -> None:
        self.set_fill_color(*DTT_GREEN)
        self.rect(0, 0, self.w, 22, style="F")
        self.set_xy(14, 5)
        self.set_font("OpenSans", "B", 15)
        self.set_text_color(255, 255, 255)
        self.cell(0, 7, _safe("TALENTCOMPASS"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_x(14)
        self.set_font("OpenSans", "", 9)
        line = "AI Workforce Intelligence  -  Deloitte Luxembourg"
        if self._subtitle:
            line = f"{line}  -  {self._subtitle}"
        self.cell(0, 5, _safe(line), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        if self._logo:
            try:
                self.image(str(self._logo), x=self.w - 48, y=3, w=36)
            except Exception:
                pass
        self.set_text_color(*DTT_BLACK)
        # fpdf leaves the cursor wherever the header text ended (~y=17), which is
        # inside the green band. Drop to the top margin so body content on every
        # auto-page-break page starts cleanly below the band. (The builders set
        # their own y on page 1, so the title page is unaffected.)
        self.set_xy(self.l_margin, self.t_margin)

    def footer(self) -> None:
        self.set_y(-12)
        self.set_draw_color(*DTT_LINE)
        self.set_line_width(0.2)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(1.5)
        self.set_font("OpenSans", "", 8)
        self.set_text_color(*DTT_GREY)
        self.cell(
            0,
            4,
            _safe("Confidential  -  Deloitte Luxembourg  -  Session export"),
            align="C",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        self.cell(0, 4, _safe(f"Page {self.page_no()}"), align="C")
        self.set_text_color(*DTT_BLACK)


# -- Timestamp ------------------------------------------------------------------
def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


# -- Geometry / page-flow helpers ----------------------------------------------
def _content_w(pdf: FPDF) -> float:
    return pdf.w - pdf.l_margin - pdf.r_margin


def _need(pdf: FPDF, height: float) -> None:
    """Start a new page if *height* mm would not fit before the bottom margin."""
    if pdf.get_y() + height > pdf.page_break_trigger:
        pdf.add_page()


def _fit_font(pdf: FPDF, text: str, max_w: float, style: str, size: float,
              floor: float = 7.0) -> float:
    """Shrink a font size until *text* fits in *max_w*; return the size used."""
    s = size
    while s > floor:
        pdf.set_font("OpenSans", style, s)
        if pdf.get_string_width(text) <= max_w:
            break
        s -= 0.5
    pdf.set_font("OpenSans", style, s)
    return s


# -- Low-level text helpers -----------------------------------------------------
def _body(pdf: FPDF, text: Any, size: int = 10) -> None:
    if not text:
        return
    pdf.set_x(pdf.l_margin)
    pdf.set_font("OpenSans", "", size)
    pdf.set_text_color(*DTT_BLACK)
    pdf.multi_cell(0, 5.2, text=_safe(text), align="L")


def _section(pdf: FPDF, title: Any, size: int = 13) -> None:
    """Primary section heading with a green accent rule on the left."""
    _need(pdf, 11)
    pdf.ln(3)
    y = pdf.get_y()
    pdf.set_fill_color(*DTT_GREEN)
    pdf.rect(pdf.l_margin, y + 0.6, 1.8, size * 0.42, style="F")
    pdf.set_xy(pdf.l_margin + 4, y)
    pdf.set_font("OpenSans", "B", size)
    pdf.set_text_color(*DTT_HEADING)
    pdf.multi_cell(_content_w(pdf) - 4, 6, text=_safe(title), align="L")
    pdf.set_text_color(*DTT_BLACK)
    pdf.ln(0.5)


def _eyebrow(pdf: FPDF, text: Any) -> None:
    """A small uppercase pill badge -- the 'eyebrow' above a heading."""
    s = _safe(str(text).upper())
    _need(pdf, 9)
    pdf.set_font("OpenSans", "B", 7)
    pdf.set_char_spacing(1.2)
    tw = pdf.get_string_width(s) + 7
    x = pdf.l_margin
    y = pdf.get_y()
    pdf.set_fill_color(*DTT_GREENBG)
    pdf.rect(x, y, tw, 5.4, style="F", round_corners=True, corner_radius=2.7)
    pdf.set_xy(x, y + 0.5)
    pdf.set_text_color(*DTT_DARKGREEN)
    pdf.cell(tw, 4.4, s, align="C")
    pdf.set_char_spacing(0.0)
    pdf.set_text_color(*DTT_BLACK)
    pdf.set_y(y + 5.4 + 1.6)


def _record_title(pdf: FPDF, eyebrow: str, title: Any, size: int = 17) -> None:
    """Eyebrow badge + large record title (replaces the plain green-rule head)."""
    _need(pdf, 18)
    pdf.ln(2)
    _eyebrow(pdf, eyebrow)
    pdf.set_x(pdf.l_margin)
    pdf.set_font("OpenSans", "B", size)
    pdf.set_text_color(*DTT_BLACK)
    pdf.multi_cell(_content_w(pdf), size * 0.46, text=_safe(title), align="L")
    # thin green underline rule for weight
    y = pdf.get_y() + 1.2
    pdf.set_fill_color(*DTT_GREEN)
    pdf.rect(pdf.l_margin, y, 22, 1.1, style="F")
    pdf.set_y(y + 3.2)


def _cover(pdf: FPDF, eyebrow: str, title: str, subtitle: str,
           meta_lines: list[str]) -> None:
    """Render a premium cover page: eyebrow, oversized title, rule, meta."""
    pdf.add_page()
    pdf.set_y(78)
    _eyebrow(pdf, eyebrow)
    pdf.ln(3)
    pdf.set_x(pdf.l_margin)
    pdf.set_font("OpenSans", "B", 30)
    pdf.set_text_color(*DTT_BLACK)
    pdf.multi_cell(_content_w(pdf), 13, text=_safe(title), align="L")
    pdf.ln(2)
    pdf.set_x(pdf.l_margin)
    pdf.set_font("OpenSans", "", 13)
    pdf.set_text_color(*DTT_GREY)
    pdf.multi_cell(_content_w(pdf), 6.5, text=_safe(subtitle), align="L")
    pdf.ln(5)
    pdf.set_fill_color(*DTT_GREEN)
    pdf.rect(pdf.l_margin, pdf.get_y(), 40, 1.6, style="F")
    pdf.ln(8)
    pdf.set_x(pdf.l_margin)
    pdf.set_font("OpenSans", "", 10)
    pdf.set_text_color(80, 80, 80)
    for line in meta_lines:
        if not line:
            continue
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(_content_w(pdf), 5.6, text=_safe(line), align="L")
    pdf.set_text_color(*DTT_BLACK)


# Back-compat alias: _h was the old primary heading helper.
def _h(pdf: FPDF, title: Any, size: int = 13) -> None:
    _section(pdf, title, size)


def _subh(pdf: FPDF, title: Any) -> None:
    _need(pdf, 8)
    pdf.ln(1.5)
    pdf.set_x(pdf.l_margin)
    pdf.set_font("OpenSans", "B", 10)
    pdf.set_text_color(50, 50, 50)
    pdf.multi_cell(0, 5, text=_safe(title), align="L")
    pdf.set_text_color(*DTT_BLACK)


def _bullets(pdf: FPDF, items: list[str]) -> None:
    pdf.set_font("OpenSans", "", 9)
    pdf.set_text_color(*DTT_BLACK)
    for it in items:
        if not it:
            continue
        _need(pdf, 5)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(0, 4.8, text=_safe(f"  -  {it}"), align="L")


# -- Visual toolkit -------------------------------------------------------------
def _cat_color(label: str) -> tuple[int, int, int]:
    """Map a task / category label to a Deloitte-palette chart colour.

    Fully-automatable -> brand green; AI-augmented/human-led -> Deloitte blue;
    human-only/neutral -> Deloitte cool grey.
    """
    s = (label or "").lower()
    if "human" in s and "led" not in s:
        return DTT_SLATE
    if "augment" in s or "assist" in s or "led" in s:
        return DTT_BLUE
    # fully-automatable / automate / default
    return DTT_GREEN


def _kpi_tiles(pdf: FPDF, tiles: list[tuple[str, str]]) -> None:
    """Render a row of KPI cards. Each tile is (value, label)."""
    tiles = [t for t in tiles if t]
    if not tiles:
        return
    n = len(tiles)
    gap = 4.0
    th = 18.0
    pad = 1.4  # outer tray padding (double-bezel)
    _need(pdf, th + 3)
    w = _content_w(pdf)
    tw = (w - gap * (n - 1)) / n
    x0 = pdf.l_margin
    y = pdf.get_y()
    for i, (value, label) in enumerate(tiles):
        x = x0 + i * (tw + gap)
        # Outer tray (machined-hardware look).
        pdf.set_fill_color(*DTT_TRAY)
        pdf.rect(x, y, tw, th, style="F", round_corners=True, corner_radius=2.4)
        # Inner core.
        ix, iy = x + pad, y + pad
        iw, ih = tw - 2 * pad, th - 2 * pad
        pdf.set_fill_color(*DTT_TILE)
        pdf.rect(ix, iy, iw, ih, style="F", round_corners=True, corner_radius=1.6)
        # Green accent rule on the inner core.
        pdf.set_fill_color(*DTT_GREEN)
        pdf.rect(ix, iy + 1.4, 1.8, ih - 2.8, style="F")
        # Value (auto-shrunk to fit).
        inner = iw - 6
        _fit_font(pdf, _safe(str(value)), inner, "B", 13)
        pdf.set_text_color(*DTT_BLACK)
        pdf.set_xy(ix + 4, iy + 2.2)
        pdf.cell(inner, 7, _safe(str(value)))
        # Label.
        pdf.set_xy(ix + 4, iy + 9.4)
        pdf.set_font("OpenSans", "", 7.5)
        pdf.set_text_color(*DTT_GREY)
        pdf.multi_cell(inner, 3.3, _safe(str(label)), align="L")
    pdf.set_text_color(*DTT_BLACK)
    pdf.set_y(y + th + 3.5)


def _meter(pdf: FPDF, label: str, value: float, maxv: float = 100.0,
           suffix: str = "%", color: tuple[int, int, int] = DTT_GREEN) -> None:
    """A labelled horizontal progress bar (label left, value right, bar below)."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        v = 0.0
    _need(pdf, 11)
    w = _content_w(pdf)
    x = pdf.l_margin
    y = pdf.get_y()
    # label / value line
    pdf.set_xy(x, y)
    pdf.set_font("OpenSans", "", 9)
    pdf.set_text_color(*DTT_BLACK)
    pdf.cell(w * 0.72, 5, _safe(label))
    pdf.set_font("OpenSans", "B", 9)
    pdf.set_text_color(*color)
    val_txt = f"{v:g}{suffix}"
    pdf.cell(w * 0.28, 5, _safe(val_txt), align="R",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    # bar
    by = pdf.get_y()
    bh = 4.6
    frac = 0.0 if maxv <= 0 else max(0.0, min(1.0, v / maxv))
    pdf.set_fill_color(*DTT_TRACK)
    pdf.rect(x, by, w, bh, style="F", round_corners=True, corner_radius=1.2)
    if frac > 0:
        pdf.set_fill_color(*color)
        pdf.rect(x, by, max(1.2, w * frac), bh, style="F",
                 round_corners=True, corner_radius=1.2)
    pdf.set_text_color(*DTT_BLACK)
    pdf.set_y(by + bh + 2)


def _hbar_chart(pdf: FPDF, rows: list[tuple[str, float, tuple[int, int, int]]],
                unit: str = "", maxv: float | None = None, fmt=None) -> None:
    """Horizontal bar chart. Each row is (label, value, colour).

    Label sits above its bar (handles long labels without squeezing the plot),
    value is shown right-aligned on the label line. Pass *fmt* (a callable
    value -> str) to control the value label, e.g. EUR formatting.
    """
    rows = [r for r in rows if r]
    if not rows:
        return
    vals = [float(r[1] or 0) for r in rows]
    top = maxv if maxv is not None else max(vals + [1.0])
    if top <= 0:
        top = 1.0
    w = _content_w(pdf)
    x = pdf.l_margin
    for label, value, color in rows:
        try:
            v = float(value or 0)
        except (TypeError, ValueError):
            v = 0.0
        _need(pdf, 11)
        y = pdf.get_y()
        # label + value
        pdf.set_xy(x, y)
        _fit_font(pdf, _safe(str(label)), w * 0.78, "", 8.5)
        pdf.set_text_color(*DTT_BLACK)
        pdf.cell(w * 0.78, 4.6, _safe(str(label)))
        pdf.set_font("OpenSans", "B", 8.5)
        pdf.set_text_color(*color)
        val_txt = fmt(v) if fmt else f"{v:g}{unit}"
        pdf.cell(w * 0.22, 4.6, _safe(val_txt), align="R",
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        # bar
        by = pdf.get_y()
        bh = 3.8
        frac = max(0.0, min(1.0, v / top))
        pdf.set_fill_color(*DTT_TRACK)
        pdf.rect(x, by, w, bh, style="F", round_corners=True, corner_radius=1.0)
        if frac > 0:
            pdf.set_fill_color(*color)
            pdf.rect(x, by, max(1.0, w * frac), bh, style="F",
                     round_corners=True, corner_radius=1.0)
        pdf.set_y(by + bh + 2.4)
    pdf.set_text_color(*DTT_BLACK)


def _gauge(pdf: FPDF, score: float, label: str = "", maxv: float = 100.0,
           suffix: str = "/100", color: tuple[int, int, int] = DTT_GREEN) -> None:
    """A donut gauge (vector). Big score in the hole, caption to the right."""
    try:
        s = float(score)
    except (TypeError, ValueError):
        s = 0.0
    d = 26.0
    r = d / 2.0
    _need(pdf, d + 5)
    x = pdf.l_margin
    y = pdf.get_y()
    cx = x + r
    cy = y + r
    frac = 0.0 if maxv <= 0 else max(0.0, min(1.0, s / maxv))
    # base ring
    pdf.set_fill_color(*DTT_TRACK)
    pdf.solid_arc(cx, cy, r, 0, 360, style="F")
    # value arc, clockwise from 12 o'clock
    if frac > 0:
        pdf.set_fill_color(*color)
        sweep = 360.0 * frac
        pdf.solid_arc(cx, cy, r, -90, -90 + sweep, clockwise=False, style="F")
    # hole
    pdf.set_fill_color(255, 255, 255)
    pdf.circle(cx, cy, r * 0.64, style="F")
    # centre value
    pdf.set_xy(cx - r, cy - 4.4)
    pdf.set_font("OpenSans", "B", 13)
    pdf.set_text_color(*DTT_BLACK)
    pdf.cell(2 * r, 6, _safe(f"{s:g}"), align="C")
    pdf.set_xy(cx - r, cy + 1.8)
    pdf.set_font("OpenSans", "", 6.5)
    pdf.set_text_color(*DTT_GREY)
    pdf.cell(2 * r, 3, _safe(suffix), align="C")
    # caption to the right of the gauge
    if label:
        lx = x + d + 6
        pdf.set_xy(lx, cy - 4)
        pdf.set_font("OpenSans", "B", 11)
        pdf.set_text_color(*DTT_HEADING)
        pdf.multi_cell(pdf.w - pdf.r_margin - lx, 5, _safe(label), align="L")
    pdf.set_text_color(*DTT_BLACK)
    pdf.set_y(y + d + 3)
