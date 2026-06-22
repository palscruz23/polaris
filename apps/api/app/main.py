from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.conversations import router as conversations_router
from app.routes.defect_elimination import router as defect_elimination_router

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

app.include_router(conversations_router)
app.include_router(defect_elimination_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "open-reliability-api"}
