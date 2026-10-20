from fastapi import FastAPI

from backend.errors import install_error_handlers
from backend.routes_cards import router as cards_router

app = FastAPI(title="Task Flow API")
install_error_handlers(app)
app.include_router(cards_router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
