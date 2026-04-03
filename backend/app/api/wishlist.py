"""위시리스트(찜하기) API"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_user, get_current_user
from app.models import Wishlist, Vehicle, Listing, User

router = APIRouter(prefix="/api/wishlist", tags=["wishlist"])


@router.get("/")
def get_my_wishlist(
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """내 찜 목록을 조회한다."""
    items = (
        db.query(Wishlist)
        .filter(Wishlist.user_id == user.id)
        .order_by(Wishlist.created_at.desc())
        .all()
    )

    result = []
    for w in items:
        vehicle = db.query(Vehicle).filter(Vehicle.id == w.vehicle_id).first()
        if not vehicle:
            continue
        listing = db.query(Listing).filter(Listing.vehicle_id == vehicle.id).first()
        result.append({
            "wishlist_id": w.id,
            "vehicle_id": vehicle.id,
            "brand": vehicle.brand,
            "model": vehicle.model,
            "year": vehicle.year,
            "mileage": vehicle.mileage,
            "thumbnail_url": vehicle.thumbnail_url,
            "model_3d_status": vehicle.model_3d_status,
            "listing_id": listing.id if listing else None,
            "title": listing.title if listing else f"{vehicle.brand} {vehicle.model}",
            "price": listing.price if listing else None,
            "status": listing.status if listing else None,
            "created_at": w.created_at.isoformat(),
        })

    return {"items": result, "count": len(result)}


@router.post("/toggle/{vehicle_id}")
def toggle_wishlist(
    vehicle_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """찜을 토글한다 (추가/제거)."""
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="차량을 찾을 수 없습니다.")

    existing = (
        db.query(Wishlist)
        .filter(Wishlist.user_id == user.id, Wishlist.vehicle_id == vehicle_id)
        .first()
    )

    if existing:
        db.delete(existing)
        db.commit()
        return {"wishlisted": False, "message": "찜이 해제되었습니다."}
    else:
        wishlist = Wishlist(user_id=user.id, vehicle_id=vehicle_id)
        db.add(wishlist)
        db.commit()
        return {"wishlisted": True, "message": "찜 목록에 추가되었습니다."}


@router.get("/check/{vehicle_id}")
def check_wishlist(
    vehicle_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """특정 차량의 찜 여부를 확인한다."""
    if not user:
        return {"wishlisted": False}

    existing = (
        db.query(Wishlist)
        .filter(Wishlist.user_id == user.id, Wishlist.vehicle_id == vehicle_id)
        .first()
    )
    return {"wishlisted": existing is not None}


@router.get("/count/{vehicle_id}")
def get_wishlist_count(
    vehicle_id: int,
    db: Session = Depends(get_db),
):
    """특정 차량의 찜 수를 조회한다."""
    count = db.query(Wishlist).filter(Wishlist.vehicle_id == vehicle_id).count()
    return {"vehicle_id": vehicle_id, "count": count}
