"""중고차 시세 조회 API - 내부 거래 데이터 + 외부 API 연동"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.dependencies import get_db, get_current_user
from app.models import Vehicle, Listing, TransactionHistory, User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/market", tags=["market"])

# 외부 API 키 (Carapis Encar API)
CARAPIS_API_KEY = os.getenv("CARAPIS_API_KEY", "")


def _get_internal_stats(db: Session, brand: str, model: str,
                        year: Optional[int] = None,
                        months: int = 6) -> dict:
    """내부 거래 데이터에서 시세 통계를 계산한다."""
    cutoff = datetime.utcnow() - timedelta(days=months * 30)

    query = (
        db.query(TransactionHistory)
        .join(Vehicle, TransactionHistory.vehicle_id == Vehicle.id)
        .filter(
            Vehicle.brand == brand,
            Vehicle.model == model,
            TransactionHistory.transaction_date >= cutoff,
        )
    )
    if year:
        query = query.filter(Vehicle.year == year)

    transactions = query.all()

    if not transactions:
        return None

    prices = [t.price for t in transactions]
    mileages = [t.mileage_at_sale for t in transactions if t.mileage_at_sale]

    return {
        "count": len(prices),
        "avg_price": int(sum(prices) / len(prices)),
        "min_price": min(prices),
        "max_price": max(prices),
        "median_price": sorted(prices)[len(prices) // 2],
        "avg_mileage": int(sum(mileages) / len(mileages)) if mileages else None,
        "recent_transactions": [
            {
                "date": t.transaction_date.strftime("%Y-%m-%d"),
                "price": t.price,
                "mileage": t.mileage_at_sale,
                "source": t.source,
                "region": t.buyer_region or t.seller_region,
            }
            for t in sorted(transactions, key=lambda x: x.transaction_date, reverse=True)[:10]
        ],
    }


def _get_active_listings_stats(db: Session, brand: str, model: str,
                               year: Optional[int] = None) -> dict:
    """현재 판매 중인 매물에서 가격 통계를 계산한다."""
    query = (
        db.query(Listing)
        .join(Vehicle, Listing.vehicle_id == Vehicle.id)
        .filter(
            Vehicle.brand == brand,
            Vehicle.model == model,
            Listing.status == "active",
        )
    )
    if year:
        query = query.filter(Vehicle.year == year)

    listings = query.all()

    if not listings:
        return None

    prices = [l.price for l in listings]

    return {
        "count": len(prices),
        "avg_price": int(sum(prices) / len(prices)),
        "min_price": min(prices),
        "max_price": max(prices),
        "listings": [
            {
                "id": l.id,
                "title": l.title,
                "price": l.price,
                "vehicle_id": l.vehicle_id,
            }
            for l in sorted(listings, key=lambda x: x.price)[:5]
        ],
    }


async def _fetch_external_price(brand: str, model: str,
                                year: Optional[int] = None) -> dict:
    """
    외부 API에서 시세를 조회한다.
    Carapis Encar API 연동 틀 - API 키 설정 시 바로 작동.

    설정 방법:
      export CARAPIS_API_KEY="your-api-key"

    API 문서: https://docs.carapis.com/parsers/encar.com/api-reference
    무료 티어: 1,000대 조회 가능 (API 키 불필요)
    """
    if not CARAPIS_API_KEY:
        # API 키 없이도 무료 티어 사용 가능
        pass

    try:
        import httpx

        params = {
            "brand": brand,
            "model": model,
        }
        if year:
            params["year_min"] = year
            params["year_max"] = year

        headers = {}
        if CARAPIS_API_KEY:
            headers["Authorization"] = f"Bearer {CARAPIS_API_KEY}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            # Carapis Encar API
            response = await client.get(
                "https://api.carapis.com/v1/encar/vehicles",
                params=params,
                headers=headers,
            )

            if response.status_code == 200:
                data = response.json()
                vehicles = data.get("vehicles", data.get("results", []))
                if vehicles:
                    prices = [v.get("price", 0) for v in vehicles if v.get("price")]
                    if prices:
                        return {
                            "source": "encar",
                            "count": len(prices),
                            "avg_price": int(sum(prices) / len(prices)),
                            "min_price": min(prices),
                            "max_price": max(prices),
                            "sample_listings": vehicles[:5],
                        }
    except ImportError:
        logger.info("httpx 미설치 - 외부 시세 조회 스킵 (pip install httpx)")
    except Exception as e:
        logger.warning(f"외부 시세 조회 실패: {e}")

    return None


def _generate_depreciation_estimate(brand: str, model: str, year: int,
                                    current_price: Optional[int] = None) -> dict:
    """감가상각 추정치를 생성한다."""
    current_year = 2026
    age = current_year - year

    # 브랜드별 감가율 (연간)
    depreciation_rates = {
        "현대": 0.12, "기아": 0.13, "제네시스": 0.10,
        "BMW": 0.15, "벤츠": 0.14, "아우디": 0.16,
        "쉐보레": 0.14, "르노": 0.15, "쌍용": 0.14,
    }
    rate = depreciation_rates.get(brand, 0.13)

    # 신차 가격 추정 (모델별)
    new_car_prices = {
        ("현대", "그랜저"): 4200, ("현대", "아반떼"): 2200,
        ("현대", "투싼"): 3200, ("현대", "소나타"): 3000,
        ("현대", "팰리세이드"): 4500, ("현대", "캐스퍼"): 1500,
        ("기아", "K5"): 2800, ("기아", "K8"): 3800,
        ("기아", "쏘렌토"): 3800, ("기아", "카니발"): 3600,
        ("기아", "EV6"): 5500, ("기아", "스포티지"): 3200,
        ("제네시스", "G80"): 6500, ("제네시스", "GV70"): 5500,
        ("제네시스", "GV80"): 7500, ("제네시스", "G70"): 4500,
        ("BMW", "520i"): 6800, ("BMW", "320i"): 5500,
        ("BMW", "X5"): 9500, ("BMW", "X3"): 6500,
        ("벤츠", "E300"): 7500, ("벤츠", "C200"): 5800,
    }
    base_price = new_car_prices.get((brand, model), 3500)

    # 연도별 감가 곡선
    curve = []
    for y in range(0, min(age + 5, 15)):
        estimated = int(base_price * (1 - rate) ** y)
        curve.append({
            "year": current_year - y,
            "age": y,
            "estimated_price": estimated,
            "is_current": y == age,
        })

    estimated_current = int(base_price * (1 - rate) ** age)

    return {
        "new_car_price": base_price,
        "estimated_current": estimated_current,
        "depreciation_rate": round(rate * 100, 1),
        "age_years": age,
        "depreciation_curve": curve,
        "price_vs_estimate": round(
            (current_price / estimated_current * 100), 1
        ) if current_price and estimated_current > 0 else None,
    }


@router.get("/price/{vehicle_id}")
async def get_market_price(
    vehicle_id: int,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user),
):
    """차량의 시세 정보를 종합적으로 조회한다."""
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="차량을 찾을 수 없습니다.")

    listing = db.query(Listing).filter(Listing.vehicle_id == vehicle_id).first()
    current_price = listing.price if listing else None

    # 내부 거래 데이터
    internal = _get_internal_stats(db, vehicle.brand, vehicle.model, vehicle.year)

    # 현재 판매 중인 매물
    active = _get_active_listings_stats(db, vehicle.brand, vehicle.model, vehicle.year)

    # 외부 시세 (Carapis Encar)
    external = await _fetch_external_price(vehicle.brand, vehicle.model, vehicle.year)

    # 감가상각 추정
    depreciation = _generate_depreciation_estimate(
        vehicle.brand, vehicle.model, vehicle.year, current_price
    )

    # 종합 시세 산출
    prices = []
    if internal:
        prices.append(internal["avg_price"])
    if active:
        prices.append(active["avg_price"])
    if external:
        prices.append(external["avg_price"])
    if depreciation:
        prices.append(depreciation["estimated_current"])

    overall_avg = int(sum(prices) / len(prices)) if prices else None

    # 가격 판정
    verdict = None
    if current_price and overall_avg:
        ratio = current_price / overall_avg
        if ratio < 0.90:
            verdict = {"level": "저렴", "color": "#10B981", "message": f"시세 대비 {int((1 - ratio) * 100)}% 저렴합니다"}
        elif ratio < 1.05:
            verdict = {"level": "적정", "color": "#0EA5E9", "message": "시세 수준의 적정 가격입니다"}
        elif ratio < 1.15:
            verdict = {"level": "다소 높음", "color": "#F59E0B", "message": f"시세 대비 {int((ratio - 1) * 100)}% 높습니다"}
        else:
            verdict = {"level": "높음", "color": "#EF4444", "message": f"시세 대비 {int((ratio - 1) * 100)}% 높습니다. 네고를 권장합니다"}

    return {
        "vehicle_id": vehicle_id,
        "vehicle_name": f"{vehicle.brand} {vehicle.model} {vehicle.year}",
        "current_price": current_price,
        "overall_avg_price": overall_avg,
        "verdict": verdict,
        "internal_data": internal,
        "active_listings": active,
        "external_data": external,
        "depreciation": depreciation,
        "data_sources": [
            s for s in [
                "CarNeRF 거래기록" if internal else None,
                "판매중 매물" if active else None,
                "엔카 시세" if external else None,
                "감가상각 모델" if depreciation else None,
            ] if s
        ],
    }


@router.get("/average")
async def get_average_prices(
    brand: Optional[str] = None,
    model: Optional[str] = None,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """브랜드/모델별 평균 거래 가격을 조회한다."""
    query = (
        db.query(
            Vehicle.brand,
            Vehicle.model,
            Vehicle.year,
            func.avg(TransactionHistory.price).label("avg_price"),
            func.count(TransactionHistory.id).label("count"),
            func.min(TransactionHistory.price).label("min_price"),
            func.max(TransactionHistory.price).label("max_price"),
        )
        .join(TransactionHistory, TransactionHistory.vehicle_id == Vehicle.id)
        .group_by(Vehicle.brand, Vehicle.model, Vehicle.year)
    )

    if brand:
        query = query.filter(Vehicle.brand == brand)
    if model:
        query = query.filter(Vehicle.model == model)
    if year_min:
        query = query.filter(Vehicle.year >= year_min)
    if year_max:
        query = query.filter(Vehicle.year <= year_max)

    results = query.order_by(Vehicle.brand, Vehicle.model, Vehicle.year.desc()).all()

    return {
        "results": [
            {
                "brand": r.brand,
                "model": r.model,
                "year": r.year,
                "avg_price": int(r.avg_price),
                "count": r.count,
                "min_price": r.min_price,
                "max_price": r.max_price,
            }
            for r in results
        ],
        "total_count": len(results),
    }
