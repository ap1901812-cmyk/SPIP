from typing import Any, Optional
from pydantic import BaseModel


class ErrorResponse(BaseModel):
    code: str
    message: str
    request_id: str
    details: Optional[Any] = None

