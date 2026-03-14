"""
AI 가격 예측 API
- .pkl 모델이 있으면 실제 ML 모델 사용 (LightGBM/XGBoost)
- 없으면 휴리스틱 mock으로 폴백
"""

import os
import logging

import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import Vehicle, Listing
from app.config import BASE_DIR

router = APIRouter(prefix="/api/predict", tags=["predict"])
logger = logging.getLogger(__name__)

# ── 모델 경로 ──
MODEL_DIR = os.path.join(os.path.dirname(BASE_DIR), "backend", "app", "ml_models")
PRICE_MODEL_PATH = os.path.join(MODEL_DIR, "price_predictor.pkl")
PRICE_ENCODERS_PATH = os.path.join(MODEL_DIR, "price_encoders.pkl")
PRICE_FEATURES_PATH = os.path.join(MODEL_DIR, "price_features.pkl")
PRICE_META_PATH = os.path.join(MODEL_DIR, "price_meta.pkl")

# ── 모델 로드 (서버 시작 시 1회) ──
_price_model = None
_price_encoders = None
_price_features = None
_price_meta = None
_model_loaded = False


def _load_price_model():
    """가격 예측 모델을 로드. .pkl 파일이 없으면 None"""
    global _price_model, _price_encoders, _price_features, _price_meta, _model_loaded
    if _model_loaded:
        return _price_model is not None

    _model_loaded = True
    try:
        if not os.path.exists(PRICE_MODEL_PATH):
            logger.info(f"[가격예측] 모델 파일 없음: {PRICE_MODEL_PATH} → mock 모드")
            return False

        import joblib
        _price_model = joblib.load(PRICE_MODEL_PATH)
        _price_encoders = joblib.load(PRICE_ENCODERS_PATH)
        _price_features = joblib.load(PRICE_FEATURES_PATH)
        _price_meta = joblib.load(PRICE_META_PATH)
        logger.info(f"[가격예측] 모델 로드 성공: {_price_meta.get('best_model', '?')} (R²={_price_meta.get('r2', '?')})")
        return True
    except Exception as e:
        logger.warning(f"[가격예측] 모델 로드 실패: {e} → mock 모드")
        _price_model = None
        return False


class PriceRequest(BaseModel):
    brand: str
    model: str
    year: int
    mileage: int
    fuel_type: str
    transmission: str = "자동"
    engine_cc: int = 0
    region: str = "서울"
    accident_count: int = 0
    defect_score: float = 0.0


class PriceResponse(BaseModel):
    predicted_price: int
    price_range_low: int
    price_range_high: int
    confidence: float
    defect_adjusted_price: Optional[int] = None
    defect_discount: Optional[int] = None
    similar_listings: list = []
    depreciation_curve: list = []
    model_type: str = "mock"  # "ml" or "mock"


# ── 브랜드 등급 (학습 스크립트와 동일) ──
LUXURY_BRANDS = {'제네시스', 'BMW', '벤츠', '아우디', '볼보', '렉서스', '포르쉐',
                 '랜드로버', '재규어', '마세라티', '벤틀리', '롤스로이스'}
IMPORT_BRANDS = {'폭스바겐', '토요타', '혼다', '미니', '지프', '푸조',
                 '시트로엥', '닛산', '포드', '테슬라', '폴스타'}
FUEL_MAP = {'가솔린': 0, '디젤': 1, '전기': 2, '하이브리드': 3, 'LPG': 4, 'CNG': 5}


def _safe_label_encode(encoder, value: str) -> int:
    """학습 데이터에 없는 값이면 0 반환"""
    try:
        return int(encoder.transform([value])[0])
    except (ValueError, KeyError):
        return 0


def predict_price_ml(req: PriceRequest) -> dict:
    """실제 ML 모델을 사용한 가격 예측"""
    car_age = max(0, 2026 - req.year)
    annual_mileage = req.mileage / (car_age + 0.5)

    brand_tier = 3 if req.brand in LUXURY_BRANDS else (2 if req.brand in IMPORT_BRANDS else 1)
    fuel_encoded = FUEL_MAP.get(req.fuel_type, 0)

    brand_le = _safe_label_encode(_price_encoders['brand'], req.brand)
    model_le = _safe_label_encode(_price_encoders['model'], req.model)
    fuel_le = _safe_label_encode(_price_encoders['fuel_type'], req.fuel_type)
    region_le = _safe_label_encode(_price_encoders['region'], req.region) if 'region' in _price_encoders else 0

    # brand_avg_price, model_avg_price는 학습 시 target encoding이므로 대략적 추정
    brand_avg = {
        '현대': 1800, '기아': 1700, '제네시스': 4500, '쉐보레': 1500,
        '르노': 1300, 'BMW': 4000, '벤츠': 5000, '아우디': 3800,
        '볼보': 3500, '토요타': 3000, '테슬라': 4500,
    }
    model_avg_price = brand_avg.get(req.brand, 2000)
    brand_avg_price = brand_avg.get(req.brand, 2000)

    # 피처 벡터 구성 (학습 시 feature_cols 순서 동일)
    feature_dict = {
        'year': req.year,
        'mileage': req.mileage,
        'car_age': car_age,
        'annual_mileage': annual_mileage,
        'brand_tier': brand_tier,
        'fuel_encoded': fuel_encoded,
        'engine_cc': req.engine_cc,
        'brand_avg_price': brand_avg_price,
        'model_avg_price': model_avg_price,
        'brand_le': brand_le,
        'model_le': model_le,
        'fuel_type_le': fuel_le,
        'region_le': region_le,
    }

    X = np.array([[feature_dict.get(f, 0) for f in _price_features]])
    predicted = int(max(50, _price_model.predict(X)[0]))

    # 결함 반영
    defect_adjusted = None
    defect_discount = None
    if req.defect_score > 0:
        defect_adjusted = int(predicted * (1 - req.defect_score * 0.003))
        defect_discount = predicted - defect_adjusted

    # 사고 이력 반영
    if req.accident_count > 0:
        predicted = int(predicted * max(0.6, 1.0 - req.accident_count * 0.1))

    # 신뢰구간 (MAPE 기반)
    mape = _price_meta.get('mape', 20) / 100
    low = int(predicted * (1 - mape))
    high = int(predicted * (1 + mape))

    # 감가상각 곡선
    depreciation = []
    for y in range(6):
        future_age = car_age + y
        future_mileage = req.mileage + y * 15000
        fd = feature_dict.copy()
        fd['car_age'] = future_age
        fd['mileage'] = future_mileage
        fd['annual_mileage'] = future_mileage / (future_age + 0.5)
        fd['year'] = 2026 - future_age
        X_future = np.array([[fd.get(f, 0) for f in _price_features]])
        p = int(max(50, _price_model.predict(X_future)[0]))
        depreciation.append({"year": 2026 + y, "price": p})

    confidence = min(0.95, max(0.5, _price_meta.get('r2', 0.6)))

    return {
        "predicted_price": predicted,
        "price_range_low": low,
        "price_range_high": high,
        "confidence": confidence,
        "defect_adjusted_price": defect_adjusted,
        "defect_discount": defect_discount,
        "depreciation_curve": depreciation,
        "model_type": "ml",
    }


# ── Mock (모델 없을 때 폴백) ──
BRAND_BASE = {
    "현대": 3000, "기아": 2800, "제네시스": 5000,
    "쉐보레": 2500, "르노": 2200, "쌍용": 2000,
    "BMW": 5500, "벤츠": 6000, "아우디": 5000,
    "폭스바겐": 4000, "볼보": 5000, "토요타": 4500,
    "렉서스": 5500, "혼다": 3500, "포르쉐": 9000,
    "테슬라": 5500,
}


def predict_price_mock(req: PriceRequest) -> dict:
    base = BRAND_BASE.get(req.brand, 3000)
    car_age = max(0, 2026 - req.year)
    age_factor = max(0.25, 1.0 - car_age * 0.09)
    mileage_factor = max(0.4, 1.0 - (req.mileage / 10000) * 0.02)
    fuel_adj = {"전기": 1.15, "하이브리드": 1.08, "디젤": 0.97, "가솔린": 1.0, "LPG": 0.85}
    fuel_factor = fuel_adj.get(req.fuel_type, 1.0)
    accident_factor = max(0.6, 1.0 - req.accident_count * 0.12)

    predicted = int(base * age_factor * mileage_factor * fuel_factor * accident_factor)
    predicted = max(100, predicted)

    defect_adjusted = None
    defect_discount = None
    if req.defect_score > 0:
        defect_adjusted = int(predicted * (1 - req.defect_score * 0.003))
        defect_discount = predicted - defect_adjusted

    low = int(predicted * 0.92)
    high = int(predicted * 1.08)

    depreciation = []
    for y in range(6):
        future_age = car_age + y
        future_factor = max(0.25, 1.0 - future_age * 0.09)
        future_mileage = req.mileage + y * 15000
        future_mil_factor = max(0.4, 1.0 - (future_mileage / 10000) * 0.02)
        p = int(base * future_factor * future_mil_factor * fuel_factor * accident_factor)
        depreciation.append({"year": 2026 + y, "price": max(100, p)})

    return {
        "predicted_price": predicted,
        "price_range_low": low,
        "price_range_high": high,
        "confidence": 0.72 if car_age > 8 else (0.80 if car_age > 5 else 0.87),
        "defect_adjusted_price": defect_adjusted,
        "defect_discount": defect_discount,
        "depreciation_curve": depreciation,
        "model_type": "mock",
    }


def _predict(req: PriceRequest) -> dict:
    """ML 모델 있으면 ML, 없으면 mock"""
    if _load_price_model():
        return predict_price_ml(req)
    return predict_price_mock(req)


@router.post("/price", response_model=PriceResponse)
async def predict_price(req: PriceRequest, db: Session = Depends(get_db)):
    result = _predict(req)

    similar_q = (
        db.query(Listing)
        .join(Vehicle)
        .filter(Vehicle.brand == req.brand)
        .filter(Vehicle.year.between(req.year - 2, req.year + 2))
        .filter(Listing.status == "active")
        .limit(3)
        .all()
    )
    result["similar_listings"] = [
        {"title": s.title, "price": s.price, "mileage": s.vehicle.mileage, "year": s.vehicle.year}
        for s in similar_q
    ]
    return PriceResponse(**result)


@router.get("/vehicle/{vehicle_id}", response_model=PriceResponse)
async def predict_vehicle_price(vehicle_id: int, db: Session = Depends(get_db)):
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(404, "차량을 찾을 수 없습니다.")

    req = PriceRequest(
        brand=vehicle.brand,
        model=vehicle.model,
        year=vehicle.year,
        mileage=vehicle.mileage,
        fuel_type=vehicle.fuel_type,
        transmission=vehicle.transmission,
        engine_cc=vehicle.engine_cc or 0,
        region=vehicle.region or "서울",
    )
    result = _predict(req)

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
    result["similar_listings"] = [
        {"title": s.title, "price": s.price, "mileage": s.vehicle.mileage, "year": s.vehicle.year}
        for s in similar_q
    ]
    return PriceResponse(**result)
