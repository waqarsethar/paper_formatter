import os
import uuid

from fastapi import HTTPException, UploadFile

from config import settings

ALLOWED_EXTENSIONS = {".doc", ".docx"}


def get_upload_path(filename: str) -> str:
    """Generate a UUID-based path in the upload directory, preserving the original extension."""
    ext = os.path.splitext(filename)[1].lower()
    unique_name = f"{uuid.uuid4()}{ext}"
    return os.path.join(settings.upload_dir, unique_name)


def get_output_path(original_filename: str) -> str:
    """Generate an output path in the output directory with a '_formatted' suffix."""
    name, ext = os.path.splitext(original_filename)
    formatted_name = f"{name}_formatted{ext}"
    return os.path.join(settings.output_dir, formatted_name)


async def save_upload(file: UploadFile) -> str:
    """Save an uploaded file to the uploads directory with a UUID filename.

    Validates that the file extension is .doc or .docx.
    Returns the path to the saved file.
    Raises HTTPException(400) for invalid extensions.
    """
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file extension '{ext}'. Only .doc and .docx files are allowed.",
        )

    os.makedirs(settings.upload_dir, exist_ok=True)

    dest_path = get_upload_path(file.filename)
    content = await file.read()

    with open(dest_path, "wb") as f:
        f.write(content)

    return dest_path


def cleanup_files(*paths: str) -> None:
    """Delete files at the given paths, silently ignoring any that are missing."""
    for path in paths:
        try:
            os.remove(path)
        except OSError:
            pass
