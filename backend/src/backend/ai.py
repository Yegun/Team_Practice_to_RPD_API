import os
from datetime import date, timedelta
from typing import Protocol


class Analyzer(Protocol):
    """영수증 사진에서 식품 초안을 뽑는다. 실제 AI 서비스는 이 인터페이스 뒤에 붙인다 (D-020)."""

    def analyze(self, image: bytes) -> list[dict]: ...


def _in_days(n: int) -> str:
    return (date.today() + timedelta(days=n)).isoformat()


class MockAnalyzer:
    """고정 응답을 돌려주는 가짜 AI. 사진 내용은 읽지 않는다.

    MOCK_AI_MODE: ok(기본) | empty(식품 없음) | error(AI 호출 실패)
    """

    def analyze(self, image: bytes) -> list[dict]:
        mode = os.environ.get("MOCK_AI_MODE", "ok")
        if mode == "error":
            raise RuntimeError("mock AI failure")
        if mode == "empty":
            return []
        return [
            {"name": "우유", "quantity": 1, "due_date": _in_days(5), "storage": "fridge",
             "is_risky": False, "urgent_days": 2},
            {"name": "삼겹살", "quantity": 1, "due_date": _in_days(2), "storage": "fridge",
             "is_risky": True, "urgent_days": 1},
            {"name": "두부", "quantity": 2, "due_date": _in_days(4), "storage": "fridge",
             "is_risky": False, "urgent_days": 2},
            {"name": "냉동만두", "quantity": 1, "due_date": _in_days(180), "storage": "freezer",
             "is_risky": False, "urgent_days": 14},
            {"name": "양파", "quantity": 3, "due_date": None, "storage": "room",
             "is_risky": False, "urgent_days": 7},
        ]


def get_analyzer() -> Analyzer:
    return MockAnalyzer()
