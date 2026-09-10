from fastapi import FastAPI

app = FastAPI(title="QuantOS Next API", version="0.1.0")


@app.get("/")
async def root():
    return {"name": "QuantOS Next", "version": "0.1.0"}


@app.get("/api/v1/health")
async def health():
    return {
        "status": "ok",
        "service": "quantos-api",
        "version": "0.1.0",
    }
