from fastapi import APIRouter

from app.modules.account.api import admin_router
from app.modules.account.api import auth_router as account_auth_router
from app.modules.auth.api import router as auth_router
from app.modules.supplier.api.router import router as supplier_router

router = APIRouter(prefix="/api/v1")
router.include_router(auth_router)
router.include_router(account_auth_router)
router.include_router(admin_router)
router.include_router(supplier_router)
