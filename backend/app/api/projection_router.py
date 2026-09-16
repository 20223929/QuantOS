from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/projections", tags=["projections"])


@router.get("/{aggregate_id}")
async def get_projection(aggregate_id: str):
    """Return projection state placeholder endpoint.

    Repository wiring is injected by the application layer when persistence
    services are available.
    """
    raise HTTPException(status_code=404, detail="Projection not found")
