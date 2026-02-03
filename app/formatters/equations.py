"""Equation formatter: applies numbering, alignment, and spacing to equations."""

from __future__ import annotations

import re

from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH


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


def _format_number(n: int, numbering_format: str) -> str:
    """Return *n* formatted as arabic or roman."""
    if numbering_format == "roman":
        return _int_to_roman(n)
    return str(n)


# Matches standalone equation numbers: "(1)", "(2.1)", "Eq. (1)", etc.
_EQUATION_NUMBER_RE = re.compile(
    r'^\s*(?:(?:Eq\.|Equation)\s*)?\((\d+(?:\.\d+)?)\)\s*$',
    re.IGNORECASE,
)


def _has_omath_element(paragraph) -> bool:
    """Check if paragraph contains Office Math XML (equation object).

    Office Math elements are identified by tags ending with 'oMath' or 'oMathPara'.
    These represent actual equation objects embedded in Word documents.
    """
    for element in paragraph._element.iter():
        tag = element.tag
        if tag.endswith('}oMath') or tag.endswith('}oMathPara'):
            return True
    return False


def _detect_equation_paragraphs(doc) -> list[dict]:
    """Return list of equation paragraphs with metadata.

    Detects equations in two modes:
    1. Office Math XML elements (actual equation objects)
    2. Text-based equation numbers (standalone paragraphs with numbers like "(1)")

    Returns:
        List of dicts with keys:
            - para: paragraph object
            - para_idx: index in document
            - type: "omath" or "numbered_text"
            - current_number: extracted number (if applicable)
    """
    equations = []

    for idx, para in enumerate(doc.paragraphs):
        # Skip heading paragraphs
        if para.style.name and para.style.name.startswith("Heading"):
            continue

        # Mode 1: Office Math elements
        if _has_omath_element(para):
            equations.append({
                "para": para,
                "para_idx": idx,
                "type": "omath",
                "current_number": None
            })
            continue

        # Mode 2: Text-based equation numbers
        text = para.text.strip()
        match = _EQUATION_NUMBER_RE.match(text)
        if match:
            # Only consider if paragraph is relatively isolated
            # (likely a standalone equation number)
            equations.append({
                "para": para,
                "para_idx": idx,
                "type": "numbered_text",
                "current_number": match.group(1)
            })

    return equations


def _format_equation_number(num: int, config: dict) -> str:
    """Format equation number according to config.

    Args:
        num: Sequential equation number (1, 2, 3, ...)
        config: Equation configuration dict with keys:
            - numbering_format: "arabic" or "roman"
            - prefix: "" or "Eq." or "Equation"
            - number_format_template: "({num})" or "[{num}]" etc.

    Returns:
        Formatted equation number string, e.g. "(1)", "Eq. (I)", "[2]"
    """
    numbering_format = config.get("numbering_format", "arabic")
    prefix = config.get("prefix", "")
    template = config.get("number_format_template", "({num})")

    formatted_num = _format_number(num, numbering_format)

    # Apply template
    result = template.replace("{num}", formatted_num)

    # Add prefix if present
    if prefix:
        result = f"{prefix} {result}"

    return result


def _apply_equation_alignment(paragraph, alignment: str) -> None:
    """Apply alignment to equation paragraph.

    Args:
        paragraph: docx paragraph object
        alignment: "center", "left", or "right"
    """
    alignment_map = {
        "center": WD_ALIGN_PARAGRAPH.CENTER,
        "left": WD_ALIGN_PARAGRAPH.LEFT,
        "right": WD_ALIGN_PARAGRAPH.RIGHT,
    }

    if alignment in alignment_map:
        paragraph.alignment = alignment_map[alignment]


def _apply_equation_spacing(paragraph, spacing_before: int, spacing_after: int) -> None:
    """Apply spacing before and after equation paragraph.

    Args:
        paragraph: docx paragraph object
        spacing_before: points before paragraph
        spacing_after: points after paragraph
    """
    if spacing_before is not None:
        paragraph.paragraph_format.space_before = Pt(spacing_before)

    if spacing_after is not None:
        paragraph.paragraph_format.space_after = Pt(spacing_after)


def _apply_equation_font_size(paragraph, font_size: float) -> None:
    """Apply font size to all runs in equation paragraph.

    Args:
        paragraph: docx paragraph object
        font_size: font size in points (or None to skip)
    """
    if font_size is None:
        return

    size_pt = Pt(font_size)
    for run in paragraph.runs:
        run.font.size = size_pt


def _update_equation_number_text(paragraph, new_number: str, warnings: list[str]) -> None:
    """Update the text of an equation number paragraph.

    Args:
        paragraph: docx paragraph object containing equation number
        new_number: formatted equation number to replace
        warnings: list to append warnings to
    """
    try:
        if paragraph.runs:
            # Put the new number in the first run and clear the rest
            paragraph.runs[0].text = new_number
            for run in paragraph.runs[1:]:
                run.text = ""
        else:
            paragraph.text = new_number
    except Exception as e:
        warnings.append(f"Could not update equation number text: {str(e)}")


def apply_equations(doc, config) -> dict:
    """Apply equation formatting to all equations in *doc*.

    Reads ``config["equations"]`` with keys:
        numbering: "sequential" or "none"
        numbering_format: "arabic" or "roman"
        prefix: "" or "Eq." or "Equation"
        number_format_template: "({num})" or "[{num}]" etc.
        alignment: "center", "left", or "right"
        spacing_before: int (points)
        spacing_after: int (points)
        font_size: float or null (points)

    The formatter detects equations via:
    1. Office Math XML elements (actual equation objects)
    2. Text-based equation numbers (standalone paragraphs like "(1)")

    Args:
        doc: A python-docx ``Document`` object.
        config: Journal configuration dict.

    Returns:
        dict with ``"warnings"`` (list[str]) and ``"stats"`` (dict).
    """
    warnings: list[str] = []
    equations_config = config.get("equations", {})

    # Read configuration
    numbering = equations_config.get("numbering", "sequential")
    alignment = equations_config.get("alignment", "center")
    spacing_before = equations_config.get("spacing_before", 6)
    spacing_after = equations_config.get("spacing_after", 6)
    font_size = equations_config.get("font_size", None)

    # Detect all equations
    equations = _detect_equation_paragraphs(doc)

    if not equations:
        warnings.append("No equations found in document")
        return {
            "warnings": warnings,
            "stats": {"equations_found": 0},
        }

    # Process each equation
    equation_number = 0

    for eq_data in equations:
        para = eq_data["para"]
        eq_type = eq_data["type"]

        try:
            # Apply alignment
            _apply_equation_alignment(para, alignment)

            # Apply spacing
            _apply_equation_spacing(para, spacing_before, spacing_after)

            # Apply font size if specified
            if font_size is not None:
                _apply_equation_font_size(para, font_size)

            # Handle numbering for text-based equation numbers
            if eq_type == "numbered_text" and numbering == "sequential":
                equation_number += 1
                new_number = _format_equation_number(equation_number, equations_config)
                _update_equation_number_text(para, new_number, warnings)
            elif eq_type == "omath":
                # For Office Math elements, we don't modify the equation itself,
                # just apply formatting (alignment, spacing, font size)
                # Count as equation for stats
                equation_number += 1

        except Exception as e:
            warnings.append(
                f"Could not apply formatting to equation at paragraph {eq_data['para_idx']}: {str(e)}"
            )

    return {
        "warnings": warnings,
        "stats": {"equations_found": len(equations)},
    }
