"""User request/response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class UserRole(str):
    ADMIN = "ADMIN"
    USER = "USER"


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=128)
    email: EmailStr
    password: str | None = Field(default=None, min_length=1, max_length=128)
    role: str = Field(default="USER", max_length=32)
    allow_access: bool = True
    is_active: bool = True

    @field_validator("username")
    @classmethod
    def _normalize_username(cls, value: str) -> str:
        name = value.strip()
        if not name:
            raise ValueError("Username is required")
        return name

    @field_validator("password")
    @classmethod
    def _validate_password(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(ch.isupper() for ch in value):
            raise ValueError("Password must contain at least one uppercase character")
        if not any(ch.isdigit() for ch in value):
            raise ValueError("Password must contain at least one number")
        return value

    @field_validator("role")
    @classmethod
    def _clean_role(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in {"ADMIN", "USER"}:
            raise ValueError("Role must be ADMIN or USER")
        return normalized


class UserUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=128)
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)
    role: str | None = Field(default=None, max_length=32)
    allow_access: bool | None = None
    is_active: bool | None = None

    @field_validator("username")
    @classmethod
    def _normalize_username(cls, value: str | None) -> str | None:
        if value is None:
            return None
        name = value.strip()
        if not name:
            raise ValueError("Username is required")
        return name

    @field_validator("password")
    @classmethod
    def _validate_password(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(ch.isupper() for ch in value):
            raise ValueError("Password must contain at least one uppercase character")
        if not any(ch.isdigit() for ch in value):
            raise ValueError("Password must contain at least one number")
        return value

    @field_validator("role")
    @classmethod
    def _clean_role(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        if normalized not in {"ADMIN", "USER"}:
            raise ValueError("Role must be ADMIN or USER")
        return normalized


class UserLogin(BaseModel):
    username: str
    password: str


class UserRegistration(BaseModel):
    username: str = Field(..., min_length=3, max_length=128)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("username")
    @classmethod
    def _normalize_username(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Username is required")
        return value

    @field_validator("password")
    @classmethod
    def _validate_password(cls, value: str) -> str:
        if not any(ch.isupper() for ch in value) or not any(ch.isdigit() for ch in value):
            raise ValueError("Password must contain at least one uppercase character and one number")
        return value


class VerifyRegistrationRequest(BaseModel):
    username: str = Field(..., min_length=1)
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)

    @field_validator("otp", mode="before")
    @classmethod
    def _validate_otp(cls, value: object) -> str:
        if not isinstance(value, str) or len(value) != 6 or not value.isdigit():
            raise ValueError("OTP must be exactly 6 digits")
        return value


class EmailOtpRequest(BaseModel):
    email: EmailStr


class ResetPasswordVerifyRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)

    @field_validator("otp", mode="before")
    @classmethod
    def _validate_otp(cls, value: object) -> str:
        if not isinstance(value, str) or len(value) != 6 or not value.isdigit():
            raise ValueError("OTP must be exactly 6 digits")
        return value


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str = Field(..., min_length=1)

    @model_validator(mode="after")
    def _matching_passwords(self) -> "ResetPasswordRequest":
        if self.new_password != self.confirm_password:
            raise ValueError("New password and confirmation must match")
        if not any(ch.isupper() for ch in self.new_password) or not any(ch.isdigit() for ch in self.new_password):
            raise ValueError("Password must contain at least one uppercase character and one number")
        return self


class PasswordChange(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str = Field(..., min_length=1)

    @model_validator(mode="after")
    def _matching_passwords(self) -> "PasswordChange":
        if self.new_password != self.confirm_password:
            raise ValueError("New password and confirmation must match")
        if not any(ch.isupper() for ch in self.new_password) or not any(ch.isdigit() for ch in self.new_password):
            raise ValueError("Password must contain at least one uppercase character and one number")
        return self


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    role: str
    allow_access: bool
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AuthToken(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserRead


class UserList(BaseModel):
    items: list[UserRead]
    total: int
