from fastapi import APIRouter, Depends, File, UploadFile

from backend.ai import Analyzer, get_analyzer
from backend.deps import owner_id
from backend.errors import ApiError
from backend.schemas import CardIn

router = APIRouter(prefix="/api/receipts")

MAX_BYTES = 10 * 1024 * 1024


def _is_allowed_image(data: bytes) -> bool:
    """확장자나 Content-Type 이 아니라 파일 앞부분으로 jpeg, png, webp 를 확인한다."""
    return (
        data.startswith(b"\xff\xd8\xff")
        or data.startswith(b"\x89PNG\r\n\x1a\n")
        or (data[:4] == b"RIFF" and data[8:12] == b"WEBP")
    )


@router.post("/analyze")
async def analyze_receipt(
    image: UploadFile | None = File(default=None),
    _owner: str = Depends(owner_id),
    analyzer: Analyzer = Depends(get_analyzer),
) -> dict:
    """사진을 정리해 식품 초안을 돌려준다. 저장하지 않는다 (D-006)."""
    if image is None:
        raise ApiError(400, "INVALID_IMAGE", "사진 파일이 없다.", ["image"])

    data = await image.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ApiError(413, "IMAGE_TOO_LARGE", "사진은 10MB 이하여야 한다.", ["image"])
    if not _is_allowed_image(data):
        raise ApiError(400, "INVALID_IMAGE", "jpeg, png, webp 사진만 받는다.", ["image"])

    try:
        raw = analyzer.analyze(data)
        # AI 응답 형식이 이상해도 호출 실패와 같게 다룬다.
        drafts = [CardIn.model_validate(item).model_dump() for item in raw]
    except Exception:  # AI 호출 실패와 응답 형식 오류를 같게 알린다 (API-SPEC A-02)
        raise ApiError(502, "AI_FAILED", "AI 정리에 실패했다.") from None

    if not drafts:
        raise ApiError(422, "NO_FOOD_FOUND", "사진에서 식품을 찾지 못했다.")
    return {"items": drafts}
