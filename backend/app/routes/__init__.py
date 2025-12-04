"""
API Routes - Combines all route modules into a single router.
"""
from fastapi import APIRouter

from .products import router as products_router
from .customers import router as customers_router
from .policies import router as policies_router
from .calls import router as calls_router

# Main router that includes all sub-routers
router = APIRouter()
router.include_router(products_router)
router.include_router(customers_router)
router.include_router(policies_router)
router.include_router(calls_router)

__all__ = ["router"]
