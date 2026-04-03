from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from app.dependencies import get_db, hash_password, verify_password, create_access_token, require_user
from app.models import User, Listing, Vehicle, LoginHistory
from app.schemas import UserCreate, UserLogin, UserOut, Token

import re

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserOut)
def register(data: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="이미 등록된 이메일입니다.")
    user = User(
        email=data.email,
        username=data.username,
        hashed_password=hash_password(data.password),
        phone=data.phone,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _detect_device(ua: str) -> str:
    """User-Agent에서 기기 유형을 추출한다."""
    ua_lower = ua.lower() if ua else ""
    if any(k in ua_lower for k in ["iphone", "android", "mobile"]):
        return "mobile"
    elif any(k in ua_lower for k in ["ipad", "tablet"]):
        return "tablet"
    return "desktop"


def _get_browser(ua: str) -> str:
    """User-Agent에서 브라우저를 추출한다."""
    if not ua:
        return "unknown"
    if "Chrome" in ua and "Edg" in ua:
        return "Edge"
    elif "Chrome" in ua:
        return "Chrome"
    elif "Firefox" in ua:
        return "Firefox"
    elif "Safari" in ua:
        return "Safari"
    return "other"


@router.post("/login")
def login(data: UserLogin, request: Request, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()

    # 로그인 실패 기록
    if not user or not verify_password(data.password, user.hashed_password):
        if user:
            ip = request.client.host if request.client else None
            ua = request.headers.get("user-agent", "")
            db.add(LoginHistory(
                user_id=user.id,
                ip_address=ip,
                user_agent=ua[:500],
                device_type=_detect_device(ua),
                success=False,
            ))
            db.commit()
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다.")

    # 로그인 성공 기록
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent", "")
    db.add(LoginHistory(
        user_id=user.id,
        ip_address=ip,
        user_agent=ua[:500],
        device_type=_detect_device(ua),
        success=True,
    ))
    db.commit()

    token = create_access_token({"sub": str(user.id)})
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24,
    )
    return {"message": "로그인 성공", "user": UserOut.model_validate(user)}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    return {"message": "로그아웃 되었습니다."}


class ProfileUpdate(BaseModel):
    username: Optional[str] = None
    phone: Optional[str] = None
    region: Optional[str] = None


@router.put("/profile")
def update_profile(
    data: ProfileUpdate,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """프로필을 수정한다."""
    if data.username:
        user.username = data.username
    if data.phone is not None:
        user.phone = data.phone
    if data.region is not None:
        user.region = data.region
    db.commit()
    db.refresh(user)
    return {"message": "프로필이 수정되었습니다.", "user": UserOut.model_validate(user)}


@router.get("/my-listings")
def get_my_listings(
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """내 매물 목록을 조회한다."""
    listings = (
        db.query(Listing)
        .options(joinedload(Listing.vehicle))
        .filter(Listing.seller_id == user.id)
        .order_by(Listing.created_at.desc())
        .all()
    )
    return {
        "listings": [
            {
                "id": l.id,
                "title": l.title,
                "price": l.price,
                "status": l.status,
                "view_count": l.view_count,
                "created_at": l.created_at.isoformat(),
                "vehicle_id": l.vehicle.id,
                "brand": l.vehicle.brand,
                "model": l.vehicle.model,
                "year": l.vehicle.year,
                "model_3d_status": l.vehicle.model_3d_status,
                "thumbnail_url": l.vehicle.thumbnail_url,
            }
            for l in listings
        ],
        "count": len(listings),
    }


@router.put("/listings/{listing_id}/status")
def update_listing_status(
    listing_id: int,
    status: str,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """매물 상태를 변경한다 (active/reserved/sold)."""
    if status not in ("active", "reserved", "sold"):
        raise HTTPException(status_code=400, detail="유효하지 않은 상태입니다.")

    listing = db.query(Listing).filter(Listing.id == listing_id, Listing.seller_id == user.id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="매물을 찾을 수 없습니다.")

    listing.status = status
    db.commit()
    return {"message": f"매물이 '{status}'로 변경되었습니다.", "listing_id": listing_id, "status": status}


@router.delete("/listings/{listing_id}")
def delete_listing(
    listing_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """매물을 삭제한다."""
    listing = db.query(Listing).filter(Listing.id == listing_id, Listing.seller_id == user.id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="매물을 찾을 수 없습니다.")

    db.delete(listing)
    db.commit()
    return {"message": "매물이 삭제되었습니다."}


@router.get("/login-history")
def get_login_history(
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """최근 로그인 기록을 조회한다."""
    histories = (
        db.query(LoginHistory)
        .filter(LoginHistory.user_id == user.id)
        .order_by(LoginHistory.created_at.desc())
        .limit(20)
        .all()
    )
    return {
        "histories": [
            {
                "id": h.id,
                "ip_address": h.ip_address,
                "device_type": h.device_type,
                "browser": _get_browser(h.user_agent or ""),
                "success": h.success,
                "created_at": h.created_at.isoformat(),
            }
            for h in histories
        ],
        "count": len(histories),
    }
