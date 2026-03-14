"""포인트 시스템 API"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_user
from app.models import User, PointTransaction

router = APIRouter(prefix="/api/points", tags=["points"])


class PointChargeRequest(BaseModel):
    amount: int  # 충전할 포인트 (1000원 = 1000포인트)


class PointUseRequest(BaseModel):
    amount: int
    usage_type: str  # ai_usage, premium_listing
    description: str = ""


@router.get("/balance")
def get_balance(user: User = Depends(require_user)):
    return {"points": user.points, "user_id": user.id}


@router.get("/history")
def get_history(
    page: int = 1,
    size: int = 20,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    q = (
        db.query(PointTransaction)
        .filter(PointTransaction.user_id == user.id)
        .order_by(PointTransaction.created_at.desc())
    )
    total = q.count()
    items = q.offset((page - 1) * size).limit(size).all()
    return {
        "total": total,
        "items": [
            {
                "id": t.id,
                "amount": t.amount,
                "balance_after": t.balance_after,
                "transaction_type": t.transaction_type,
                "description": t.description,
                "created_at": t.created_at.isoformat(),
            }
            for t in items
        ],
    }


@router.post("/charge")
def charge_points(
    req: PointChargeRequest,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    if req.amount < 1000:
        raise HTTPException(status_code=400, detail="최소 1,000포인트부터 충전 가능합니다.")
    if req.amount > 1000000:
        raise HTTPException(status_code=400, detail="1회 최대 1,000,000포인트까지 충전 가능합니다.")

    user.points += req.amount
    tx = PointTransaction(
        user_id=user.id,
        amount=req.amount,
        balance_after=user.points,
        transaction_type="charge",
        description=f"포인트 충전 {req.amount:,}P",
    )
    db.add(tx)
    db.commit()
    return {"points": user.points, "charged": req.amount}


@router.post("/use")
def use_points(
    req: PointUseRequest,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    if req.amount <= 0:
        raise HTTPException(status_code=400, detail="사용 포인트는 1 이상이어야 합니다.")
    if user.points < req.amount:
        raise HTTPException(status_code=400, detail=f"포인트가 부족합니다. 현재: {user.points:,}P")

    ALLOWED_TYPES = {"ai_usage", "premium_listing"}
    if req.usage_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="허용되지 않은 사용 유형입니다.")

    user.points -= req.amount
    tx = PointTransaction(
        user_id=user.id,
        amount=-req.amount,
        balance_after=user.points,
        transaction_type=req.usage_type,
        description=req.description or f"{req.usage_type} 사용",
    )
    db.add(tx)
    db.commit()
    return {"points": user.points, "used": req.amount}
