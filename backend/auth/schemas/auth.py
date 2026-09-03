import uuid
from datetime import datetime
from typing import Self

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    model_validator,
)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    password_repeat: str = Field(min_length=8, max_length=128)

    @model_validator(mode='after')
    def password_match(self) -> Self:
        if self.password != self.password_repeat:
            raise ValueError('Passwords do not match')

        return self


class RegisterResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    status: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'
    expires_in: int


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    email: EmailStr
    display_name: str | None
    created_at: datetime


class EmailApprovalRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6, pattern=r'^\d{6}$')


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    email: EmailStr
    code: str = Field(
        min_length=6,
        max_length=6,
        pattern=r'^\d{6}$',
    )
    password: str = Field(min_length=8, max_length=128)
    password_repeat: str = Field(min_length=8, max_length=128)

    @model_validator(mode='after')
    def password_match(self) -> Self:
        if self.password != self.password_repeat:
            raise ValueError('Passwords do not match')

        return self
