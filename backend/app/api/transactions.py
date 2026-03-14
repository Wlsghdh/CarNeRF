"""차량 거래기록 / 시세 API"""
from datetime import datetime, timedelta
import random
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.dependencies import get_db
from app.models import Vehicle, Listing, TransactionHistory

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.get("/vehicle/{vehicle_id}")
def get_vehicle_transactions(vehicle_id: int, db: Session = Depends(get_db)):
    """특정 차량의 거래기록 (같은 모델 포함)"""
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="차량을 찾을 수 없습니다.")

    # 해당 차량의 직접 거래기록
    histories = (
        db.query(TransactionHistory)
        .filter(TransactionHistory.vehicle_id == vehicle_id)
        .order_by(TransactionHistory.transaction_date.desc())
        .all()
    )

    # 같은 브랜드/모델의 거래기록 (시세 참고)
    similar_histories = (
        db.query(TransactionHistory)
        .join(Vehicle)
        .filter(
            Vehicle.brand == vehicle.brand,
            Vehicle.model == vehicle.model,
            Vehicle.id != vehicle_id,
        )
        .order_by(TransactionHistory.transaction_date.desc())
        .limit(10)
        .all()
    )

    return {
        "vehicle_id": vehicle_id,
        "vehicle_name": f"{vehicle.brand} {vehicle.model}",
        "direct_transactions": [
            {
                "id": h.id,
                "date": h.transaction_date.strftime("%Y-%m-%d"),
                "price": h.price,
                "mileage": h.mileage_at_sale,
                "source": h.source,
                "buyer_region": h.buyer_region,
                "seller_region": h.seller_region,
            }
            for h in histories
        ],
        "similar_transactions": [
            {
                "id": h.id,
                "date": h.transaction_date.strftime("%Y-%m-%d"),
                "price": h.price,
                "mileage": h.mileage_at_sale,
                "source": h.source,
                "buyer_region": h.buyer_region,
            }
            for h in similar_histories
        ],
    }


@router.get("/market-price/{vehicle_id}")
def get_market_price(vehicle_id: int, db: Session = Depends(get_db)):
    """차량 시세 분석 (같은 모델 기준 평균가격)"""
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="차량을 찾을 수 없습니다.")

    # 같은 브랜드/모델의 현재 판매중인 매물 가격
    active_prices = (
        db.query(Listing.price)
        .join(Vehicle)
        .filter(
            Vehicle.brand == vehicle.brand,
            Vehicle.model == vehicle.model,
            Listing.status == "active",
        )
        .all()
    )
    prices = [p[0] for p in active_prices]

    # 같은 브랜드/모델의 과거 거래가격
    past_prices = (
        db.query(TransactionHistory.price, TransactionHistory.transaction_date)
        .join(Vehicle)
        .filter(
            Vehicle.brand == vehicle.brand,
            Vehicle.model == vehicle.model,
        )
        .order_by(TransactionHistory.transaction_date.desc())
        .limit(20)
        .all()
    )

    all_prices = prices + [p[0] for p in past_prices]

    if not all_prices:
        # 데이터가 없으면 현재 매물가 기준 추정
        listing = db.query(Listing).filter(Listing.vehicle_id == vehicle_id).first()
        base = listing.price if listing else 2500
        return {
            "vehicle_id": vehicle_id,
            "vehicle_name": f"{vehicle.brand} {vehicle.model}",
            "avg_price": base,
            "min_price": int(base * 0.85),
            "max_price": int(base * 1.15),
            "sample_count": 0,
            "price_trend": "stable",
            "active_listings_count": len(prices),
            "monthly_prices": [],
        }

    avg = int(sum(all_prices) / len(all_prices))
    min_p = min(all_prices)
    max_p = max(all_prices)

    # 가격 추세 (최근 거래 vs 평균)
    if past_prices and len(past_prices) >= 2:
        recent = past_prices[0][0]
        older = past_prices[-1][0]
        if recent < older * 0.95:
            trend = "decreasing"
        elif recent > older * 1.05:
            trend = "increasing"
        else:
            trend = "stable"
    else:
        trend = "stable"

    # 월별 평균가 (최근 12개월) — 빈 월도 보간하여 포함
    monthly = []
    now = datetime.utcnow()
    last_known_price = avg
    for i in range(11, -1, -1):
        month_start = (now - timedelta(days=30 * i)).replace(day=1)
        month_end = (month_start + timedelta(days=32)).replace(day=1)
        month_prices = [
            p[0] for p in past_prices
            if month_start <= p[1] < month_end
        ]
        if month_prices:
            month_avg = int(sum(month_prices) / len(month_prices))
            last_known_price = month_avg
        else:
            month_avg = last_known_price
        monthly.append({
            "month": month_start.strftime("%Y-%m"),
            "avg_price": month_avg,
            "count": len(month_prices),
        })

    return {
        "vehicle_id": vehicle_id,
        "vehicle_name": f"{vehicle.brand} {vehicle.model}",
        "avg_price": avg,
        "min_price": min_p,
        "max_price": max_p,
        "sample_count": len(all_prices),
        "price_trend": trend,
        "active_listings_count": len(prices),
        "monthly_prices": monthly,
    }
