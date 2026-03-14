"""AI 차량 요약 API - ChatGPT API를 사용한 차량 특징/장단점 요약"""
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_user
from app.models import Vehicle, Listing, DiagnosisReport, UserReview, User

router = APIRouter(prefix="/api/ai", tags=["ai"])

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


def _build_vehicle_prompt(vehicle: Vehicle, listing: Optional[Listing],
                          diagnosis: Optional[DiagnosisReport],
                          reviews: list[UserReview]) -> str:
    """차량 정보를 기반으로 ChatGPT 프롬프트를 생성"""
    info = f"""차량 정보:
- 브랜드/모델: {vehicle.brand} {vehicle.model}
- 연식: {vehicle.year}년
- 트림: {vehicle.trim or '정보없음'}
- 연료: {vehicle.fuel_type}
- 변속기: {vehicle.transmission}
- 주행거리: {vehicle.mileage:,}km
- 배기량: {vehicle.engine_cc or 0}cc
- 지역: {vehicle.region or '미지정'}
"""
    if listing:
        info += f"- 판매가: {listing.price:,}만원\n"
        if listing.description:
            info += f"- 판매자 설명: {listing.description}\n"

    if diagnosis:
        info += f"""
AI 진단 결과:
- 종합 점수: {diagnosis.overall_score}점
- 외관: {diagnosis.exterior_score}점, 내부: {diagnosis.interior_score}점, 엔진: {diagnosis.engine_score}점
- 사고이력: {diagnosis.accident_history or '정보없음'}
- AI 소견: {diagnosis.report_summary or ''}
"""

    if reviews:
        info += "\n실제 구매/판매 후기:\n"
        for r in reviews[:5]:
            info += f"- [{r.review_type}] (평점 {r.rating}/5): {r.content}\n"

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


@router.get("/vehicle-summary/{vehicle_id}")
def get_vehicle_summary(
    vehicle_id: int,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user),
):
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="차량을 찾을 수 없습니다.")

    listing = db.query(Listing).filter(Listing.vehicle_id == vehicle_id).first()
    diagnosis = db.query(DiagnosisReport).filter(DiagnosisReport.vehicle_id == vehicle_id).first()
    reviews = db.query(UserReview).filter(UserReview.vehicle_id == vehicle_id).all()

    # OpenAI API 사용 (키가 있을 때)
    if OPENAI_API_KEY:
        try:
            import openai
            client = openai.OpenAI(api_key=OPENAI_API_KEY)
            vehicle_info = _build_vehicle_prompt(vehicle, listing, diagnosis, reviews)

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": """당신은 중고차 전문 분석가입니다.
주어진 차량 정보를 바탕으로 구매자에게 유용한 분석을 제공하세요.
반드시 아래 JSON 형식으로만 응답하세요:
{
  "summary": "차량 종합 요약 (2-3문장)",
  "pros": ["장점1", "장점2", ...],
  "cons": ["단점1", "단점2", ...],
  "known_issues": "이 모델의 알려진 고질병이나 주의사항 (없으면 null)",
  "review_summary": "실제 후기 요약 (후기가 있으면 1-2문장, 없으면 null)"
}"""},
                    {"role": "user", "content": vehicle_info},
                ],
                temperature=0.7,
                max_tokens=800,
            )

            import json
            result = json.loads(response.choices[0].message.content)
            result["vehicle_id"] = vehicle.id
            result["vehicle_name"] = f"{vehicle.brand} {vehicle.model} {vehicle.year}"
            result["source"] = "chatgpt"
            return result
        except Exception:
            pass

    # Fallback: 모의 요약
    return _generate_mock_summary(vehicle, listing, diagnosis)
