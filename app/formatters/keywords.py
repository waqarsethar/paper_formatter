"""Enhanced keywords formatter: applies formatting to keywords sections."""

from __future__ import annotations

import re

from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH


ALIGNMENT_MAP = {
    "left": WD_ALIGN_PARAGRAPH.LEFT,
    "center": WD_ALIGN_PARAGRAPH.CENTER,
    "right": WD_ALIGN_PARAGRAPH.RIGHT,
}


def _apply_alignment(paragraph, alignment_name: str) -> None:
    """Set *paragraph* alignment from a string like ``"center"`` or ``"left"``."""
    alignment = ALIGNMENT_MAP.get(alignment_name.lower())
    if alignment is not None:
        paragraph.paragraph_format.alignment = alignment


def _find_keywords_paragraph(doc):
    """Return the paragraph that contains the keywords line.

    Looks for a paragraph whose text starts with "keyword" (case-insensitive).
    """
    for paragraph in doc.paragraphs:
        if paragraph.text.strip().lower().startswith("keyword"):
            return paragraph
    return None


def apply_keywords(doc, config) -> dict:
    """Enhanced keywords formatting.

    Reads ``config["keywords"]`` with keys:
        heading_text: str (e.g., "Keywords:")
        separator: str (e.g., ", " or "; ")
        italic: bool (optional, default: False)
        font_size: float (optional, default: 12)
        alignment: "left" | "center" (optional, default: "left")
        max_keywords: int (optional validation)

    Args:
        doc: A python-docx ``Document`` object.
        config: Journal configuration dict.

    Returns:
        dict with ``"warnings"`` (list[str]) and ``"stats"`` (dict).
    """
    warnings: list[str] = []

    # Handle null keywords config (Nature, PLOS ONE)
    keywords_config = config.get("keywords")
    if keywords_config is None:
        return {"warnings": [], "stats": {"keywords_count": 0}}

    keywords_para = _find_keywords_paragraph(doc)

    if keywords_para is None:
        # Keywords are optional, so don't warn if not found
        return {"warnings": warnings, "stats": {"keywords_count": 0}}

    # Get configuration options
    heading_text = keywords_config.get("heading_text", "Keywords:")
    separator = keywords_config.get("separator", ", ")
    italic = keywords_config.get("italic", False)
    font_size = keywords_config.get("font_size", 12)
    alignment = keywords_config.get("alignment", "left")
    max_keywords = keywords_config.get("max_keywords")

    text = keywords_para.text
    # Split into heading part and keywords part
    kw_match = re.match(
        r"^(keywords?\s*[:.]?\s*)(.*)",
        text,
        re.IGNORECASE,
    )

    if kw_match:
        _heading_part = kw_match.group(1)
        keywords_body = kw_match.group(2)

        # Detect the current separator by trying common options
        current_sep = None
        for candidate in ("; ", ", ", ";", ","):
            if candidate in keywords_body:
                current_sep = candidate
                break

        # Replace separator if needed
        if current_sep is not None and current_sep != separator:
            keywords_body = separator.join(
                kw.strip() for kw in keywords_body.split(current_sep)
            )

        new_text = heading_text + " " + keywords_body

        # Replace text
        if keywords_para.runs:
            keywords_para.runs[0].text = new_text
            for run in keywords_para.runs[1:]:
                run.text = ""
        else:
            keywords_para.text = new_text

        # Apply formatting
        for run in keywords_para.runs:
            run.font.size = Pt(font_size)
            run.font.italic = italic

        # Apply alignment
        _apply_alignment(keywords_para, alignment)

        # Count keywords
        keywords_list = [kw.strip() for kw in keywords_body.split(separator) if kw.strip()]
        keywords_count = len(keywords_list)

        # Validate max keywords
        if max_keywords is not None and keywords_count > max_keywords:
            warnings.append(
                f"Document contains {keywords_count} keywords, "
                f"which exceeds the maximum of {max_keywords}."
            )

        return {"warnings": warnings, "stats": {"keywords_count": keywords_count}}

    return {"warnings": warnings, "stats": {"keywords_count": 0}}
