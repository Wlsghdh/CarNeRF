import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from fastapi.templating import Jinja2Templates

from app.config import CORS_ORIGINS, BASE_DIR

templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "app", "templates"))
from app.database import engine, SessionLocal, Base

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
from app.models import User, Vehicle, Listing, DiagnosisReport, PointTransaction, UserReview, TransactionHistory, Wishlist, LoginHistory, AIAnalysisCache  # noqa: F401
from app.api import pages, vehicles, listings, auth, upload, pipeline, predict, defect
from app.api import ai_summary, points, reviews, transactions, seller, market_price, wishlist
from app.api import search, stats
from app.services.seed_data import seed_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables & seed data
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="CarNeRF",
    description="AI 기반 3D 중고차 플랫폼",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Error handlers
from fastapi.exceptions import HTTPException as StarletteHTTPException

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404 and not request.url.path.startswith("/api/"):
        return templates.TemplateResponse("error.html", {
            "request": request,
            "user": None,
            "error_code": 404,
            "error_title": "페이지를 찾을 수 없습니다",
            "error_message": "요청하신 페이지가 존재하지 않거나 이동되었습니다.",
        }, status_code=404)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.getLogger("app").error(f"Unhandled error: {exc}", exc_info=True)
    if not request.url.path.startswith("/api/"):
        return templates.TemplateResponse("error.html", {
            "request": request,
            "user": None,
            "error_code": 500,
            "error_title": "서버 오류",
            "error_message": "예상치 못한 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
        }, status_code=500)
    return JSONResponse(
        status_code=500,
        content={"detail": "서버 내부 오류가 발생했습니다."},
    )


# Static files (absolute paths for reliability)
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "app", "static")), name="static")
app.mount("/uploads", StaticFiles(directory=os.path.join(BASE_DIR, "uploads")), name="uploads")
app.mount("/promo", StaticFiles(directory=os.path.join(BASE_DIR, "..", "promo_assets"), html=True), name="promo")

# API routes
app.include_router(auth.router)
app.include_router(vehicles.router)
app.include_router(listings.router)
app.include_router(upload.router)
app.include_router(pipeline.router)
app.include_router(predict.router)
app.include_router(defect.router)
app.include_router(ai_summary.router)
app.include_router(points.router)
app.include_router(reviews.router)
app.include_router(transactions.router)
app.include_router(seller.router)
app.include_router(market_price.router)
app.include_router(wishlist.router)
app.include_router(search.router)
app.include_router(stats.router)

# Page routes
app.include_router(pages.router)
