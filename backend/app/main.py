from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import engine, SessionLocal, Base
from app.models import User, Vehicle, Listing, DiagnosisReport  # noqa: F401
from app.api import pages, vehicles, listings, auth, upload, pipeline, predict, defect
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

# Static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# API routes
app.include_router(auth.router)
app.include_router(vehicles.router)
app.include_router(listings.router)
app.include_router(upload.router)
app.include_router(pipeline.router)
app.include_router(predict.router)
app.include_router(defect.router)

# Page routes
app.include_router(pages.router)
