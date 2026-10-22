import re
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, field_validator

Storage = Literal["fridge", "freezer", "room"]


def check_name(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError("이름이 비어 있다.")
    if len(stripped) > 50:
        raise ValueError("이름은 50자 이하여야 한다.")
    return stripped


def check_due_date(value: str | None) -> str | None:
    if value is None:
        return None
    # YYYY-MM-DD 만 허용. date.fromisoformat 은 다른 형식도 받으므로 길이를 같이 본다.
    if len(value) != 10:
        raise ValueError("기한은 YYYY-MM-DD 형식이어야 한다.")
    date.fromisoformat(value)
    return value


class CardIn(BaseModel):
    """초안과 같은 형태. 카드 등록 요청의 항목이다."""

    model_config = ConfigDict(extra="forbid")

    name: str
    quantity: StrictInt = Field(ge=1)
    due_date: str | None
    storage: Storage
    is_risky: StrictBool
    urgent_days: StrictInt = Field(ge=1)

    _name = field_validator("name")(check_name)
    _due_date = field_validator("due_date")(check_due_date)


class CardPatch(BaseModel):
    """카드 수정 요청. 바꿀 필드만 담는다 (D-012).

    status 는 정리(archived)와 정리 취소(remaining)에 쓰고, 수정 필드와 함께 보내지 않는다.
    """

    model_config = ConfigDict(extra="forbid")

    # 보내지 않은 필드는 건드리지 않는다. 보냈다면 CardIn 과 같은 규칙을 지켜야 한다.
    # due_date 만 null 을 보낼 수 있다 (기한 비우기).
    name: str = Field(default=None)
    quantity: StrictInt = Field(default=None, ge=1)
    due_date: str | None = None
    storage: Storage = Field(default=None)
    is_risky: StrictBool = Field(default=None)
    status: Literal["remaining", "archived"] = Field(default=None)

    _name = field_validator("name")(check_name)
    _due_date = field_validator("due_date")(check_due_date)


class CardsCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[CardIn] = Field(min_length=1)


class SignupIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    login_id: str
    password: str = Field(min_length=8, max_length=128)

    @field_validator("login_id")
    @classmethod
    def _login_id(cls, value: str) -> str:
        # 소문자로 맞춰 저장한다. 이메일 형식은 강제하지 않는다.
        v = value.strip().lower()
        if not (3 <= len(v) <= 64) or not re.fullmatch(r"[a-z0-9@._-]+", v):
            raise ValueError("아이디는 3~64자의 영문, 숫자, @ . _ - 만 쓸 수 있다.")
        return v


class LoginIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    login_id: str = Field(min_length=1)
    password: str = Field(min_length=1)

    @field_validator("login_id")
    @classmethod
    def _login_id(cls, value: str) -> str:
        return value.strip().lower()
