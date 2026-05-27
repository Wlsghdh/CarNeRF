"""검색 자동완성 + 차량 비교 API"""
import json
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, distinct

from app.dependencies import get_db
from app.models import Vehicle, Listing, DiagnosisReport

router = APIRouter(prefix="/api/search", tags=["search"])


_PARSE_SYSTEM_PROMPT = """당신은 한국 중고차 검색 쿼리 파서입니다. 사용자 자연어를 구조화된 필터 JSON으로만 변환합니다.

스키마(누락 키는 null):
{
  "price_min": 만원 단위 정수 | null,
  "price_max": 만원 단위 정수 | null,
  "year_min": 정수 | null,
  "year_max": 정수 | null,
  "mileage_max": km 단위 정수 | null,
  "brand": "현대" | "기아" | "제네시스" | "BMW" | "벤츠" | "아우디" | ... | null,
  "fuel_type": "가솔린" | "디젤" | "하이브리드" | "전기" | "LPG" | null,
  "keywords": ["의미검색용 키워드 (SUV, 패밀리, 정숙, 장거리 등)"]
}

규칙:
- "2000만원대" → price_min=2000, price_max=2999
- "3천만원 이하" → price_max=3000
- "1500만원~2500만원" → price_min=1500, price_max=2500
- "2020년식 이상" → year_min=2020
- "5만km 이하" → mileage_max=50000
- "10만km 미만" → mileage_max=99999
- "전기차" → fuel_type="전기"
- 명시 안 된 값은 null. 절대 추측·기본값 금지.
- keywords는 차종(SUV/세단/경차), 용도(패밀리/장거리/첫차), 특성(정숙/연비) 위주 1~5개.
- JSON만 출력. 코드블록/설명 금지."""


def _parse_query_with_gpt(query: str) -> dict:
    """자연어 쿼리 → 구조화 필터 dict. 실패 시 빈 dict."""
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return {}
    try:
        import openai
        client = openai.OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _PARSE_SYSTEM_PROMPT},
                {"role": "user", "content": query},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
            max_tokens=200,
        )
        parsed = json.loads(resp.choices[0].message.content)
        return {k: v for k, v in parsed.items() if v not in (None, "", [])}
    except Exception:
        return {}


_MATCH_REASON_SYSTEM = """당신은 한국 중고차 추천 도우미입니다. 사용자의 자연어 쿼리에 대해, 각 차량마다 (1) 적합도 판단(fit) + (2) 한 줄 이유(reason)를 작성합니다.

판단 기준 (fit):
- true: 쿼리의 핵심 의도를 충족 (예: "캠핑용" → 카니발/SUV는 true)
- false: 쿼리와 명백히 어긋남, "부족", "부적합", "어려움" 등 부정 표현이 자연스러운 경우 (예: "캠핑용" → 소형 세단은 false / "9인 가족" → 5인승 세단은 false)
- 애매하면 true (사용자가 판단할 수 있게).

reason 작성 규칙:
- 40자 이내 한국어 평어체.
- 차량명·연식·가격 반복 금지 (UI에 이미 표시됨).
- 쿼리와의 연결 고리를 구체적으로 (예: "9인승 미니밴", "공인연비 17km/L", "정숙성 평 우수").
- 일반 상식 수준 사실만. 트림별 옵션 등 모르는 건 만들지 마세요.
- fit=false인 차량의 reason은 "왜 안 맞는지" 솔직히 적습니다.

응답 형식 (모든 id 빠짐없이 포함):
{"reasons": [{"id": 매물번호, "fit": true|false, "reason": "한 줄"}, ...]}
JSON만 출력."""


def _generate_match_reasons(query: str, results: list) -> dict:
    """원본 쿼리에 대해 각 차량의 매칭 이유 한 줄 생성. {listing_id: reason} dict."""
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key or not results:
        return {}
    try:
        import openai
        client = openai.OpenAI(api_key=api_key)
        vehicles_brief = [
            {
                "id": r["listing_id"],
                "name": f"{r['brand']} {r['model']} {r['year']}년",
                "trim": r.get("trim") or "",
                "price_만원": r["price"],
                "fuel": r["fuel_type"],
                "mileage_km": r["mileage"],
            }
            for r in results
        ]
        user_content = (
            f'사용자 쿼리: "{query}"\n\n'
            f'차량 목록 (JSON):\n{json.dumps(vehicles_brief, ensure_ascii=False, indent=2)}'
        )
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _MATCH_REASON_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=1200,
        )
        data = json.loads(resp.choices[0].message.content)
        reasons = data.get("reasons", [])
        out: dict = {}
        for r in reasons:
            if "id" not in r or "reason" not in r:
                continue
            out[int(r["id"])] = {
                "reason": str(r["reason"]).strip(),
                "fit": bool(r.get("fit", True)),
            }
        return out
    except Exception:
        return {}


def _apply_parsed_filters(q_listing, parsed: dict):
    if parsed.get("price_min") is not None:
        q_listing = q_listing.filter(Listing.price >= parsed["price_min"])
    if parsed.get("price_max") is not None:
        q_listing = q_listing.filter(Listing.price <= parsed["price_max"])
    if parsed.get("year_min") is not None:
        q_listing = q_listing.filter(Vehicle.year >= parsed["year_min"])
    if parsed.get("year_max") is not None:
        q_listing = q_listing.filter(Vehicle.year <= parsed["year_max"])
    if parsed.get("mileage_max") is not None:
        q_listing = q_listing.filter(Vehicle.mileage <= parsed["mileage_max"])
    if parsed.get("brand"):
        q_listing = q_listing.filter(Vehicle.brand == parsed["brand"])
    if parsed.get("fuel_type"):
        q_listing = q_listing.filter(Vehicle.fuel_type == parsed["fuel_type"])
    return q_listing


def _build_result_dict(listing, match=None, score_default=50.0) -> dict:
    v = listing.vehicle
    return {
        "listing_id": listing.id,
        "vehicle_id": listing.vehicle_id,
        "title": listing.title,
        "price": listing.price,
        "brand": v.brand,
        "model": v.model,
        "year": v.year,
        "trim": v.trim,
        "fuel_type": v.fuel_type,
        "mileage": v.mileage,
        "region": v.region,
        "thumbnail_url": v.thumbnail_url,
        "has_3d": v.model_3d_status == "ready",
        "match_score": round(match.score * 100, 1) if match else score_default,
        "match_excerpt": (match.excerpt.strip()[:180].rstrip() + "...") if match and len(match.excerpt.strip()) > 180 else (match.excerpt.strip() if match else ""),
        "match_source": match.excerpt_source if match else "",
        "match_url": match.excerpt_url if match else "",
        "match_title": match.excerpt_title if match else "",
    }


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


@router.get("/semantic")
def semantic_search(
    q: str = Query(..., min_length=2, max_length=200, description="자연어 검색 쿼리"),
    limit: int = Query(12, ge=1, le=24),
    db: Session = Depends(get_db),
):
    """LLM 파싱 + RAG 의미 검색 하이브리드.

    1) GPT-4o-mini로 쿼리를 구조화 필터(가격/연식/연료/주행거리 등)와 키워드로 파싱
    2) 키워드로 Chroma 의미 검색 → 매칭 (brand, model) 후보 + 발췌
    3) 각 후보에 대해 구조화 필터를 만족하는 active listing 조회
    4) 부족분은 구조화 필터만 적용한 listing으로 fallback
    """
    try:
        from app.rag.retriever import semantic_search_vehicles
        from app.rag.sanitize import sanitize_user_text
    except Exception:
        raise HTTPException(status_code=503, detail="RAG 인덱스가 준비되지 않았습니다.")

    # 사용자 쿼리도 prompt injection 키워드 차단 (max_length는 FastAPI Query로 이미 200)
    q = sanitize_user_text(q, max_chars=200)
    parsed = _parse_query_with_gpt(q)
    parse_source = "gpt-4o-mini" if parsed else "none"

    # 의미 검색용 쿼리: 파싱된 키워드 우선, 없으면 원본
    keywords = parsed.get("keywords") or []
    search_query = " ".join(keywords) if keywords else q

    try:
        matches = semantic_search_vehicles(search_query, top_k_chunks=30, max_vehicles=limit * 3)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"검색 중 오류: {e}")

    results = []
    seen_keys: set = set()
    for m in matches:
        if len(results) >= limit:
            break
        q_listing = (
            db.query(Listing)
            .options(joinedload(Listing.vehicle))
            .join(Vehicle)
            .filter(
                Vehicle.brand == m.brand,
                Vehicle.model == m.model,
                Listing.status == "active",
            )
        )
        q_listing = _apply_parsed_filters(q_listing, parsed)
        listing = q_listing.order_by(Listing.created_at.desc()).first()
        if not listing:
            continue
        results.append(_build_result_dict(listing, match=m))
        seen_keys.add((m.brand, m.model))

    # Fallback: 구조화 필터가 있는데 의미 검색 매칭이 부족하면 구조화 필터만으로 채움
    structural_keys = ["price_min", "price_max", "year_min", "year_max",
                       "mileage_max", "brand", "fuel_type"]
    has_structural = any(parsed.get(k) is not None for k in structural_keys)
    if has_structural and len(results) < limit:
        q_fallback = (
            db.query(Listing)
            .options(joinedload(Listing.vehicle))
            .join(Vehicle)
            .filter(Listing.status == "active")
        )
        q_fallback = _apply_parsed_filters(q_fallback, parsed)
        for listing in q_fallback.order_by(Vehicle.year.desc()).all():
            if len(results) >= limit:
                break
            key = (listing.vehicle.brand, listing.vehicle.model)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            results.append(_build_result_dict(listing, match=None, score_default=50.0))

    # 의미 키워드가 없는 쿼리(예: "2000만원대", "2020년 이상")는 차종 적합도 판단이 무의미.
    # 구조 필터로 이미 통과한 결과를 GPT가 차종 매칭 기준으로 잘못 거를 수 있어 스킵.
    has_semantic_intent = bool(keywords)

    if has_semantic_intent:
        # 결과별 매칭 이유 + 적합도 판단 (배치 GPT 호출, 1회)
        reason_map = _generate_match_reasons(q, results)
        filtered: list = []
        excluded: int = 0
        for r in results:
            rd = reason_map.get(r["listing_id"])
            if rd is None:
                # GPT 판단 없음 — 안전하게 통과 (reason 비움)
                r["match_reason"] = ""
                filtered.append(r)
            elif rd["fit"]:
                r["match_reason"] = rd["reason"]
                filtered.append(r)
            else:
                excluded += 1
        results = filtered
    else:
        excluded = 0
        for r in results:
            r["match_reason"] = ""

    # 0건 fallback: 가격/주행거리 조건이 빡빡해 0건이고 의미검색 매칭은 있는 경우,
    # 가격·주행거리 조건만 풀어서 "유사 매물" 후보를 별도 필드로 반환.
    # 프론트는 본 results가 비면 near_results 섹션을 노출하면 됨.
    near_results: list = []
    price_or_mileage_filter = (
        parsed.get("price_min") is not None
        or parsed.get("price_max") is not None
        or parsed.get("mileage_max") is not None
    )
    if not results and matches and price_or_mileage_filter:
        near_parsed = {
            k: v for k, v in parsed.items()
            if k not in ("price_min", "price_max", "mileage_max")
        }
        near_seen: set = set()
        near_limit = max(3, limit // 2)
        for m in matches:
            if len(near_results) >= near_limit:
                break
            if (m.brand, m.model) in near_seen:
                continue
            q_near = (
                db.query(Listing)
                .options(joinedload(Listing.vehicle))
                .join(Vehicle)
                .filter(
                    Vehicle.brand == m.brand,
                    Vehicle.model == m.model,
                    Listing.status == "active",
                )
            )
            q_near = _apply_parsed_filters(q_near, near_parsed)
            listing = q_near.order_by(Listing.created_at.desc()).first()
            if listing:
                near = _build_result_dict(listing, match=m)
                near["match_reason"] = ""
                near_results.append(near)
                near_seen.add((m.brand, m.model))

    return {
        "query": q,
        "method": "hybrid",
        "parsed": parsed,
        "parse_source": parse_source,
        "excluded_unfit": excluded,
        "results": results,
        "near_results": near_results,
    }


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
