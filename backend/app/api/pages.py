import math
from typing import Optional

from fastapi import APIRouter, Depends, Request, Query
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from app.dependencies import get_db, get_current_user
from app.models import Listing, Vehicle, User, DiagnosisReport, UserReview, TransactionHistory

router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/promo-viewer")
def promo_viewer(request: Request):
    """Public 3DGS viewer for promo screen-recording (no auth, fullscreen)."""
    return templates.TemplateResponse("promo_viewer.html", {"request": request})


@router.get("/")
def home(request: Request, db: Session = Depends(get_db), user: Optional[User] = Depends(get_current_user)):
    featured = (
        db.query(Listing)
        .options(joinedload(Listing.vehicle).joinedload(Vehicle.diagnosis))
        .filter(Listing.status == "active")
        .order_by(Listing.view_count.desc())
        .limit(4)
        .all()
    )

    # 실제 통계
    stats = {
        "total_listings": db.query(Listing).filter(Listing.status == "active").count(),
        "total_vehicles": db.query(Vehicle).count(),
        "total_transactions": db.query(TransactionHistory).count(),
        "total_3d_models": db.query(Vehicle).filter(Vehicle.model_3d_status == "ready").count(),
        "total_users": db.query(User).count(),
    }

    return templates.TemplateResponse("home.html", {
        "request": request,
        "user": user,
        "featured": featured,
        "stats": stats,
    })


@router.get("/listings")
def listings_page(
    request: Request,
    brand: Optional[str] = None,
    fuel_type: Optional[str] = None,
    region: Optional[str] = None,
    price_min: Optional[int] = None,
    price_max: Optional[int] = None,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
    search: Optional[str] = None,
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
    if region:
        q = q.filter(Vehicle.region == region)
    if price_min is not None:
        q = q.filter(Listing.price >= price_min)
    if price_max is not None:
        q = q.filter(Listing.price <= price_max)
    if year_min is not None:
        q = q.filter(Vehicle.year >= year_min)
    if year_max is not None:
        q = q.filter(Vehicle.year <= year_max)
    if search:
        term = f"%{search}%"
        q = q.filter(
            (Listing.title.ilike(term)) |
            (Listing.description.ilike(term)) |
            (Vehicle.brand.ilike(term)) |
            (Vehicle.model.ilike(term)) |
            (Vehicle.trim.ilike(term))
        )

    total = q.count()

    if sort == "region_match" and user and user.region:
        from sqlalchemy import case
        q = q.order_by(
            case((Vehicle.region == user.region, 0), else_=1),
            Listing.created_at.desc(),
        )
    elif sort == "price_asc":
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
    regions = [r[0] for r in db.query(Vehicle.region).filter(Vehicle.region.isnot(None)).distinct().order_by(Vehicle.region).all()]

    return templates.TemplateResponse("listings.html", {
        "request": request,
        "user": user,
        "listings": listings,
        "total": total,
        "total_pages": total_pages,
        "current_page": page,
        "brands": brands,
        "regions": regions,
        "filters": {
            "brand": brand,
            "fuel_type": fuel_type,
            "region": region,
            "price_min": price_min,
            "price_max": price_max,
            "year_min": year_min,
            "year_max": year_max,
            "search": search,
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
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="차량을 찾을 수 없습니다.")

    listing = (
        db.query(Listing)
        .options(joinedload(Listing.seller))
        .filter(Listing.vehicle_id == vehicle_id)
        .first()
    )
    if listing:
        # 세션 기반 중복 방지: 쿠키에 viewed 플래그
        viewed_key = f"viewed_{vehicle_id}"
        if not request.cookies.get(viewed_key):
            listing.view_count += 1
            db.commit()

    diagnosis = db.query(DiagnosisReport).filter(DiagnosisReport.vehicle_id == vehicle_id).first()
    review_count = db.query(UserReview).filter(UserReview.vehicle_id == vehicle_id).count()
    transaction_count = db.query(TransactionHistory).filter(TransactionHistory.vehicle_id == vehicle_id).count()

    response = templates.TemplateResponse("vehicle_detail.html", {
        "request": request,
        "user": user,
        "vehicle": vehicle,
        "listing": listing,
        "diagnosis": diagnosis,
        "review_count": review_count,
        "transaction_count": transaction_count,
    })
    # 조회수 중복 방지 쿠키 (1시간)
    viewed_key = f"viewed_{vehicle_id}"
    if not request.cookies.get(viewed_key):
        response.set_cookie(viewed_key, "1", max_age=3600, httponly=True)
    return response


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


@router.get("/mypage")
def mypage(request: Request, db: Session = Depends(get_db), user: Optional[User] = Depends(get_current_user)):
    if not user:
        return templates.TemplateResponse("login.html", {"request": request, "user": None})
    return templates.TemplateResponse("mypage.html", {"request": request, "user": user})


@router.get("/compare")
def compare_page(request: Request, user: Optional[User] = Depends(get_current_user)):
    return templates.TemplateResponse("compare.html", {"request": request, "user": user})


@router.get("/viewer/{vehicle_id}")
def viewer_page(
    request: Request,
    vehicle_id: int,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user),
):
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="차량을 찾을 수 없습니다.")

    return templates.TemplateResponse("viewer.html", {
        "request": request,
        "user": user,
        "vehicle": vehicle,
    })
