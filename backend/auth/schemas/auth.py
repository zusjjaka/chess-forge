import uuid
from datetime import (
    date,
    datetime,
)
from typing import Self

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from core.constants import (
    MAXIMUM_USER_AGE,
    MINIMUM_USER_AGE,
)
from models.user import Gender


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
    gender: Gender | None
    country: str | None
    birth_date: date | None
    bio: str | None
    telegram_alias: str | None
    created_at: datetime


class UserUpdateRequest(BaseModel):
    display_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=25,
    )
    gender: Gender | None = None
    country: str | None = Field(
        default=None,
        min_length=2,
        max_length=2,
        pattern=r'^[A-Z]{2}$',
    )
    birth_date: date | None = None
    bio: str | None = Field(
        default=None,
        min_length=1,
        max_length=75,
    )
    telegram_alias: str | None = Field(
        default=None,
        min_length=5,
        max_length=32,
        pattern=r'^[A-Za-z][A-Za-z0-9_]*$',
    )

    @field_validator('birth_date')
    @classmethod
    def validate_birth_date(cls, birthday: date | None) -> date | None:
        if birthday is None:
            return None

        age = date.today() - birthday

        if not MINIMUM_USER_AGE <= age <= MAXIMUM_USER_AGE:
            raise ValueError(f'Age must be between {MINIMUM_USER_AGE.days // 365} '
                             'and {MAXIMUM_USER_AGE.days // 365} years')

        return birthday


class UserUpdateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    email: EmailStr
    display_name: str | None
    gender: Gender | None
    country: str | None
    birth_date: date | None
    bio: str | None
    telegram_alias: str | None


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


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)
    new_password_repeat: str = Field(min_length=8, max_length=128)

    @model_validator(mode='after')
    def password_match(self) -> Self:
        if self.new_password != self.new_password_repeat:
            raise ValueError('Passwords do not match')

        return self


class EmailChangeRequest(BaseModel):
    new_email: EmailStr
    password: str = Field(
        min_length=8,
        max_length=128,
    )


class EmailChangeConfirm(BaseModel):
    code: str = Field(
        min_length=6,
        max_length=6,
        pattern=r'^\d{6}$',
    )
