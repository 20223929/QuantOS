from fastapi import APIRouter, HTTPException

from app.storage.repositories.state_projection_repository import StateProjectionRepository

router = APIRouter(prefix="/api/projections", tags=["projections"])


class _EmptySession:
    def get(self, *_args, **_kwargs):
        return None


def get_repository():
    return StateProjectionRepository(_EmptySession())


@router.get("/{aggregate_id}")
async def get_projection(aggregate_id: str):
    """Return persisted projection state."""
    repository = get_repository()
    projection = repository.get(aggregate_id)

    if projection is None:
        raise HTTPException(status_code=404, detail="Projection not found")

    return {
        "aggregate_id": projection.aggregate_id,
        "version": projection.version,
        "state": projection.state_json,
    }
