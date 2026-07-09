"""API key settings router."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.models import User
from app.db.session import get_db
from app.dependencies import get_current_user
from app.schemas.api_keys import ApiKeyCreateRequest, ApiKeyResponse
from app.services.api_key_service import ApiKeyError, ApiKeyService

router = APIRouter(prefix="/me/settings", tags=["settings"])


@router.get("/api-keys", response_model=list[ApiKeyResponse])
def list_api_keys(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ApiKeyResponse]:
    keys = ApiKeyService(db).list_keys(user.id)
    return [
        ApiKeyResponse(
            id=k.id,
            vendor=k.vendor.value,
            last_four=k.last_four,
            created_at=k.created_at,
        )
        for k in keys
    ]


@router.post("/api-keys", response_model=ApiKeyResponse, status_code=status.HTTP_201_CREATED)
def create_api_key(
    req: ApiKeyCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiKeyResponse:
    try:
        key = ApiKeyService(db).create_key(user.id, req.vendor, req.api_key)
    except ApiKeyError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    return ApiKeyResponse(
        id=key.id,
        vendor=key.vendor.value,
        last_four=key.last_four,
        created_at=key.created_at,
    )


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_api_key(
    key_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        ApiKeyService(db).delete_key(user.id, key_id)
    except ApiKeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
