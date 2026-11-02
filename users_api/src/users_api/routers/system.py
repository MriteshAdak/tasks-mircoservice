"""Operational endpoints for the user API."""

from fastapi import APIRouter


router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict[str, str]:
    """Return a liveness response without opening a database connection."""

    return {"status": "ok"}
