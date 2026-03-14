"""차량 리뷰/후기 API"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_user, get_current_user
from app.models import Vehicle, UserReview, User

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


class ReviewCreate(BaseModel):
    vehicle_id: int
    rating: int  # 1~5
    content: str
    review_type: str = "buyer"  # buyer or seller


@router.get("/vehicle/{vehicle_id}")
def get_vehicle_reviews(
    vehicle_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="차량을 찾을 수 없습니다.")

    q = (
        db.query(UserReview)
        .filter(UserReview.vehicle_id == vehicle_id)
        .order_by(UserReview.created_at.desc())
    )
    total = q.count()
    reviews = q.offset((page - 1) * size).limit(size).all()

    # 평균 평점 계산
    all_ratings = (
        db.query(UserReview.rating)
        .filter(UserReview.vehicle_id == vehicle_id)
        .all()
    )
    avg_rating = sum(r[0] for r in all_ratings) / len(all_ratings) if all_ratings else 0

    return {
        "total": total,
        "avg_rating": round(avg_rating, 1),
        "reviews": [
            {
                "id": r.id,
                "rating": r.rating,
                "content": r.content,
                "review_type": r.review_type,
                "author_name": r.author.username if r.author else "익명",
                "created_at": r.created_at.isoformat(),
            }
            for r in reviews
        ],
    }


@router.post("/")
def create_review(
    data: ReviewCreate,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    vehicle = db.query(Vehicle).filter(Vehicle.id == data.vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="차량을 찾을 수 없습니다.")

    if not 1 <= data.rating <= 5:
        raise HTTPException(status_code=400, detail="평점은 1~5 사이여야 합니다.")
    if len(data.content.strip()) < 10:
        raise HTTPException(status_code=400, detail="후기는 10자 이상 작성해주세요.")
    if data.review_type not in ("buyer", "seller"):
        raise HTTPException(status_code=400, detail="후기 유형은 buyer 또는 seller만 가능합니다.")

    review = UserReview(
        vehicle_id=data.vehicle_id,
        author_id=user.id,
        rating=data.rating,
        content=data.content,
        review_type=data.review_type,
    )
    db.add(review)
    db.commit()
    db.refresh(review)

    return {
        "id": review.id,
        "rating": review.rating,
        "content": review.content,
        "review_type": review.review_type,
        "author_name": user.username,
        "created_at": review.created_at.isoformat(),
    }


@router.get("/model-summary/{brand}/{model}")
def get_model_review_summary(
    brand: str,
    model: str,
    db: Session = Depends(get_db),
):
    """같은 브랜드/모델의 모든 차량 후기를 종합하여 요약"""
    reviews = (
        db.query(UserReview)
        .join(Vehicle)
        .filter(Vehicle.brand == brand, Vehicle.model == model)
        .all()
    )

    if not reviews:
        return {
            "brand": brand,
            "model": model,
            "total_reviews": 0,
            "avg_rating": 0,
            "summary": f"{brand} {model}에 대한 후기가 아직 없습니다.",
            "common_pros": [],
            "common_cons": [],
        }

    avg = sum(r.rating for r in reviews) / len(reviews)

    # 간단한 키워드 기반 분석
    positive_keywords = ["좋", "만족", "추천", "깨끗", "좋아", "편리", "연비", "넓", "조용"]
    negative_keywords = ["불편", "소음", "고장", "수리", "비싸", "좁", "아쉬", "문제"]

    common_pros = []
    common_cons = []
    for r in reviews:
        for kw in positive_keywords:
            if kw in r.content and kw not in [p.split(":")[0] for p in common_pros]:
                common_pros.append(f"{kw}: \"{r.content[:50]}...\"" if len(r.content) > 50 else f"{kw}: \"{r.content}\"")
        for kw in negative_keywords:
            if kw in r.content and kw not in [c.split(":")[0] for c in common_cons]:
                common_cons.append(f"{kw}: \"{r.content[:50]}...\"" if len(r.content) > 50 else f"{kw}: \"{r.content}\"")

    return {
        "brand": brand,
        "model": model,
        "total_reviews": len(reviews),
        "avg_rating": round(avg, 1),
        "summary": f"{brand} {model} 모델의 실제 이용자 후기 {len(reviews)}건을 분석한 결과, 평균 평점 {avg:.1f}점입니다.",
        "common_pros": common_pros[:5],
        "common_cons": common_cons[:5],
    }
