from fastapi import APIRouter

from app.modules.auth.api import router as auth_router
from app.modules.supplier.api.router import router as supplier_router

router = APIRouter(prefix="/api/v1")
router.include_router(auth_router)
router.include_router(supplier_router)
