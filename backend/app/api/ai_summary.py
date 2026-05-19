"""AI 차량 요약 API - ChatGPT + RAG + 결함 인식 + DB 캐싱"""
import hashlib
import json
import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_user
from app.models import Vehicle, Listing, DiagnosisReport, UserReview, User, AIAnalysisCache
from app.rag.sanitize import sanitize_user_text, sanitize_review

router = APIRouter(prefix="/api/ai", tags=["ai"])

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# 프롬프트/스키마가 바뀌면 이 값을 올려서 캐시를 일괄 무효화한다.
PROMPT_VERSION = "v12-defects-all-cons-major-2026-05-19"


# 한국 중고차 성능기록부·진단서에 자주 등장하는 전문 용어 → 일반인 풀이 사전.
# system_prompt에 주입해 GPT가 첫 등장 시 괄호로 자동 풀이하게 함.
TERMINOLOGY_GLOSSARY: dict[str, str] = {
    # 외판 부위
    "펜더": "앞바퀴 위 외판",
    "휀더": "앞바퀴 위 외판",
    "쿼터패널": "뒷바퀴 위 측면판",
    "사이드실": "차체 옆 아래 부분",
    "휠하우스": "바퀴 안쪽 공간",
    "대쉬패널": "엔진룸과 실내 격벽",
    # 수리/사고 분류
    "단순교환": "외판만 교체, 사고차 아님",
    "외판교환": "외판만 교체, 뼈대 무관",
    "골격손상": "차체 뼈대 손상, 사고차",
    # 차량 부품·시스템 약어
    "DPF": "디젤 매연 필터",
    "EGR": "배기가스 재순환 장치",
    "CVT": "무단변속기",
    "DCT": "듀얼 클러치 변속기",
    "BSD": "후측방 사각 감지",
    "LDWS": "차선 이탈 경보",
    "ECU": "차량 제어 컴퓨터",
    "SOH": "배터리 잔여 수명",
    # 검사 결과 용어
    "누유": "기름 누출",
    "누수": "냉각수·기름 누출",
    "슬립": "변속기 미끄럼",
    "백래쉬": "기어 사이 유격",
}


def _glossary_for_prompt(text_blob: str) -> str:
    """text_blob에 등장하는 용어만 골라 system_prompt용 미니 사전 문자열로 반환."""
    hits = [(t, g) for t, g in TERMINOLOGY_GLOSSARY.items() if t in text_blob]
    if not hits:
        return ""
    return "\n".join(f"  · {t} = {g}" for t, g in hits)


def _apply_inline_gloss(result: dict) -> dict:
    """ChatGPT 응답 텍스트 필드에서 전문 용어 첫 등장에 괄호 풀이 자동 삽입.

    응답 전체에서 용어당 1회만 풀이. summary → pros → cons → known_issues → review_summary 순회.
    이미 괄호 풀이가 붙어있으면(다음 문자가 '(') 스킵.
    """
    applied: set[str] = set()

    def gloss_text(text: str) -> str:
        if not text:
            return text
        nonlocal applied
        for term, gloss in TERMINOLOGY_GLOSSARY.items():
            if term in applied:
                continue
            idx = text.find(term)
            if idx < 0:
                continue
            end = idx + len(term)
            # 이미 괄호 풀이가 있으면 적용된 것으로 마킹
            if end < len(text) and text[end] == '(':
                applied.add(term)
                continue
            text = text[:end] + f"({gloss})" + text[end:]
            applied.add(term)
        return text

    if isinstance(result.get("summary"), str):
        result["summary"] = gloss_text(result["summary"])
    if isinstance(result.get("pros"), list):
        result["pros"] = [gloss_text(p) for p in result["pros"]]
    if isinstance(result.get("cons"), list):
        result["cons"] = [gloss_text(c) for c in result["cons"]]
    if isinstance(result.get("known_issues"), str):
        result["known_issues"] = gloss_text(result["known_issues"])
    if isinstance(result.get("review_summary"), str):
        result["review_summary"] = gloss_text(result["review_summary"])
    return result


# GPT가 "단점 없음" 등을 표현할 때 빈 배열 대신 ["null"], ["없음"] 같은 placeholder를
# 넣는 경우가 있음. 프론트에 그대로 노출되면 부자연스러우니 후처리로 정리.
_PLACEHOLDER_VALUES = {
    "null", "none", "n/a", "na",
    "없음", "해당없음", "해당 없음", "(없음)", "특이사항 없음",
    "결함 없음", "단점 없음", "특별한 단점 없음", "특별한 단점이 없습니다",
}


def _clean_list_field(items) -> list:
    if not isinstance(items, list):
        return []
    out = []
    for x in items:
        if not isinstance(x, str):
            continue
        s = x.strip()
        if not s:
            continue
        if s.lower() in _PLACEHOLDER_VALUES:
            continue
        out.append(s)
    return out


def _clean_str_field(value):
    if not isinstance(value, str):
        return value
    s = value.strip()
    if not s or s.lower() in _PLACEHOLDER_VALUES:
        return None
    return value


def _sanitize_result(result: dict) -> dict:
    """GPT 응답 / 캐시 hit 결과를 프론트 노출 전 정리.

    - cons/pros/known_issues 리스트의 'null', '없음' 같은 placeholder 제거
    - 빈 cons는 ["특별한 단점은 발견되지 않았습니다"] 라는 사용자 친화 메시지로 채움
      (장점만 있는 차량인데 cons가 비면 UI가 어색해지므로)
    """
    if not isinstance(result, dict):
        return result
    result["pros"] = _clean_list_field(result.get("pros"))
    cons = _clean_list_field(result.get("cons"))
    if not cons:
        # 결함이 없거나 GPT가 단점을 못 찾은 경우, 명시적 메시지 1건 노출
        cons = ["특별한 단점은 발견되지 않았습니다."]
    result["cons"] = cons
    if "known_issues" in result:
        result["known_issues"] = _clean_str_field(result["known_issues"])
    if "review_summary" in result:
        result["review_summary"] = _clean_str_field(result["review_summary"])
    return result


_NO_CONS_MSG = "특별한 단점은 발견되지 않았습니다."


_SEVERE_ACCIDENT_KEYWORDS = ("골격손상", "전손", "침수", "인사사고", "프레임", "사고차")


def _augment_pros(result: dict, vehicle: Vehicle,
                  listing: Optional[Listing],
                  db: Session) -> dict:
    """동급 시세 대비 매물가가 저렴하면 pros 1줄 자동 보충.

    내부 거래 데이터(TransactionHistory)의 동일 brand+model 평균을 기준으로,
    매물가가 7% 이상 저렴하면 "동급 시세 대비 저렴한 가격" 추가.
    GPT가 이미 가격 관련 장점을 넣었으면 중복 추가하지 않는다.
    """
    if not isinstance(result, dict) or not listing or not vehicle:
        return result

    pros = list(result.get("pros") or [])

    def already_has(keywords: tuple[str, ...]) -> bool:
        return any(
            any(k in p for k in keywords)
            for p in pros if isinstance(p, str)
        )

    if already_has(("가격", "저렴", "가성비", "시세")):
        return result

    try:
        from app.api.market_price import _get_internal_stats
        stats = _get_internal_stats(db, vehicle.brand, vehicle.model)
    except Exception:
        stats = None

    if not stats or not stats.get("avg_price") or stats.get("count", 0) < 3:
        return result

    avg = stats["avg_price"]
    if listing.price <= avg * 0.93:
        discount_pct = round((1 - listing.price / avg) * 100)
        pros.append(f"동급 시세 평균보다 {discount_pct}% 저렴한 가격")
        result["pros"] = pros[:6]

    return result


def _augment_cons(result: dict, vehicle: Vehicle,
                  listing: Optional[Listing],
                  diagnosis: Optional[DiagnosisReport]) -> dict:
    """안전망 후처리 — GPT가 빠뜨릴 수 없는 **중대 사고**만 강제 보충.

    단순교환·연식·주행거리 등은 GPT 판단에 맡긴다 (system prompt가 처리).
    GPT 응답에 이미 비슷한 키워드가 있으면 중복 추가하지 않는다.
    """
    if not isinstance(result, dict):
        return result

    cons = list(result.get("cons") or [])
    cons = [c for c in cons if c != _NO_CONS_MSG]

    def already_has(keywords: tuple[str, ...]) -> bool:
        return any(
            any(k in c for k in keywords)
            for c in cons if isinstance(c, str)
        )

    additions: list[str] = []

    # 중대 사고만 강제 — 골격손상·전손·침수·인사사고 등
    if diagnosis and diagnosis.accident_history:
        acc = diagnosis.accident_history.strip()
        is_severe = any(kw in acc for kw in _SEVERE_ACCIDENT_KEYWORDS)
        if is_severe and not already_has(_SEVERE_ACCIDENT_KEYWORDS):
            additions.append(f"{acc} 이력")

    cons.extend(additions)
    if not cons:
        cons = [_NO_CONS_MSG]
    result["cons"] = cons
    return result


def _retrieve_review_excerpts(brand: str, model: str, k: int = 5) -> tuple[str, list[dict]]:
    """RAG로 차종별 리뷰 청크 검색.

    Returns:
        (excerpts_text, sources): 발췌 텍스트와 출처 메타 리스트.
        RAG 모듈/Chroma 미준비 시 ("", []) 반환 (graceful degradation).
    """
    try:
        from app.rag.retriever import retrieve, get_sources
    except Exception:
        return "", []
    try:
        chunks = retrieve(brand=brand, model=model, k=k)
    except Exception:
        return "", []
    if not chunks:
        return "", []
    excerpts = []
    for i, c in enumerate(chunks, 1):
        excerpts.append(f"[발췌{i}] ({c.title} — {c.source})\n{c.text}")
    return "\n\n".join(excerpts), get_sources(chunks)


def _get_defect_findings(vehicle: Vehicle) -> dict:
    """차량 결함 정보 조회. defect.py의 resolve_defects 재사용."""
    try:
        from app.api.defect import resolve_defects
    except Exception:
        return {"defect_count": 0, "defects": [], "total_defect_score": 0, "severity_level": "양호"}
    try:
        return resolve_defects(vehicle.id, vehicle)
    except Exception:
        return {"defect_count": 0, "defects": [], "total_defect_score": 0, "severity_level": "양호"}


def _retrieve_defect_explanations_for(defects: dict, max_total: int = 6) -> tuple[str, list[dict]]:
    """발견된 각 결함 종류별로 일반인용 풀이 청크 retrieval.

    동일 종류 결함이 여러 개여도 한 번만 검색. 최대 max_total건의 풀이 발췌 반환.
    Returns: (excerpts_text, sources_list)
    """
    try:
        from app.rag.retriever import retrieve_defect_explanations
    except Exception:
        return "", []

    seen_types = set()
    all_chunks = []
    for d in defects.get("defects", []):
        kind = d.get("type_kr") or d.get("type") or "결함"
        severity = d.get("severity", "")
        key = (kind, severity)
        if key in seen_types:
            continue
        seen_types.add(key)
        try:
            chunks = retrieve_defect_explanations(kind, severity, k=2)
        except Exception:
            chunks = []
        for c in chunks:
            all_chunks.append({
                "for_defect": kind,
                "severity": severity,
                "chunk": c,
            })
        if len(all_chunks) >= max_total:
            break

    all_chunks = all_chunks[:max_total]
    if not all_chunks:
        return "", []

    excerpts = []
    for i, item in enumerate(all_chunks, 1):
        c = item["chunk"]
        excerpts.append(
            f"[결함풀이{i}] (결함 종류: {item['for_defect']}, 출처: {c.title} — {c.source})\n{c.text}"
        )
    seen_urls = set()
    sources_unique = []
    for item in all_chunks:
        c = item["chunk"]
        if c.url in seen_urls:
            continue
        seen_urls.add(c.url)
        sources_unique.append({"url": c.url, "title": c.title, "source": c.source, "kind": "defect_guide"})
    return "\n\n".join(excerpts), sources_unique


# (결함 종류, 심각도) → (예상 수리비 만원 범위, 안전 영향) 매핑
# 외관 결함은 안전 영향 없음을 명시, 부식만 구조 영향 가능성 언급
_REPAIR_COST_MAP = {
    ("scratch", "경미"):     ("5~15만원",   "안전 문제는 없음 — 시각적 손상"),
    ("scratch", "중간"):     ("20~40만원",  "안전 문제는 없음 — 도색 복원 권장"),
    ("scratch", "심각"):     ("50~100만원", "안전 문제는 없음 — 판금+도색 필요"),
    ("dent", "경미"):        ("10~20만원",  "안전 문제는 없음 — 덴트 복원(PDR) 가능"),
    ("dent", "중간"):        ("30~60만원",  "안전 문제는 없음 — 판금 필요"),
    ("dent", "심각"):        ("80~150만원", "구조 점검 권장 — 강한 충격 흔적 가능성"),
    ("paint", "경미"):       ("10~25만원",  "안전 문제는 없음 — 부분 도색"),
    ("paint", "중간"):       ("30~70만원",  "안전 문제는 없음 — 패널 도색"),
    ("paint", "심각"):       ("80~200만원", "안전 문제는 없음 — 다수 패널 도색"),
    ("corrosion", "경미"):   ("15~30만원",  "장기 부식 진행 가능 — 방청 처리 권장"),
    ("corrosion", "중간"):   ("50~100만원", "구조 점검 권장 — 부식 부위 확장 가능"),
    ("corrosion", "심각"):   ("150만원+",   "정밀 점검 필수 — 차체 안전 영향 가능"),
}


def _annotate_defect(defect: dict) -> dict:
    """결함 dict에 예상 수리비·안전 영향 추가 (in-place 아닌 새 dict)."""
    dtype = (defect.get("type") or "").lower()
    severity = defect.get("severity", "")
    key_candidates = [(dtype, severity)]
    if "scratch" in dtype or "스크래치" in (defect.get("type_kr") or ""):
        key_candidates.append(("scratch", severity))
    if "dent" in dtype or "덴트" in (defect.get("type_kr") or ""):
        key_candidates.append(("dent", severity))
    if "paint" in dtype or "도색" in (defect.get("type_kr") or ""):
        key_candidates.append(("paint", severity))
    if "corrosion" in dtype or "부식" in (defect.get("type_kr") or ""):
        key_candidates.append(("corrosion", severity))

    cost, safety = None, None
    for k in key_candidates:
        if k in _REPAIR_COST_MAP:
            cost, safety = _REPAIR_COST_MAP[k]
            break
    out = dict(defect)
    if cost:
        out["estimated_repair_cost"] = cost
        out["safety_note"] = safety
    return out


def _grade_from_score(score: float) -> str:
    """진단 점수 → 일반인 등급."""
    if score >= 90:  return "우수"
    if score >= 80:  return "양호"
    if score >= 70:  return "보통"
    if score >= 60:  return "주의"
    return "미흡"


def _build_vehicle_prompt(vehicle: Vehicle, listing: Optional[Listing],
                          diagnosis: Optional[DiagnosisReport],
                          reviews: list[UserReview],
                          defects: Optional[dict] = None) -> str:
    """차량 정보를 기반으로 ChatGPT 프롬프트를 생성"""
    year_age = 2026 - vehicle.year
    info = f"""━━━ 이 차량 핵심 정보 (개별 매물) ━━━
- 브랜드/모델: {vehicle.brand} {vehicle.model} {vehicle.year}년식 ({year_age}년 경과)
- 트림: {vehicle.trim or '정보없음'}
- 연료/변속기: {vehicle.fuel_type} / {vehicle.transmission}
- 주행거리: {vehicle.mileage:,}km (연평균 {vehicle.mileage // max(year_age, 1):,}km)
- 배기량: {vehicle.engine_cc or 0}cc
- 지역: {vehicle.region or '미지정'}
"""
    if listing:
        info += f"- 판매가: {listing.price:,}만원\n"
        if listing.description:
            info += f"- 판매자 설명: {sanitize_user_text(listing.description)}\n"

    if diagnosis:
        info += f"""
━━━ 이 차량 AI 진단 결과 ━━━
- 종합: {diagnosis.overall_score}점 → 등급 {_grade_from_score(diagnosis.overall_score)}
- 외관: {diagnosis.exterior_score}점 ({_grade_from_score(diagnosis.exterior_score)})
- 내부: {diagnosis.interior_score}점 ({_grade_from_score(diagnosis.interior_score)})
- 엔진: {diagnosis.engine_score}점 ({_grade_from_score(diagnosis.engine_score)})
- 사고이력: {diagnosis.accident_history or '정보없음'}
- AI 소견: {diagnosis.report_summary or '(없음)'}
"""

    if defects and defects.get("defect_count", 0) > 0:
        info += f"""
━━━ 이 차량 외관 결함 (YOLOv8 탐지) ━━━
- 결함 점수: {defects.get('total_defect_score', 0)}점 / 등급: {defects.get('severity_level', '양호')}
- 발견 결함 {defects.get('defect_count', 0)}건 (예상 수리비·안전 영향 포함):
"""
        for i, d in enumerate(defects.get("defects", [])[:10], 1):
            ann = _annotate_defect(d)
            sev = ann.get("severity", "정보없음")
            kind = ann.get("type_kr") or ann.get("type") or "결함"
            conf = ann.get("confidence", 0)
            desc = sanitize_user_text(ann.get("description") or "", max_chars=200)
            cost = ann.get("estimated_repair_cost") or "추정 어려움"
            safety = ann.get("safety_note") or ""
            info += (f"  {i}) {kind} ({sev}, 신뢰도 {int(conf*100)}%) — {desc}\n"
                     f"     · 예상 수리비: {cost}\n"
                     f"     · 안전 영향: {safety}\n")

    if reviews:
        info += "\n━━━ 이 차량 실 사용자 후기 ━━━\n"
        for r in reviews[:5]:
            info += f"- [{r.review_type}] (평점 {r.rating}/5): {sanitize_review(r.content)}\n"

    return info


def _generate_mock_summary(vehicle: Vehicle, listing: Optional[Listing],
                           diagnosis: Optional[DiagnosisReport]) -> dict:
    """OpenAI API 키가 없을 때 사용하는 모의 요약"""
    year_age = 2026 - vehicle.year
    mileage_per_year = vehicle.mileage / max(year_age, 1)

    pros = []
    cons = []

    # 연식 기반
    if year_age <= 2:
        pros.append(f"최신 {vehicle.year}년식으로 최신 안전사양 및 편의사양 탑재")
    elif year_age <= 4:
        pros.append(f"{vehicle.year}년식으로 적정 연식, 감가상각 대비 가성비 우수")
    else:
        cons.append(f"{year_age}년 경과 차량으로 주요 소모품 교체 시기 확인 필요")

    # 주행거리 기반
    if mileage_per_year < 15000:
        pros.append(f"연평균 {mileage_per_year:,.0f}km 주행으로 적은 주행거리")
    elif mileage_per_year > 25000:
        cons.append(f"연평균 {mileage_per_year:,.0f}km로 다소 높은 주행거리")

    # 연료 기반
    fuel_info = {
        "전기": ("유지비가 낮고 친환경", "충전 인프라 확인 필요, 배터리 노화 점검 권장"),
        "하이브리드": ("도심 연비 우수, 친환경", "하이브리드 배터리 상태 점검 권장"),
        "디젤": ("고속도로 연비 우수, 토크 높음", "DPF 및 요소수 관리 필요"),
        "가솔린": ("정숙성 우수, 유지보수 편리", "도심 연비 상대적 열위"),
    }
    if vehicle.fuel_type in fuel_info:
        pros.append(fuel_info[vehicle.fuel_type][0])
        cons.append(fuel_info[vehicle.fuel_type][1])

    # 브랜드 기반
    brand_info = {
        "현대": "현대차 공식 서비스 네트워크 전국 최다",
        "기아": "기아 공식 A/S 네트워크 광범위",
        "제네시스": "제네시스 전용 서비스센터, 프리미엄 A/S",
        "BMW": "수입차 특유의 주행 성능과 고급감",
        "쉐보레": "미국차 특유의 넉넉한 실내공간",
    }
    if vehicle.brand in brand_info:
        pros.append(brand_info[vehicle.brand])

    # 진단 기반
    if diagnosis:
        if diagnosis.overall_score >= 90:
            pros.append(f"AI 진단 종합 {diagnosis.overall_score}점으로 매우 우수한 상태")
        elif diagnosis.overall_score >= 80:
            pros.append(f"AI 진단 종합 {diagnosis.overall_score}점으로 양호한 상태")
        else:
            cons.append(f"AI 진단 종합 {diagnosis.overall_score}점으로 일부 주의 필요")

        if diagnosis.accident_history and "무사고" in diagnosis.accident_history:
            pros.append("무사고 차량으로 확인")
        elif diagnosis.accident_history:
            cons.append(f"사고이력: {diagnosis.accident_history}")

    # 가격 기반
    if listing and diagnosis:
        mid_price = (diagnosis.estimated_price_low + diagnosis.estimated_price_high) / 2
        if listing.price < mid_price * 0.95:
            pros.append("시세 대비 저렴한 가격으로 가성비 우수")
        elif listing.price > mid_price * 1.05:
            cons.append("시세 대비 다소 높은 가격, 네고 여부 확인 권장")

    # 고질병 정보 (모델별)
    known_issues = {
        ("현대", "그랜저"): "연식에 따라 미션 진동 또는 공조 소음이 보고된 사례가 있으니 시승 시 확인하세요.",
        ("현대", "투싼"): "디젤 모델은 DPF 재생 주기를 확인하시고, 단거리 주행이 많았다면 점검을 권장합니다.",
        ("현대", "아반떼"): "CVT 변속기 모델은 고속 주행 시 엔진 소음이 있을 수 있습니다.",
        ("기아", "K5"): "일부 연식에서 전자장비(AVN) 오류 사례가 있으니 최신 업데이트 여부를 확인하세요.",
        ("기아", "쏘렌토"): "디젤 모델 고압펌프 관련 리콜 이력을 확인하시기 바랍니다.",
        ("기아", "EV6"): "충전 시 HPC 호환성 이슈가 일부 보고되었으나 소프트웨어 업데이트로 해결됩니다.",
        ("제네시스", "G80"): "에어서스펜션 장착 모델은 장기 사용 시 에어 누출 점검이 필요합니다.",
        ("BMW", "520i"): "냉각수 누수 및 오일 소모량 점검을 권장합니다. B48 엔진 특성상 정기적 관리가 중요합니다.",
    }
    issue = known_issues.get((vehicle.brand, vehicle.model))

    summary = f"""{vehicle.brand} {vehicle.model} {vehicle.year}년식은 """
    if diagnosis and diagnosis.overall_score >= 85:
        summary += "전반적으로 상태가 우수한 차량입니다. "
    else:
        summary += "합리적인 선택이 될 수 있는 차량입니다. "

    if listing:
        summary += f"현재 {listing.price:,}만원에 판매 중이며, "
    if diagnosis:
        summary += f"AI 진단 결과 종합 {diagnosis.overall_score}점을 기록했습니다. "

    return {
        "vehicle_id": vehicle.id,
        "vehicle_name": f"{vehicle.brand} {vehicle.model} {vehicle.year}",
        "summary": summary,
        "pros": pros[:5],
        "cons": cons[:5],
        "known_issues": issue,
        "review_summary": None,
        "source": "mock",
    }


def _compute_input_hash(vehicle: Vehicle, listing: Optional[Listing],
                        diagnosis: Optional[DiagnosisReport],
                        reviews: list[UserReview], defects: dict,
                        sources: list[dict]) -> str:
    """입력 상태가 변하면 캐시 무효화 — vehicle/listing/diagnosis/defects/reviews/sources/prompt_version 직렬화 후 SHA256."""
    payload = {
        "_prompt_version": PROMPT_VERSION,
        "v": {
            "brand": vehicle.brand, "model": vehicle.model, "year": vehicle.year,
            "trim": vehicle.trim, "fuel": vehicle.fuel_type, "mileage": vehicle.mileage,
            "engine_cc": vehicle.engine_cc, "transmission": vehicle.transmission,
        },
        "l": {"price": listing.price, "desc": listing.description} if listing else None,
        "d": {
            "overall": diagnosis.overall_score, "ext": diagnosis.exterior_score,
            "int": diagnosis.interior_score, "eng": diagnosis.engine_score,
            "acc": diagnosis.accident_history, "summary": diagnosis.report_summary,
        } if diagnosis else None,
        "def": {
            "count": defects.get("defect_count", 0),
            "score": defects.get("total_defect_score", 0),
            "level": defects.get("severity_level", ""),
            "items": [
                {"type": d.get("type_kr") or d.get("type"), "sev": d.get("severity"),
                 "conf": round(d.get("confidence", 0), 2), "desc": d.get("description")}
                for d in defects.get("defects", [])[:10]
            ],
        },
        "r": [{"rating": r.rating, "content": r.content, "type": r.review_type} for r in reviews[:5]],
        "src": [{"url": s.get("url"), "title": s.get("title")} for s in sources],
    }
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


@router.get("/vehicle-summary/{vehicle_id}")
def get_vehicle_summary(
    vehicle_id: int,
    force: bool = Query(False, description="True면 캐시 무시하고 ChatGPT 재호출"),
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user),
):
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="차량을 찾을 수 없습니다.")

    listing = db.query(Listing).filter(Listing.vehicle_id == vehicle_id).first()
    diagnosis = db.query(DiagnosisReport).filter(DiagnosisReport.vehicle_id == vehicle_id).first()
    reviews = db.query(UserReview).filter(UserReview.vehicle_id == vehicle_id).all()

    # RAG + 결함 (캐시 hit 시에도 재계산 필요 — hash 비교용)
    excerpts, sources = _retrieve_review_excerpts(vehicle.brand, vehicle.model, k=5)
    defects = _get_defect_findings(vehicle)
    defect_excerpts, defect_sources = _retrieve_defect_explanations_for(defects)
    input_hash = _compute_input_hash(vehicle, listing, diagnosis, reviews, defects, sources + defect_sources)

    # 캐시 조회 (force=True면 무시)
    cache_row = db.query(AIAnalysisCache).filter(AIAnalysisCache.vehicle_id == vehicle_id).first()
    if cache_row and cache_row.input_hash == input_hash and not force:
        try:
            cached = json.loads(cache_row.data_json)
            cached["cached"] = True
            cached["generated_at"] = cache_row.generated_at.isoformat() if cache_row.generated_at else None
            cached = _sanitize_result(cached)
            cached = _augment_cons(cached, vehicle, listing, diagnosis)
            cached = _augment_pros(cached, vehicle, listing, db)
            return cached
        except Exception:
            pass  # 캐시 손상 시 그냥 새로 생성

    # OpenAI API 사용 (키가 있을 때)
    if OPENAI_API_KEY:
        try:
            import openai
            client = openai.OpenAI(api_key=OPENAI_API_KEY)
            vehicle_info = _build_vehicle_prompt(vehicle, listing, diagnosis, reviews, defects)

            system_prompt = (
                "당신은 비전문가 구매자에게 **이 개별 매물**을 설명하는 분석가입니다.\n"
                "당신의 임무는 모델 마케팅이 아니라, '이 차량의 진단 점수·결함·메타'를 일반인 언어로 풀어 쓰는 것입니다.\n\n"

                "【summary 작성 규칙 — 반드시 4문장, 아래 순서 그대로】\n"
                "  ① **이 차량 메타**: '이 차량은 [브랜드 모델 연식], [경과년수]년 경과, 주행거리 [N]km, [사고이력]입니다.'\n"
                "  ② **진단 등급 풀이**: 'AI 진단은 [전반 등급]으로, 외관 [등급]·내부 [등급]·엔진 [등급]입니다.' (점수 숫자 X)\n"
                "  ③ **결함 또는 시세 관찰**:\n"
                "       - 결함 N건 있으면: '외관에서 [부위] [종류] 등 N건이 발견되어 [총 수리비 추정]이 추가로 들 수 있습니다.'\n"
                "       - 결함 없으면: '외관 결함은 발견되지 않았으며, 현재 매물가는 [N]만원입니다.'\n"
                "  ④ **권고**: '주행거리·진단·결함을 종합하면 [사도 좋다/주의 필요/네고 여지]'\n\n"

                "【summary에서 절대 쓰지 말 것 — 위반 시 무효】\n"
                "  ✘ 모델 일반론: '가족용', '패밀리카', '스포티', '정숙성', '디자인이 좋은', '고속 연비 우수' 등\n"
                "  ✘ 카탈로그·마케팅 표현: '안정적인 주행 성능', '넓은 실내'\n"
                "  ✘ 추상적 호감 표현: '매력적', '인기 모델'\n"
                "  → 이런 모델 평가는 **review_summary**나 **known_issues**에만 사용하세요.\n\n"

                "【pros 규칙】 이 차량 메타·진단 결과 기반만 (예: '연식 대비 낮은 주행거리', '무사고', '진단 우수 등급')\n"
                "【cons 규칙 — 외관 결함 전부 + 구매에 큰 영향 줄 약점만】\n"
                "  cons는 **이 차량 구매 결정에 영향을 줄 만한 약점**입니다.\n\n"
                "  ▶ **① 외관 결함 (YOLOv8 탐지)** — 입력의 결함 N건은 **갯수와 무관하게 전부 1줄씩 cons에 포함**.\n"
                "    형식: `[부위] [결함 종류]` 예: '좌측 앞 도어 스크래치', '후면 테일게이트 미세 덴트'\n"
                "    경미한 결함도 빼지 않음. 누락 금지.\n\n"
                "  ▶ **② 비결함 약점** — 아래 카테고리를 점검하되, **'구매를 망설일 만큼 큰 문제'만 추가**:\n"
                "    - 사고/수리 이력: 골격손상·전손·인사사고 등 **중대 사고만 cons에 포함**. 단순교환·외판교환 같은 가벼운 이력은 cons에 넣지 말 것 (summary 첫 문장에 사실로만 언급).\n"
                "    - 연식: **15년 이상 경과**만. 5~10년대는 일반적이라 cons 제외.\n"
                "    - 누적 주행거리: **15만km 이상**만. 10만km대도 가벼운 차종은 일반적이라 제외.\n"
                "    - AI 진단 등급: '주의' 이하 항목만 cons (양호·우수는 제외).\n"
                "    - 시세: 동급 시세 대비 **명확히 비싼 경우만** (애매하면 제외).\n\n"
                "  ▶ **형식·금지**\n"
                "    - 각 줄 한 가지 약점, 25자 이내, 짧고 명사형.\n"
                "    - 금지: 수리비 숫자, 안전영향, 심각도 라벨, '[참고]' 코멘트.\n"
                "    - 모든 카테고리에 해당사항 없으면 빈 배열 `[]`. **'null'·'없음' 같은 placeholder 금지**.\n"
                "【known_issues】 같은 차종 고질병 (RAG 발췌 근거). 발췌에 없으면 null.\n"
                "【review_summary】 같은 차종 구매자 평 1~2문장. 발췌 근거.\n\n"

                "【표현 규칙】\n"
                "  - 점수 숫자 금지 → '우수/양호/보통/주의/미흡' 등급 한국어로만\n"
                "  - 전문 용어는 응답 본문에서 **첫 등장 시 괄호로 풀어쓰기**. 두 번째부터는 풀이 생략.\n"
                "    예: '단순교환(차체 뼈대 아닌 외판만 교체)', '쿼터패널(뒷바퀴 위 측면판)', 'DPF(디젤 매연 필터)'\n\n"
            )
            # 입력에 실제로 등장하는 용어만 사전으로 주입
            input_blob = vehicle_info + (excerpts or "") + (defect_excerpts or "")
            gloss = _glossary_for_prompt(input_blob)
            if gloss:
                system_prompt += (
                    "━━━ 🔴 매우 중요: 전문 용어 자동 풀이 (반드시 지킬 것) ━━━\n"
                    "아래 용어가 응답(summary/pros/cons/known_issues/review_summary)에 등장할 때 "
                    "**처음 한 번만 반드시** 괄호 풀이를 붙이세요. 일반인 구매자가 이해할 수 있게 하기 위함입니다.\n\n"
                    f"{gloss}\n\n"
                    "✅ 올바른 예:\n"
                    "  - '단순교환(차체 뼈대가 아닌 외판만 교체된 가벼운 수리) 1회 이력이 있습니다.'\n"
                    "  - '좌측 펜더(앞바퀴 위 외판) 도색 흔적이 있습니다.'\n"
                    "  - 'DPF(디젤 매연 필터) 클리닝 권장.'\n"
                    "❌ 잘못된 예 (괄호 풀이 누락):\n"
                    "  - '단순교환 1회 이력이 있습니다.'  ← 첫 등장인데 풀이 없음\n"
                    "  - '좌측 펜더 도색 흔적'  ← 풀이 없음\n\n"
                    "두 번째 등장부터는 풀이 생략 OK.\n\n"
                )
            if excerpts:
                system_prompt += (
                    "[관련 리뷰 발췌]는 **같은 차종**에 대한 외부 매체 리뷰입니다.\n"
                    "known_issues와 review_summary 작성 시 이 발췌를 근거로 하고, 발췌에 없는 고질병은 추측하지 마세요.\n"
                    "이 차량 개별 분석(summary/pros/cons)에는 발췌를 참고만 하고, 차량 메타·진단·결함을 우선 반영하세요.\n\n"
                )

            if defects.get("defect_count", 0) > 0:
                system_prompt += (
                    "[이 차량 외관 결함]이 포함되어 있습니다. 각 결함은 cons에 **'부위 + 결함 종류'만** 짧게 적으세요. "
                    "수리비·안전영향·심각도·[참고:] 등 일체 금지. 그것들은 summary 셋째 문장에서 총합으로만 다룹니다.\n\n"
                )

            system_prompt += """반드시 아래 JSON 형식으로만 응답하세요. 모든 값은 한국어 자연어:
{
  "summary": "이 차량 컨텍스트로 시작하는 3~4문장 종합 요약 + 구매 권고",
  "pros": ["이 차량의 강점들 (3~5개, 차량 메타·진단 우선)"],
  "cons": ["이 차량의 약점들 (결함은 부위·수리비·안전영향 포함, 3~5개)"],
  "known_issues": "같은 차종의 알려진 고질병 (없으면 null)",
  "review_summary": "같은 차종 구매자들의 평 1~2문장 (없으면 null)"
}"""

            user_content = vehicle_info
            if excerpts:
                user_content += f"\n\n[관련 리뷰 발췌 — 같은 차종]\n{excerpts}"
            if defect_excerpts:
                user_content += f"\n\n[결함 풀이 발췌 — 검수/수리 가이드]\n{defect_excerpts}"

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.7,
                max_tokens=800,
            )

            result = json.loads(response.choices[0].message.content)
            # 전문 용어 자동 풀이 — GPT가 빼먹은 괄호 풀이를 결정론적으로 삽입
            result = _apply_inline_gloss(result)
            result = _sanitize_result(result)
            result = _augment_cons(result, vehicle, listing, diagnosis)
            result = _augment_pros(result, vehicle, listing, db)
            result["vehicle_id"] = vehicle.id
            result["vehicle_name"] = f"{vehicle.brand} {vehicle.model} {vehicle.year}"
            result["source"] = "chatgpt+rag" if (excerpts or defect_excerpts) else "chatgpt"
            result["sources"] = sources
            result["defect_sources"] = defect_sources
            result["rag_used"] = bool(excerpts)
            result["defect_rag_used"] = bool(defect_excerpts)
            result["defect_count"] = defects.get("defect_count", 0)
            result["cached"] = False

            # 캐시 upsert
            now = datetime.utcnow()
            if cache_row:
                cache_row.data_json = json.dumps(result, ensure_ascii=False)
                cache_row.input_hash = input_hash
                cache_row.source = result["source"]
                cache_row.generated_at = now
            else:
                db.add(AIAnalysisCache(
                    vehicle_id=vehicle_id,
                    data_json=json.dumps(result, ensure_ascii=False),
                    input_hash=input_hash,
                    source=result["source"],
                    generated_at=now,
                ))
            db.commit()
            result["generated_at"] = now.isoformat()
            return result
        except Exception:
            pass

    # Fallback: 모의 요약 (sources 스키마 일관성 유지, 캐시는 저장 안 함)
    result = _generate_mock_summary(vehicle, listing, diagnosis)
    result["sources"] = sources
    result["defect_sources"] = defect_sources
    result["rag_used"] = bool(excerpts)
    result["defect_rag_used"] = bool(defect_excerpts)
    result["defect_count"] = defects.get("defect_count", 0)
    result["cached"] = False
    result = _sanitize_result(result)
    result = _augment_cons(result, vehicle, listing, diagnosis)
    result = _augment_pros(result, vehicle, listing, db)
    return result
