"""검색 자동완성 + 차량 비교 API"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, distinct

from app.dependencies import get_db
from app.models import Vehicle, Listing, DiagnosisReport

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("/autocomplete")
def autocomplete(
    q: str = Query(..., min_length=1),
    limit: int = Query(8, ge=1, le=20),
    db: Session = Depends(get_db),
):
    """검색 자동완성 - 브랜드, 모델, 트림을 검색"""
    term = f"%{q}%"
    results = []
    seen = set()

    # 브랜드 매칭
    brands = (
        db.query(Vehicle.brand)
        .filter(Vehicle.brand.ilike(term))
        .distinct()
        .limit(3)
        .all()
    )
    for (brand,) in brands:
        if brand not in seen:
            results.append({"type": "brand", "text": brand, "label": f"{brand} 전체"})
            seen.add(brand)

    # 브랜드+모델 매칭
    models = (
        db.query(Vehicle.brand, Vehicle.model)
        .filter(
            (Vehicle.brand.ilike(term)) |
            (Vehicle.model.ilike(term)) |
            (func.concat(Vehicle.brand, " ", Vehicle.model).ilike(term))
        )
        .distinct()
        .limit(5)
        .all()
    )
    for brand, model in models:
        key = f"{brand} {model}"
        if key not in seen:
            count = (
                db.query(Listing)
                .join(Vehicle)
                .filter(Vehicle.brand == brand, Vehicle.model == model, Listing.status == "active")
                .count()
            )
            results.append({
                "type": "model",
                "text": key,
                "label": f"{brand} {model}",
                "count": count,
            })
            seen.add(key)

    # 매물 제목 매칭
    if len(results) < limit:
        listings = (
            db.query(Listing.title, Listing.id)
            .filter(Listing.title.ilike(term), Listing.status == "active")
            .limit(limit - len(results))
            .all()
        )
        for title, lid in listings:
            if title not in seen:
                results.append({"type": "listing", "text": title, "listing_id": lid})
                seen.add(title)

    return {"results": results[:limit]}


@router.get("/compare")
def compare_vehicles(
    ids: str = Query(..., description="차량 ID 목록 (쉼표 구분, 최대 4대)"),
    db: Session = Depends(get_db),
):
    """차량 비교 - 최대 4대의 차량 스펙/가격/진단 비교"""
    try:
        vehicle_ids = [int(x.strip()) for x in ids.split(",")]
    except ValueError:
        raise HTTPException(status_code=400, detail="유효하지 않은 차량 ID입니다.")

    if len(vehicle_ids) > 4:
        raise HTTPException(status_code=400, detail="최대 4대까지 비교 가능합니다.")
    if len(vehicle_ids) < 2:
        raise HTTPException(status_code=400, detail="2대 이상 선택해주세요.")

    comparisons = []
    for vid in vehicle_ids:
        vehicle = db.query(Vehicle).filter(Vehicle.id == vid).first()
        if not vehicle:
            continue

        listing = db.query(Listing).filter(
            Listing.vehicle_id == vid, Listing.status == "active"
        ).first()

        diagnosis = db.query(DiagnosisReport).filter(
            DiagnosisReport.vehicle_id == vid
        ).first()

        comparisons.append({
            "vehicle": {
                "id": vehicle.id,
                "brand": vehicle.brand,
                "model": vehicle.model,
                "year": vehicle.year,
                "trim": vehicle.trim,
                "fuel_type": vehicle.fuel_type,
                "transmission": vehicle.transmission,
                "mileage": vehicle.mileage,
                "color": vehicle.color,
                "engine_cc": vehicle.engine_cc,
                "region": vehicle.region,
                "thumbnail_url": vehicle.thumbnail_url,
                "has_3d": vehicle.model_3d_status == "ready",
            },
            "listing": {
                "id": listing.id,
                "title": listing.title,
                "price": listing.price,
                "is_negotiable": listing.is_negotiable,
                "view_count": listing.view_count,
            } if listing else None,
            "diagnosis": {
                "overall_score": diagnosis.overall_score,
                "exterior_score": diagnosis.exterior_score,
                "interior_score": diagnosis.interior_score,
                "engine_score": diagnosis.engine_score,
                "accident_history": diagnosis.accident_history,
                "estimated_price_low": diagnosis.estimated_price_low,
                "estimated_price_high": diagnosis.estimated_price_high,
            } if diagnosis else None,
        })

    if len(comparisons) < 2:
        raise HTTPException(status_code=404, detail="비교할 차량이 충분하지 않습니다.")

    # 비교 요약 생성
    prices = [c["listing"]["price"] for c in comparisons if c["listing"]]
    mileages = [c["vehicle"]["mileage"] for c in comparisons]
    scores = [c["diagnosis"]["overall_score"] for c in comparisons if c["diagnosis"]]

    summary = {
        "cheapest": min(comparisons, key=lambda c: c["listing"]["price"] if c["listing"] else float("inf"))["vehicle"]["id"] if prices else None,
        "lowest_mileage": min(comparisons, key=lambda c: c["vehicle"]["mileage"])["vehicle"]["id"],
        "best_condition": max(comparisons, key=lambda c: c["diagnosis"]["overall_score"] if c["diagnosis"] else 0)["vehicle"]["id"] if scores else None,
        "price_range": {"min": min(prices), "max": max(prices)} if prices else None,
    }

    return {"vehicles": comparisons, "summary": summary}


@router.get("/popular-keywords")
def popular_keywords(db: Session = Depends(get_db)):
    """인기 검색 키워드 (브랜드별 매물 수 기준)"""
    brand_counts = (
        db.query(Vehicle.brand, func.count(Listing.id))
        .join(Listing, Listing.vehicle_id == Vehicle.id)
        .filter(Listing.status == "active")
        .group_by(Vehicle.brand)
        .order_by(func.count(Listing.id).desc())
        .limit(10)
        .all()
    )

    return {
        "keywords": [
            {"text": brand, "count": count}
            for brand, count in brand_counts
        ]
    }
