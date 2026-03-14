"""판매자 전환/인증 API"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_user
from app.models import User

router = APIRouter(prefix="/api/seller", tags=["seller"])


class SellerUpgradeRequest(BaseModel):
    name: str  # 실명
    phone: str  # 전화번호
    vehicle_registration: str  # 차량등록증 번호 (간이 인증)
    region: str  # 활동 지역


@router.get("/status")
def get_seller_status(user: User = Depends(require_user)):
    return {
        "user_id": user.id,
        "role": user.role,
        "is_verified": user.is_verified,
        "region": user.region,
    }


@router.post("/upgrade")
def upgrade_to_seller(
    data: SellerUpgradeRequest,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    if user.role == "seller" and user.is_verified:
        return {"message": "이미 판매자 인증이 완료되었습니다.", "role": user.role}

    # 간이 인증 (실제로는 본인인증 API + 차량등록증 OCR 등 연동)
    if not data.name.strip():
        raise HTTPException(status_code=400, detail="실명을 입력해주세요.")
    if not data.phone.strip():
        raise HTTPException(status_code=400, detail="전화번호를 입력해주세요.")
    if not data.vehicle_registration.strip():
        raise HTTPException(status_code=400, detail="차량등록증 번호를 입력해주세요.")
    if not data.region.strip():
        raise HTTPException(status_code=400, detail="활동 지역을 선택해주세요.")

    user.role = "seller"
    user.is_verified = True
    user.phone = data.phone
    user.region = data.region
    db.commit()

    return {
        "message": "판매자 인증이 완료되었습니다.",
        "role": user.role,
        "is_verified": user.is_verified,
        "region": user.region,
    }
