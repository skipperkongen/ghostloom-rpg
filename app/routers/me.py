"""Profile router."""

from fastapi import APIRouter, Depends

from app.db.models import User
from app.dependencies import get_current_user
from app.schemas.auth import UserResponse

router = APIRouter(tags=["profile"])


@router.get("/me", response_model=UserResponse)
def get_me(user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse(id=user.id, email=user.email, display_name=user.display_name)


@router.get("/me/settings", response_model=UserResponse)
def get_settings(user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse(id=user.id, email=user.email, display_name=user.display_name)
