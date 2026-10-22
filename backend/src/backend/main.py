from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.auth import session_secret
from backend.errors import install_error_handlers
from backend.routes_auth import router as auth_router
from backend.routes_cards import router as cards_router
from backend.routes_receipts import router as receipts_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    session_secret()  # SESSION_SECRET 이 없으면 시작하지 않는다.
    yield


app = FastAPI(title="Task Flow API", lifespan=lifespan)
install_error_handlers(app)
app.include_router(auth_router)
app.include_router(cards_router)
app.include_router(receipts_router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
