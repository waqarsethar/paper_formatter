"""Figure formatter: applies caption prefix, numbering, and font size to figure captions."""

from __future__ import annotations

import re

from docx.shared import Pt


# Matches "Figure 1", "Fig. 2", "Fig 3", etc. at the start of a paragraph.
_FIGURE_CAPTION_RE = re.compile(
    r"^(figure|fig\.?)\s+(\d+)",
    re.IGNORECASE,
)


def _reformat_caption_text(text: str, prefix: str, number: int) -> str:
    """Replace the figure label in *text* with the configured prefix and number.

    For example ``"Fig. 1 - Overview"`` with prefix ``"Figure"`` becomes
    ``"Figure 1 - Overview"``.
    """
    new_label = f"{prefix} {number}"
    return _FIGURE_CAPTION_RE.sub(new_label, text, count=1)


def apply_figures(doc, config) -> dict:
    """Apply figure caption formatting to all recognised figure captions.

    Reads ``config["figures"]`` with keys:
        caption_position: ``"above"`` or ``"below"`` (informational)
        prefix: str (e.g. ``"Figure"`` or ``"Fig."``)
        numbering_format: ``"arabic"``
        caption_font_size: float in pt

    The formatter scans every paragraph for text that starts with a figure
    label (``Figure``, ``Fig.``, ``Fig``) followed by a number, reformats the
    label and applies the configured font size.

    Args:
        doc: A python-docx ``Document`` object.
        config: Journal configuration dict.

    Returns:
        dict with ``"warnings"`` (list[str]) and ``"stats"`` (dict).
    """
    warnings: list[str] = []
    figures_config = config.get("figures", {})

    prefix = figures_config.get("prefix", "Figure")
    caption_font_size = figures_config.get("caption_font_size", 10.0)
    size_pt = Pt(caption_font_size)

    figure_number = 0

    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        if not _FIGURE_CAPTION_RE.match(text):
            continue

        figure_number += 1

        # --- Reformat caption text ---
        new_text = _reformat_caption_text(paragraph.text, prefix, figure_number)

        if paragraph.runs:
            # Put the full reformatted text into the first run and clear the
            # rest so we don't duplicate content.
            paragraph.runs[0].text = new_text
            for run in paragraph.runs[1:]:
                run.text = ""
        else:
            paragraph.text = new_text

        # --- Apply caption font size to all runs ---
        for run in paragraph.runs:
            run.font.size = size_pt

    return {
        "warnings": warnings,
        "stats": {"figures_found": figure_number},
    }
