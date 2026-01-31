import asyncio
import logging
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from app.api.schemas import (
    FormatResponse,
    FormattingWarning,
    JournalInfo,
    JournalListResponse,
)
from app.core.pipeline import list_journals, load_journal_config, run_pipeline
from app.services.file_service import cleanup_files, get_output_path, save_upload

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/api/journals", response_model=JournalListResponse)
async def get_journals():
    journals = list_journals()
    return JournalListResponse(
        journals=[JournalInfo(**j) for j in journals]
    )


@router.get("/api/journals/{journal_id}")
async def get_journal_config(journal_id: str):
    try:
        config = load_journal_config(journal_id)
        return config
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Journal '{journal_id}' not found")


@router.post("/api/format", response_model=FormatResponse)
async def format_manuscript(
    file: UploadFile = File(...),
    journal_id: str = Form(...),
):
    # Validate file extension
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    ext = Path(file.filename).suffix.lower()
    if ext not in (".doc", ".docx"):
        raise HTTPException(status_code=400, detail="Only .doc and .docx files are accepted")

    # Save upload
    upload_path = await save_upload(file)
    output_path = get_output_path(file.filename)

    try:
        # Run pipeline in executor to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, run_pipeline, upload_path, journal_id, output_path
        )

        fmt_warnings = [
            FormattingWarning(step="pipeline", message=w)
            for w in result.warnings
        ]

        if not result.success:
            return FormatResponse(
                success=False,
                message=f"Formatting failed: {'; '.join(result.errors)}",
                warnings=fmt_warnings,
                stats=result.stats,
            )

        # Build download URL from output filename
        output_filename = Path(result.output_path).name
        download_url = f"/api/download/{output_filename}"

        return FormatResponse(
            success=True,
            message="Formatting complete! Download your formatted document below.",
            warnings=fmt_warnings,
            stats=result.stats,
            download_url=download_url,
        )

    except Exception as e:
        logger.error(f"Format endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cleanup_files(upload_path)


@router.get("/api/download/{filename}")
async def download_file(filename: str):
    # Prevent path traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    output_dir = Path("output")
    file_path = output_dir / filename

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
