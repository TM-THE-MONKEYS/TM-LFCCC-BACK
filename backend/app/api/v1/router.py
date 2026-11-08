from fastapi import APIRouter

from app.api.v1.endpoints import auth, donations, products, reports, sales, users

router = APIRouter()

router.include_router(products.router, prefix="/products", tags=["Products"])
router.include_router(sales.router, prefix="/sales", tags=["Sales"])
router.include_router(donations.router, prefix="/donations", tags=["Donations"])
router.include_router(reports.router, prefix="/reports", tags=["Reports"])
router.include_router(auth.router, prefix="/auth", tags=["Auth"])
router.include_router(users.router, prefix="/users", tags=["Users"])
