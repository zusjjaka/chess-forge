import uuid
from typing import Literal

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
)


class EmailVerificationData(BaseModel):
    code: str = Field(min_length=6, max_length=6, pattern=r'^\d{6}$')


EmailMessageType = Literal[
    'email.verification',
    'email.change',
    'email.password_reset',
]


class EmailMessage(BaseModel):
    type: EmailMessageType
    to: EmailStr
    data: dict[str, str]
    message_id: uuid.UUID
    version: int = 1
