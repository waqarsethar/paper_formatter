from __future__ import annotations

from pydantic import BaseModel, EmailStr


class JournalInfo(BaseModel):
    id: str
    name: str
    description: str


class JournalListResponse(BaseModel):
    journals: list[JournalInfo]


class FormatRequest(BaseModel):
    journal_id: str
    email: EmailStr


class FormattingWarning(BaseModel):
    step: str
    message: str


class FormattingStats(BaseModel):
    citations_found: int
    citations_reformatted: int
    references_found: int
    references_reformatted: int
    tables_found: int
    figures_found: int


class FormatResponse(BaseModel):
    success: bool
    message: str
    warnings: list[FormattingWarning] = []
    stats: FormattingStats | None = None


class FormattingResult(BaseModel):
    success: bool
    warnings: list[str]
    errors: list[str]
    stats: FormattingStats
    output_path: str | None
