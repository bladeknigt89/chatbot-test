from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=8, max_length=200)


class UserOut(ORMModel):
    id: str
    username: str
    created_at: datetime


class AgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    system_prompt: str = ""
    status: Literal["active", "inactive"] = "active"
    show_sources: bool = True
    widget_primary_color: str = "#2563eb"
    widget_title: str = ""
    widget_position: Literal["right", "left"] = "right"
    widget_welcome_message: str = "Üdvözlöm! Miben segíthetek a dokumentumok alapján?"


class AgentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    system_prompt: str | None = None
    status: Literal["active", "inactive"] | None = None
    show_sources: bool | None = None
    widget_primary_color: str | None = None
    widget_title: str | None = None
    widget_position: Literal["right", "left"] | None = None
    widget_welcome_message: str | None = None


class AgentOut(ORMModel):
    id: str
    name: str
    description: str
    system_prompt: str
    status: str
    show_sources: bool = True
    widget_primary_color: str
    widget_title: str
    widget_position: str
    widget_welcome_message: str
    created_at: datetime
    updated_at: datetime
    document_count: int = 0


class DocumentOut(ORMModel):
    id: str
    agent_id: str
    original_filename: str
    mime_type: str
    file_size: int
    status: str
    processing_stage: str
    progress_percent: int = 0
    error_message: str | None
    chunk_count: int
    created_at: datetime
    updated_at: datetime


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class ApiKeyOut(ORMModel):
    id: str
    name: str
    key_prefix: str
    status: str
    created_by: str
    last_used_at: datetime | None
    created_at: datetime
    revoked_at: datetime | None


class ApiKeyCreated(ApiKeyOut):
    key: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    session_id: str | None = None
    stream: bool = True
    include_sources: bool = True


class ChatSource(BaseModel):
    document_id: str
    document_name: str
    chunk_index: int
    page_number: int | None = None
    sheet_name: str | None = None
    score: float | None = None


class ChatResponse(BaseModel):
    session_id: str
    message: str
    sources: list[ChatSource] = []


class AuditLogOut(ORMModel):
    id: str
    timestamp: datetime
    user: str
    action: str
    resource_type: str
    resource_id: str
    details: str
    ip: str | None


class DashboardOut(BaseModel):
    agent_count: int
    document_count: int
    processing_document_count: int
    api_key_count: int
    chat_requests_today: int
    errors_today: int


class SettingsOut(BaseModel):
    chat_history_enabled: bool
    chunk_size: int
    chunk_overlap: int
    top_k: int
    max_file_size: int
    llm_provider: str
    llm_model: str
    embedding_provider: str
    embedding_model: str
    ocr_enabled: bool
    ocr_dpi: int
    ocr_languages: str


class SettingsUpdate(BaseModel):
    chat_history_enabled: bool | None = None


class WidgetConfigOut(BaseModel):
    agent_id: str
    agent_name: str
    status: str
    primary_color: str
    title: str
    position: str
    welcome_message: str
    show_sources: bool = True


class ErrorOut(BaseModel):
    detail: str
