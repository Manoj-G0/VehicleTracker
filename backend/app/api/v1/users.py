"""Admin endpoints for user management."""

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, require_admin, require_authenticated_user
from app.db.session import get_db
from app.schemas.user import UserCreate, UserList, UserRead, UserUpdate
from app.services.user_service import UserService

router = APIRouter()


def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    return UserService(db)


@router.get("/users", response_model=UserList, summary="List users")
async def list_users(
    service: UserService = Depends(get_user_service),
    _: CurrentUser = Depends(require_admin),
) -> UserList:
    users = await service.list_users()
    return UserList(items=users, total=len(users))


@router.get("/users/{user_id}", response_model=UserRead, summary="Get user")
async def get_user(
    user_id: int,
    service: UserService = Depends(get_user_service),
    _: CurrentUser = Depends(require_admin),
) -> UserRead:
    return await service.get_user(user_id)


@router.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED, summary="Create user")
async def create_user(
    payload: UserCreate,
    service: UserService = Depends(get_user_service),
    _: CurrentUser = Depends(require_admin),
) -> UserRead:
    return await service.create_user(payload)


@router.put("/users/{user_id}", response_model=UserRead, summary="Update user")
async def update_user(
    user_id: int,
    payload: UserUpdate,
    service: UserService = Depends(get_user_service),
    _: CurrentUser = Depends(require_admin),
) -> UserRead:
    return await service.update_user(user_id, payload)


@router.patch("/users/{user_id}/access", response_model=UserRead, summary="Grant or revoke application access")
async def update_access(
    user_id: int,
    payload: UserUpdate,
    service: UserService = Depends(get_user_service),
    _: CurrentUser = Depends(require_admin),
) -> UserRead:
    if payload.allow_access is None:
        from app.core.exceptions import ValidationAppError
        raise ValidationAppError("allow_access is required", field="allow_access")
    return await service.update_user(user_id, UserUpdate(allow_access=payload.allow_access))


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete user")
async def delete_user(
    user_id: int,
    service: UserService = Depends(get_user_service),
    _: CurrentUser = Depends(require_admin),
) -> Response:
    await service.delete_user(user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/profile", response_model=UserRead, summary="Get profile")
async def get_profile(
    user: CurrentUser = Depends(require_authenticated_user),
    service: UserService = Depends(get_user_service),
) -> UserRead:
    return await service.get_profile(user.id)
