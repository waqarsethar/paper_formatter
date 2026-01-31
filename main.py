from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from config import settings
from app.api.routes import router

app = FastAPI(title="Manuscript Formatter")

app.mount("/static", StaticFiles(directory=Path(__file__).parent / "app" / "static"), name="static")
app.include_router(router)

# Ensure upload/output dirs exist
Path(settings.upload_dir).mkdir(exist_ok=True)
Path(settings.output_dir).mkdir(exist_ok=True)
