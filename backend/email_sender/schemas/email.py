import uuid
from typing import Literal

from pydantic import BaseModel

EmailMessageType = Literal[
    'email.verification',
    'email.change',
    'email.password_reset',
]


class EmailMessage(BaseModel):
    type: EmailMessageType
    to: str
    data: dict[str, str]
    message_id: uuid.UUID
    version: int = 1
