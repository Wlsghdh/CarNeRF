import math
from typing import Optional

from fastapi import APIRouter, Depends, Request, Query
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from app.dependencies import get_db, get_current_user
from app.models import Listing, Vehicle, User, DiagnosisReport

router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/")
def home(request: Request, db: Session = Depends(get_db), user: Optional[User] = Depends(get_current_user)):
    featured = (
        db.query(Listing)
        .options(joinedload(Listing.vehicle))
        .filter(Listing.status == "active")
        .order_by(Listing.view_count.desc())
        .limit(4)
        .all()
    )
    return templates.TemplateResponse("home.html", {
        "request": request,
        "user": user,
        "featured": featured,
    })


@router.get("/listings")
def listings_page(
    request: Request,
    brand: Optional[str] = None,
    fuel_type: Optional[str] = None,
    price_min: Optional[int] = None,
    price_max: Optional[int] = None,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
    sort: str = "newest",
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user),
):
    PAGE_SIZE = 12

    q = db.query(Listing).options(joinedload(Listing.vehicle)).filter(Listing.status == "active").join(Vehicle)

    if brand:
        q = q.filter(Vehicle.brand == brand)
    if fuel_type:
        q = q.filter(Vehicle.fuel_type == fuel_type)
    if price_min is not None:
        q = q.filter(Listing.price >= price_min)
    if price_max is not None:
        q = q.filter(Listing.price <= price_max)
    if year_min is not None:
        q = q.filter(Vehicle.year >= year_min)
    if year_max is not None:
        q = q.filter(Vehicle.year <= year_max)

    total = q.count()

    if sort == "price_asc":
        q = q.order_by(Listing.price.asc())
    elif sort == "price_desc":
        q = q.order_by(Listing.price.desc())
    elif sort == "mileage":
        q = q.order_by(Vehicle.mileage.asc())
    else:
        q = q.order_by(Listing.created_at.desc())

    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    listings = q.offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE).all()

    brands = [r[0] for r in db.query(Vehicle.brand).distinct().order_by(Vehicle.brand).all()]

    return templates.TemplateResponse("listings.html", {
        "request": request,
        "user": user,
        "listings": listings,
        "total": total,
        "total_pages": total_pages,
        "current_page": page,
        "brands": brands,
        "filters": {
            "brand": brand,
            "fuel_type": fuel_type,
            "price_min": price_min,
            "price_max": price_max,
            "year_min": year_min,
            "year_max": year_max,
            "sort": sort,
        },
    })


@router.get("/vehicles/{vehicle_id}")
def vehicle_detail(
    request: Request,
    vehicle_id: int,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user),
):
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        return templates.TemplateResponse("home.html", {
            "request": request, "user": user, "featured": [],
        }, status_code=404)

    listing = (
        db.query(Listing)
        .options(joinedload(Listing.seller))
        .filter(Listing.vehicle_id == vehicle_id)
        .first()
    )
    if listing:
        listing.view_count += 1
        db.commit()

    diagnosis = db.query(DiagnosisReport).filter(DiagnosisReport.vehicle_id == vehicle_id).first()

    return templates.TemplateResponse("vehicle_detail.html", {
        "request": request,
        "user": user,
        "vehicle": vehicle,
        "listing": listing,
        "diagnosis": diagnosis,
    })


@router.get("/sell")
def sell_page(request: Request, user: Optional[User] = Depends(get_current_user)):
    return templates.TemplateResponse("sell.html", {
        "request": request,
        "user": user,
    })


@router.get("/login")
def login_page(request: Request, user: Optional[User] = Depends(get_current_user)):
    return templates.TemplateResponse("login.html", {
        "request": request,
        "user": user,
    })


@router.get("/viewer/{vehicle_id}")
def viewer_page(
    request: Request,
    vehicle_id: int,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user),
):
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        return templates.TemplateResponse("home.html", {
            "request": request, "user": user, "featured": [],
        }, status_code=404)

    return templates.TemplateResponse("viewer.html", {
        "request": request,
        "user": user,
        "vehicle": vehicle,
    })
