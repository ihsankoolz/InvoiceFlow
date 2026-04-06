from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str
    role: Literal["SELLER", "INVESTOR"]
    uen: Optional[str] = None


class RegisterResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    uen: Optional[str] = None
    account_status: str
    created_at: datetime
