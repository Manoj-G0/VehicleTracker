"""Root API router."""

from fastapi import APIRouter

from app.api.v1 import auth, health, imports, users, vehicles

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/v1", tags=["Authentication"])
api_router.include_router(health.router, prefix="/v1", tags=["Health"])
api_router.include_router(vehicles.router, prefix="/v1", tags=["Vehicles"])
api_router.include_router(imports.router, prefix="/v1", tags=["Imports"])
api_router.include_router(users.router, prefix="/v1", tags=["Users"])
