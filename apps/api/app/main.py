from fastapi import FastAPI


app = FastAPI(title="Open Reliability API", version="0.1.0")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "open-reliability-api"}
