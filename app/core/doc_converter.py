"""Convert legacy .doc files to .docx format using LibreOffice headless."""

import subprocess
from pathlib import Path


def convert_doc_to_docx(doc_path: str) -> str:
    """Convert a .doc file to .docx using LibreOffice headless mode.

    If the file already has a .docx extension, it is returned as-is.

    Args:
        doc_path: Path to the input .doc or .docx file.

    Returns:
        Path to the .docx file (original or newly converted).

    Raises:
        FileNotFoundError: If the input file does not exist.
        RuntimeError: If the LibreOffice conversion fails or times out.
    """
    path = Path(doc_path)

    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {doc_path}")

    # Already .docx — nothing to do
    if path.suffix.lower() == ".docx":
        return str(path)

    output_dir = str(path.parent)

    try:
        result = subprocess.run(
            [
                "soffice",
                "--headless",
                "--convert-to",
                "docx",
                "--outdir",
                output_dir,
                str(path),
            ],
            timeout=60,
            capture_output=True,
            text=True,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"LibreOffice conversion timed out after 60 seconds for: {doc_path}"
        ) from exc

    if result.returncode != 0:
        raise RuntimeError(
            f"LibreOffice conversion failed (exit code {result.returncode}): "
            f"{result.stderr.strip()}"
        )

    converted_path = Path(output_dir) / (path.stem + ".docx")

    if not converted_path.exists():
        raise RuntimeError(
            f"Conversion appeared to succeed but output file not found: {converted_path}"
        )

    return str(converted_path)
