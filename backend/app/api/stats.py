"""관리자/통계 API - 플랫폼 현황 대시보드 데이터"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import datetime, timedelta

from app.dependencies import get_db
from app.models import Vehicle, Listing, User, TransactionHistory, UserReview, Wishlist, LoginHistory

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/dashboard")
def dashboard_stats(db: Session = Depends(get_db)):
    """플랫폼 전체 통계"""
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    total_users = db.query(User).count()
    total_listings = db.query(Listing).filter(Listing.status == "active").count()
    total_vehicles = db.query(Vehicle).count()
    total_3d = db.query(Vehicle).filter(Vehicle.model_3d_status == "ready").count()
    total_transactions = db.query(TransactionHistory).count()
    total_reviews = db.query(UserReview).count()

    # 이번 주 신규
    new_users_week = db.query(User).filter(User.created_at >= week_ago).count()
    new_listings_week = db.query(Listing).filter(Listing.created_at >= week_ago).count()

    # 브랜드별 매물 분포
    brand_dist = (
        db.query(Vehicle.brand, func.count(Listing.id))
        .join(Listing, Listing.vehicle_id == Vehicle.id)
        .filter(Listing.status == "active")
        .group_by(Vehicle.brand)
        .order_by(func.count(Listing.id).desc())
        .all()
    )

    # 가격대 분포
    price_ranges = [
        ("1000만원 이하", 0, 1000),
        ("1000~2000만원", 1000, 2000),
        ("2000~3000만원", 2000, 3000),
        ("3000~5000만원", 3000, 5000),
        ("5000만원 이상", 5000, 999999),
    ]
    price_dist = []
    for label, pmin, pmax in price_ranges:
        count = (
            db.query(Listing)
            .filter(Listing.status == "active", Listing.price >= pmin, Listing.price < pmax)
            .count()
        )
        price_dist.append({"label": label, "count": count})

    # 연식 분포
    year_dist = (
        db.query(Vehicle.year, func.count(Vehicle.id))
        .join(Listing, Listing.vehicle_id == Vehicle.id)
        .filter(Listing.status == "active")
        .group_by(Vehicle.year)
        .order_by(Vehicle.year.desc())
        .limit(10)
        .all()
    )

    return {
        "overview": {
            "total_users": total_users,
            "total_listings": total_listings,
            "total_vehicles": total_vehicles,
            "total_3d_models": total_3d,
            "total_transactions": total_transactions,
            "total_reviews": total_reviews,
            "new_users_week": new_users_week,
            "new_listings_week": new_listings_week,
        },
        "brand_distribution": [{"brand": b, "count": c} for b, c in brand_dist],
        "price_distribution": price_dist,
        "year_distribution": [{"year": y, "count": c} for y, c in year_dist],
    }


@router.get("/price-trends")
def price_trends(
    brand: str = Query(None),
    model: str = Query(None),
    db: Session = Depends(get_db),
):
    """브랜드/모델별 가격 추이"""
    q = db.query(TransactionHistory).join(Vehicle)

    if brand:
        q = q.filter(Vehicle.brand == brand)
    if model:
        q = q.filter(Vehicle.model == model)

    transactions = q.order_by(TransactionHistory.transaction_date.asc()).all()

    if not transactions:
        return {"trends": [], "avg_price": 0}

    trends = []
    for t in transactions:
        trends.append({
            "date": t.transaction_date.isoformat() if t.transaction_date else None,
            "price": t.price,
            "mileage": t.mileage_at_sale,
        })

    avg = sum(t.price for t in transactions) / len(transactions)

    return {
        "trends": trends,
        "avg_price": round(avg),
        "total_transactions": len(transactions),
    }
