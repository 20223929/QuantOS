from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.api.projection_router import router as projection_router
from app.websocket.projection_routes import router as projection_websocket_router
from app.api.v1.trading import execution_outbox_dispatcher
from app.storage.execution_outbox_worker import ExecutionOutboxWorker


outbox_worker = ExecutionOutboxWorker(execution_outbox_dispatcher)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    outbox_worker.start()
    try:
        yield
    finally:
        await outbox_worker.stop()


app = FastAPI(title="QuantOS Next API", version="0.1.0", lifespan=lifespan)
app.include_router(api_router, prefix="/api/v1")
app.include_router(projection_router)
app.include_router(projection_websocket_router)


@app.get("/")
async def root():
    return {"name": "QuantOS Next API", "version": "0.1.0"}


@app.get("/api/v1/health")
async def health():
    return {
        "status": "ok",
        "service": "quantos-api",
        "version": "0.1.0",
    }
