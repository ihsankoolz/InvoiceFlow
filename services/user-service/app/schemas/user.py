from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str
    role: Literal["SELLER", "INVESTOR"]
    uen: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    uen: Optional[str]
    account_status: str
    created_at: datetime

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class StatusUpdate(BaseModel):
    account_status: Literal["ACTIVE", "DEFAULTED"]
