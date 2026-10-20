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


class CardsCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[CardIn] = Field(min_length=1)
