"""
AI 가격 예측 API
- 학습 완료된 모델이 있다고 가정 (현재는 휴리스틱 기반 mock)
- 실제 모델 학습 후 joblib.load()로 교체
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import Vehicle, Listing

router = APIRouter(prefix="/api/predict", tags=["predict"])


class PriceRequest(BaseModel):
    brand: str
    model: str
    year: int
    mileage: int
    fuel_type: str
    transmission: str = "자동"
    engine_cc: int = 0
    accident_count: int = 0
    defect_score: float = 0.0  # 0~100, 팀B 결함 점수


class PriceResponse(BaseModel):
    predicted_price: int
    price_range_low: int
    price_range_high: int
    confidence: float
    defect_adjusted_price: Optional[int] = None
    defect_discount: Optional[int] = None
    similar_listings: list = []
    depreciation_curve: list = []


# 브랜드별 기본 시세 (만원, 신차 기준 대략적)
BRAND_BASE = {
    "현대": 3000, "기아": 2800, "제네시스": 5000,
    "쉐보레": 2500, "르노": 2200, "쌍용": 2000,
    "BMW": 5500, "벤츠": 6000, "아우디": 5000,
    "폭스바겐": 4000, "볼보": 5000, "토요타": 4500,
    "렉서스": 5500, "혼다": 3500, "포르쉐": 9000,
    "테슬라": 5500,
}


def predict_price_mock(req: PriceRequest) -> dict:
    """
    Mock 가격 예측 (실제 모델 학습 후 교체)
    현실적인 감가 로직 적용
    """
    base = BRAND_BASE.get(req.brand, 3000)

    # 차량 나이에 따른 감가 (연 약 8~12%)
    car_age = max(0, 2026 - req.year)
    age_factor = max(0.25, 1.0 - car_age * 0.09)

    # 주행거리 감가 (1만km당 약 2%)
    mileage_factor = max(0.4, 1.0 - (req.mileage / 10000) * 0.02)

    # 연료 타입 보정
    fuel_adj = {"전기": 1.15, "하이브리드": 1.08, "디젤": 0.97, "가솔린": 1.0, "LPG": 0.85}
    fuel_factor = fuel_adj.get(req.fuel_type, 1.0)

    # 사고 이력 감가
    accident_factor = max(0.6, 1.0 - req.accident_count * 0.12)

    predicted = int(base * age_factor * mileage_factor * fuel_factor * accident_factor)
    predicted = max(100, predicted)  # 최소 100만원

    # 결함 점수 반영
    defect_adjusted = None
    defect_discount = None
    if req.defect_score > 0:
        defect_adjusted = int(predicted * (1 - req.defect_score * 0.003))
        defect_discount = predicted - defect_adjusted

    # 신뢰 구간 (±8%)
    low = int(predicted * 0.92)
    high = int(predicted * 1.08)

    # 감가상각 곡선 (향후 5년)
    depreciation = []
    for y in range(6):
        future_age = car_age + y
        future_factor = max(0.25, 1.0 - future_age * 0.09)
        future_mileage = req.mileage + y * 15000
        future_mil_factor = max(0.4, 1.0 - (future_mileage / 10000) * 0.02)
        p = int(base * future_factor * future_mil_factor * fuel_factor * accident_factor)
        depreciation.append({"year": 2026 + y, "price": max(100, p)})

    confidence = 0.87
    if car_age > 8:
        confidence = 0.72
    elif car_age > 5:
        confidence = 0.80

    return {
        "predicted_price": predicted,
        "price_range_low": low,
        "price_range_high": high,
        "confidence": confidence,
        "defect_adjusted_price": defect_adjusted,
        "defect_discount": defect_discount,
        "depreciation_curve": depreciation,
    }


@router.post("/price", response_model=PriceResponse)
async def predict_price(req: PriceRequest, db: Session = Depends(get_db)):
    result = predict_price_mock(req)

    # 유사 매물 검색
    similar_q = (
        db.query(Listing)
        .join(Vehicle)
        .filter(Vehicle.brand == req.brand)
        .filter(Vehicle.year.between(req.year - 2, req.year + 2))
        .filter(Listing.status == "active")
        .limit(3)
        .all()
    )
    similar = []
    for s in similar_q:
        similar.append({
            "title": s.title,
            "price": s.price,
            "mileage": s.vehicle.mileage,
            "year": s.vehicle.year,
        })
    result["similar_listings"] = similar

    return PriceResponse(**result)


@router.get("/vehicle/{vehicle_id}", response_model=PriceResponse)
async def predict_vehicle_price(vehicle_id: int, db: Session = Depends(get_db)):
    """차량 ID로 바로 예측"""
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        from fastapi import HTTPException
        raise HTTPException(404, "차량을 찾을 수 없습니다.")

    req = PriceRequest(
        brand=vehicle.brand,
        model=vehicle.model,
        year=vehicle.year,
        mileage=vehicle.mileage,
        fuel_type=vehicle.fuel_type,
        transmission=vehicle.transmission,
        engine_cc=vehicle.engine_cc or 0,
    )
    result = predict_price_mock(req)

    # 유사 매물
    similar_q = (
        db.query(Listing)
        .join(Vehicle)
        .filter(Vehicle.brand == vehicle.brand)
        .filter(Vehicle.year.between(vehicle.year - 2, vehicle.year + 2))
        .filter(Vehicle.id != vehicle_id)
        .filter(Listing.status == "active")
        .limit(3)
        .all()
    )
    similar = []
    for s in similar_q:
        similar.append({
            "title": s.title,
            "price": s.price,
            "mileage": s.vehicle.mileage,
            "year": s.vehicle.year,
        })
    result["similar_listings"] = similar

    return PriceResponse(**result)
