import datetime as dt
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str = Field(min_length=1, max_length=100)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        has_letter = any(ch.isalpha() and ch.isascii() for ch in value)
        has_digit = any(ch.isdigit() for ch in value)
        if not has_letter or not has_digit:
            raise ValueError("Пароль должен содержать латинские буквы и цифры")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class MessageResponse(BaseModel):
    message: str


class TokenResponse(BaseModel):
    token: str


class FamilyCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class FamilyResponse(BaseModel):
    id: int
    name: str
    invite_code: str
    owner_id: int


class FamilyJoinRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6)


class FamilyJoinResponse(BaseModel):
    message: str
    family_id: int
    family_name: str


class InviteCodeResponse(BaseModel):
    invite_code: str


class FamilyMemberResponse(BaseModel):
    user_id: int
    user_name: str
    user_email: str
    role: str
    can_manage_accounts: bool = False
    can_delete_any_transactions: bool = False


class FamilyPermissionUpdateRequest(BaseModel):
    user_id: int
    can_manage_accounts: bool = False
    can_delete_any_transactions: bool = False


class AccountCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class AccountResponse(BaseModel):
    id: int
    name: str
    is_default: bool


class TransactionCreateRequest(BaseModel):
    family_id: int
    type: Literal["income", "expense"]
    amount: float = Field(gt=0)
    category: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    account_type: str = Field(default="main", min_length=1, max_length=100)
    recurring_monthly: bool = False
    recurring_day: int = Field(default=1, ge=1, le=28)


class TransactionResponse(BaseModel):
    id: int
    type: str
    amount: float
    category: str
    description: str | None
    account_type: str
    date: dt.date
    user_name: str
    is_recurring_generated: bool


class RecurringPaymentResponse(BaseModel):
    id: int
    amount: float
    category: str
    description: str | None
    account_type: str
    day_of_month: int
    active: bool


class RecurringPaymentUpdateRequest(BaseModel):
    amount: float = Field(gt=0)
    category: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    account_type: Literal["main", "savings"] = "main"
    day_of_month: int = Field(ge=1, le=28)


class SavingsGoalRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    target_amount: float = Field(gt=0)
    deadline_year: int = Field(ge=2000, le=3000)
    deadline_month: int = Field(ge=1, le=12)
    account_type: Literal["main", "savings"] = "main"


class SavingsGoalResponse(BaseModel):
    title: str
    target_amount: float
    deadline_year: int
    deadline_month: int
    account_type: str
    current_balance: float
    progress_percent: int
    remaining_amount: float
    achieved: bool


class AuditLogResponse(BaseModel):
    id: int
    actor_name: str
    action: str
    details: str
    created_at: dt.datetime


class ReportResponse(BaseModel):
    total_income: float
    total_expense: float
    balance: float
    by_category: dict[str, float]
    by_user: dict[str, float]


class CurrentUserResponse(BaseModel):
    id: int
    email: str
    name: str


class MembershipFamilyResponse(BaseModel):
    user_id: int
    family_id: int
    family_name: str
    role: str
