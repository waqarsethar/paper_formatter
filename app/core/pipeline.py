import json
import logging
from pathlib import Path
from docx import Document

from config import settings
from app.api.schemas import FormattingResult, FormattingStats
from app.core.doc_converter import convert_doc_to_docx
from app.formatters.layout import apply_layout
from app.formatters.fonts import apply_fonts
from app.formatters.headings import apply_headings
from app.formatters.title_page import apply_title_page
from app.formatters.sections import apply_section_order
from app.formatters.citations import apply_citations
from app.formatters.references import apply_references
from app.formatters.tables import apply_tables
from app.formatters.figures import apply_figures

logger = logging.getLogger(__name__)

def load_journal_config(journal_id: str) -> dict:
    config_path = Path(settings.journal_config_dir) / f"{journal_id}.json"
    if not config_path.exists():
        raise FileNotFoundError(f"Journal config not found: {journal_id}")
    with open(config_path, "r") as f:
        return json.load(f)

def list_journals() -> list[dict]:
    config_dir = Path(settings.journal_config_dir)
    journals = []
    for config_file in sorted(config_dir.glob("*.json")):
        with open(config_file, "r") as f:
            config = json.load(f)
        journals.append({
            "id": config_file.stem,
            "name": config.get("name", config_file.stem),
            "description": config.get("description", "")
        })
    return journals

def run_pipeline(input_path: str, journal_id: str, output_path: str) -> FormattingResult:
    warnings = []
    errors = []
    stats = FormattingStats(
        citations_found=0, citations_reformatted=0,
        references_found=0, references_reformatted=0,
        tables_found=0, figures_found=0
    )

    try:
        # Convert .doc if needed
        docx_path = convert_doc_to_docx(input_path)

        # Load config
        config = load_journal_config(journal_id)

        # Load document
        doc = Document(docx_path)

        # Run each formatter step, catching per-step errors.
        # Order matters: content-detecting steps (title_page, sections,
        # citations, references) must run BEFORE headings numbering,
        # because numbering prepends prefixes like "1. " that break
        # heading-text matching.
        steps = [
            ("layout", lambda: apply_layout(doc, config)),
            ("fonts", lambda: apply_fonts(doc, config)),
            ("title_page", lambda: apply_title_page(doc, config)),
            ("sections", lambda: apply_section_order(doc, config)),
            ("citations", lambda: apply_citations(doc, config)),
            ("references", lambda: apply_references(doc, config)),
            ("headings", lambda: apply_headings(doc, config)),
            ("tables", lambda: apply_tables(doc, config)),
            ("figures", lambda: apply_figures(doc, config)),
        ]

        for step_name, step_fn in steps:
            try:
                result = step_fn()
                if result:  # formatters return dict with warnings/stats
                    warnings.extend(result.get("warnings", []))
                    # Merge stats
                    for key in stats.model_fields:
                        if key in result.get("stats", {}):
                            setattr(stats, key, getattr(stats, key) + result["stats"][key])
            except Exception as e:
                logger.warning(f"Step '{step_name}' failed: {e}")
                warnings.append(f"Step '{step_name}' partially failed: {str(e)}")

        # Save output
        doc.save(output_path)

        return FormattingResult(
            success=True, warnings=warnings, errors=errors,
            stats=stats, output_path=output_path
        )
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        return FormattingResult(
            success=False, warnings=warnings,
            errors=[str(e)], stats=stats, output_path=None
        )
