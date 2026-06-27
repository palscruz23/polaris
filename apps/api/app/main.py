from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import build_cors_origins, settings
from app.routes.auth import router as auth_router
from app.routes.conversations import router as conversations_router
from app.routes.data_browser import router as data_browser_router
from app.routes.defect_elimination import router as defect_elimination_router
from app.routes.feedback import router as feedback_router
from app.routes.models import router as models_router

app = FastAPI(title="Open Reliability API", version="0.1.0")

cors_origins = build_cors_origins(settings.frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(conversations_router)
app.include_router(data_browser_router)
app.include_router(defect_elimination_router)
app.include_router(feedback_router)
app.include_router(models_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "open-reliability-api"}
