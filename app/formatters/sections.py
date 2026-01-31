"""Section order formatter: validates document section ordering against a target order."""

from __future__ import annotations

from app.core.document_parser import get_all_sections


def apply_section_order(doc, config) -> dict:
    """Check that document sections appear in the order specified by config.

    Reads ``config["section_order"]`` — an optional list of section heading
    names such as ``["Introduction", "Methods", "Results", "Discussion",
    "Conclusion", "References"]``.

    If the key is absent or empty the formatter returns immediately.

    Because reliably reordering sections in python-docx risks document
    corruption, this formatter only **reports** mismatches rather than
    performing automatic reordering.

    Args:
        doc: A python-docx ``Document`` object.
        config: Journal configuration dict.

    Returns:
        dict with ``"warnings"`` (list[str]) and ``"stats"`` (dict).
    """
    warnings: list[str] = []

    target_order: list[str] | None = config.get("section_order")
    if not target_order:
        return {"warnings": warnings, "stats": {}}

    sections = get_all_sections(doc)

    if not sections:
        warnings.append(
            "No headed sections found in the document; "
            "cannot verify section order."
        )
        return {"warnings": warnings, "stats": {}}

    # Build a normalised lookup: lowercase target name -> original name.
    target_lower = [name.lower() for name in target_order]

    # Extract the current section headings that match any target name.
    current_headings: list[str] = []
    for section in sections:
        heading_lower = section["heading"].strip().lower()
        if heading_lower in target_lower:
            current_headings.append(section["heading"].strip())

    if not current_headings:
        warnings.append(
            "None of the expected section headings were found in the "
            f"document. Expected: {', '.join(target_order)}."
        )
        return {"warnings": warnings, "stats": {}}

    # Compare ordering of the matched sections against the target.
    current_lower = [h.lower() for h in current_headings]
    # Filter target to only those present in the document.
    expected_lower = [t for t in target_lower if t in current_lower]

    if current_lower == expected_lower:
        return {"warnings": warnings, "stats": {}}

    # Build human-readable names using the original casing from config.
    target_name_map = {name.lower(): name for name in target_order}
    expected_display = [target_name_map[t] for t in expected_lower]
    current_display = current_headings

    warnings.append(
        f"Section order mismatch: expected [{', '.join(expected_display)}], "
        f"found [{', '.join(current_display)}]. "
        "Automatic reordering is not supported; please reorder sections manually."
    )

    return {"warnings": warnings, "stats": {}}
