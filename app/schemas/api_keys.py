"""API key schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ApiKeyCreateRequest(BaseModel):
    vendor: str = Field(default="openai")
    api_key: str = Field(min_length=1)


class ApiKeyResponse(BaseModel):
    id: UUID
    vendor: str
    last_four: str
    created_at: datetime
