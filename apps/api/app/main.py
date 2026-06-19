from fastapi import FastAPI

from app.routes.chat import router as chat_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Open Reliability API", version="0.1.0")


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "open-reliability-api"}
