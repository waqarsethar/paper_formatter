from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    upload_dir: str = "uploads"
    output_dir: str = "output"
    max_file_size_mb: int = 50
    journal_config_dir: str = str(Path(__file__).parent / "app" / "journal_configs")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
