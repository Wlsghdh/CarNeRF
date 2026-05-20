from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.dependencies import get_db, require_user, get_current_user
from app.models import Listing, Vehicle, User
from app.schemas import ListingOut, ListingBrief, ListingCreate

router = APIRouter(prefix="/api/listings", tags=["listings"])


@router.get("/", response_model=list[ListingBrief])
def list_listings(
    brand: Optional[str] = None,
    fuel_type: Optional[str] = None,
    region: Optional[str] = None,
    price_min: Optional[int] = None,
    price_max: Optional[int] = None,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
    search: Optional[str] = Query(None),
    sort: Optional[str] = Query("newest", pattern="^(newest|price_asc|price_desc|mileage|region_match)$"),
    page: int = Query(1, ge=1),
    size: int = Query(12, ge=1, le=50),
    has_3d: Optional[bool] = None,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user),
):
    q = db.query(Listing).options(joinedload(Listing.vehicle)).filter(Listing.status == "active")

    if brand:
        q = q.join(Vehicle).filter(Vehicle.brand == brand)
    else:
        q = q.join(Vehicle)

    # 키워드 검색
    if search:
        search_term = f"%{search}%"
        q = q.filter(
            (Listing.title.ilike(search_term)) |
            (Listing.description.ilike(search_term)) |
            (Vehicle.brand.ilike(search_term)) |
            (Vehicle.model.ilike(search_term)) |
            (Vehicle.trim.ilike(search_term))
        )

    # 3D 모델 유무 필터
    if has_3d is True:
        q = q.filter(Vehicle.model_3d_status == "ready")

    if region:
        q = q.filter(Vehicle.region == region)
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

    if sort == "region_match" and user and user.region:
        # 사용자 지역과 같은 매물 먼저
        from sqlalchemy import case
        q = q.order_by(
            case((Vehicle.region == user.region, 0), else_=1),
            Listing.created_at.desc(),
        )
    elif sort == "newest":
        q = q.order_by(Listing.created_at.desc())
    elif sort == "price_asc":
        q = q.order_by(Listing.price.asc())
    elif sort == "price_desc":
        q = q.order_by(Listing.price.desc())
    elif sort == "mileage":
        q = q.order_by(Vehicle.mileage.asc())

    offset = (page - 1) * size
    return q.offset(offset).limit(size).all()


@router.get("/count")
def count_listings(
    brand: Optional[str] = None,
    fuel_type: Optional[str] = None,
    price_min: Optional[int] = None,
    price_max: Optional[int] = None,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
    search: Optional[str] = None,
    has_3d: Optional[bool] = None,
    page_size: int = Query(12, ge=1, le=50),
    db: Session = Depends(get_db),
):
    q = db.query(Listing).filter(Listing.status == "active").join(Vehicle)
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
    if search:
        term = f"%{search}%"
        q = q.filter(
            (Listing.title.ilike(term)) |
            (Vehicle.brand.ilike(term)) |
            (Vehicle.model.ilike(term))
        )
    if has_3d is True:
        q = q.filter(Vehicle.model_3d_status == "ready")

    total = q.count()
    total_pages = (total + page_size - 1) // page_size
    return {"count": total, "total_pages": total_pages}


@router.get("/{listing_id}", response_model=ListingOut)
def get_listing(listing_id: int, db: Session = Depends(get_db)):
    listing = (
        db.query(Listing)
        .options(joinedload(Listing.vehicle), joinedload(Listing.seller))
        .filter(Listing.id == listing_id)
        .first()
    )
    if not listing:
        raise HTTPException(status_code=404, detail="매물을 찾을 수 없습니다.")
    listing.view_count += 1
    db.commit()
    return listing


@router.post("/", response_model=ListingOut)
def create_listing(data: ListingCreate, user: User = Depends(require_user), db: Session = Depends(get_db)):
    if data.vehicle_id:
        # Use existing vehicle (e.g. created by 3D pipeline)
        vehicle = db.query(Vehicle).filter(Vehicle.id == data.vehicle_id).first()
        if not vehicle:
            raise HTTPException(status_code=404, detail="차량을 찾을 수 없습니다.")
        # Update vehicle info with form data
        vehicle.brand = data.brand
        vehicle.model = data.model
        vehicle.year = data.year
        vehicle.trim = data.trim
        vehicle.fuel_type = data.fuel_type
        vehicle.transmission = data.transmission
        vehicle.mileage = data.mileage
        vehicle.color = data.color
        vehicle.engine_cc = data.engine_cc
        vehicle.region = data.region
        # 이미지 URL이 있으면 첫 번째를 썸네일로 설정
        if data.image_urls and len(data.image_urls) > 0:
            vehicle.thumbnail_url = data.image_urls[0]
        elif not vehicle.thumbnail_url:
            vehicle.thumbnail_url = "/static/images/placeholder-car.svg"
        db.flush()
    else:
        thumbnail = "/static/images/placeholder-car.svg"
        if data.image_urls and len(data.image_urls) > 0:
            thumbnail = data.image_urls[0]
        vehicle = Vehicle(
            brand=data.brand,
            model=data.model,
            year=data.year,
            trim=data.trim,
            fuel_type=data.fuel_type,
            transmission=data.transmission,
            mileage=data.mileage,
            color=data.color,
            engine_cc=data.engine_cc,
            region=data.region,
            thumbnail_url=thumbnail,
        )
        db.add(vehicle)
        db.flush()

    listing = Listing(
        vehicle_id=vehicle.id,
        seller_id=user.id,
        title=data.title,
        description=data.description,
        price=data.price,
        is_negotiable=data.is_negotiable,
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return db.query(Listing).options(joinedload(Listing.vehicle), joinedload(Listing.seller)).filter(Listing.id == listing.id).first()
