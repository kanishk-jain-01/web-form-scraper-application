from fastapi import APIRouter

from .scraping import router as scraping_router

router = APIRouter()
router.include_router(scraping_router, prefix="/scraping", tags=["scraping"])
