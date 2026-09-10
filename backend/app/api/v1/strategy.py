from fastapi import APIRouter

router = APIRouter(prefix="/strategy", tags=["strategy"])


@router.get("/list")
async def list_strategy():
    return {"strategies": []}


@router.post("/start/{name}")
async def start_strategy(name: str):
    return {"name": name, "status": "started"}


@router.post("/stop/{name}")
async def stop_strategy(name: str):
    return {"name": name, "status": "stopped"}
