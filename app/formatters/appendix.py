"""Appendix formatter: detects and formats appendix sections with proper labeling."""

from __future__ import annotations

import re

from docx.shared import Pt

from app.core.document_parser import (
    get_all_sections,
    get_heading_level,
    strip_heading_number,
    is_reference_heading,
)


def _int_to_letter(num: int) -> str:
    """Convert an integer (1, 2, 3...) to uppercase letter (A, B, C...)."""
    if num < 1 or num > 26:
        return str(num)  # Fallback for out of range
    return chr(64 + num)  # 65 is 'A'


def _int_to_roman(num: int) -> str:
    """Convert an integer to an uppercase Roman numeral string."""
    result = []
    for value, numeral in (
        (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
        (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
        (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"),
    ):
        while num >= value:
            result.append(numeral)
            num -= value
    return "".join(result)


def _format_appendix_label(num: int, format_type: str) -> str:
    """Return appendix label formatted as letter, roman, or arabic."""
    if format_type == "letter":
        return _int_to_letter(num)
    elif format_type == "roman":
        return _int_to_roman(num)
    else:  # arabic
        return str(num)


def _detect_appendix_sections(doc) -> list[dict]:
    """Detect appendix heading paragraphs.

    Looks for:
    - Paragraphs with heading styles
    - Text starting with "appendix" (case-insensitive)
    - After references section (uses get_all_sections())

    Returns list of appendix metadata with:
        - para_idx: paragraph index
        - level: heading level
        - text: current heading text
    """
    sections = get_all_sections(doc)

    # Find the References section
    references_idx = None
    for section in sections:
        heading_text = strip_heading_number(section["heading"])
        if is_reference_heading(heading_text):
            references_idx = section["start"]
            break

    # Detect appendix sections
    appendices = []
    paragraphs = doc.paragraphs

    for idx, para in enumerate(paragraphs):
        # Skip paragraphs before References (if found)
        if references_idx is not None and idx <= references_idx:
            continue

        # Check if this is a heading paragraph
        level = get_heading_level(para)
        if level is None:
            continue

        # Check if text starts with "appendix"
        text = para.text.strip()
        stripped = strip_heading_number(text)

        if stripped.lower().startswith("appendix"):
            appendices.append({
                "para_idx": idx,
                "level": level,
                "text": text,
                "paragraph": para,
            })

    return appendices


def apply_appendix(doc, config) -> dict:
    """Format appendix sections with proper labeling.

    Reads ``config["appendix"]`` with keys:
        format: "letter" | "roman" | "arabic"
        heading_prefix: str (e.g., "Appendix" or "APPENDIX")
        numbering_format: "{prefix} {label}" or "{prefix} {label}: {title}"
        detect_subsections: bool (currently unused)
        table_numbering: "{label}{num}" (currently unused)
        figure_numbering: "{label}{num}" (currently unused)

    Args:
        doc: A python-docx ``Document`` object.
        config: Journal configuration dict.

    Returns:
        dict with ``"warnings"`` (list[str]) and ``"stats"`` (dict).
    """
    warnings: list[str] = []

    appendix_config = config.get("appendix")
    if not appendix_config:
        return {"warnings": warnings, "stats": {"appendices_found": 0}}

    # Get configuration options
    format_type = appendix_config.get("format", "letter")
    heading_prefix = appendix_config.get("heading_prefix", "Appendix")
    numbering_format = appendix_config.get("numbering_format", "{prefix} {label}")

    # Detect appendix sections
    appendices = _detect_appendix_sections(doc)

    if not appendices:
        # Appendices are optional, so don't warn
        return {"warnings": warnings, "stats": {"appendices_found": 0}}

    # Format each appendix
    for idx, appendix_info in enumerate(appendices, start=1):
        para = appendix_info["paragraph"]
        current_text = appendix_info["text"]

        # Generate label (A, B, C or I, II, III, etc.)
        label = _format_appendix_label(idx, format_type)

        # Extract title if present (text after "Appendix")
        # Match patterns like "Appendix A: Title" or "Appendix: Title" or just "Appendix"
        title_match = re.search(
            r"appendix\s*[A-Z0-9]*\s*[:.]?\s*(.*)",
            current_text,
            re.IGNORECASE
        )
        title = ""
        if title_match:
            title = title_match.group(1).strip()

        # Format new heading text
        if title and "{title}" in numbering_format:
            new_text = numbering_format.format(
                prefix=heading_prefix,
                label=label,
                title=title
            )
        else:
            # Remove {title} placeholder if present but no title
            fmt = numbering_format.replace(": {title}", "").replace(" {title}", "")
            new_text = fmt.format(
                prefix=heading_prefix,
                label=label
            )
            # Append title if we have one
            if title:
                new_text = f"{new_text}: {title}"

        # Update paragraph text
        if para.runs:
            para.runs[0].text = new_text
            for run in para.runs[1:]:
                run.text = ""
        else:
            para.text = new_text

    return {
        "warnings": warnings,
        "stats": {"appendices_found": len(appendices)}
    }
