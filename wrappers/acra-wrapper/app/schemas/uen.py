from pydantic import BaseModel
from typing import Optional


class UENValidateRequest(BaseModel):
    uen: str


class UENValidateResponse(BaseModel):
    valid: bool
    uen: str
    entity_name: Optional[str] = None
    uen_status: Optional[str] = None
    message: str
