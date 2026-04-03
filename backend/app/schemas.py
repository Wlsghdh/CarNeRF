from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


# --- Auth ---
class UserCreate(BaseModel):
    email: str
    username: str
    password: str
    phone: Optional[str] = None

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v):
        if len(v) < 8:
            raise ValueError("비밀번호는 8자 이상이어야 합니다.")
        return v


class UserLogin(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: int
    email: str
    username: str
    phone: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- Vehicle ---
class VehicleOut(BaseModel):
    id: int
    brand: str
    model: str
    year: int
    trim: Optional[str] = None
    fuel_type: str
    transmission: str
    mileage: int
    color: Optional[str] = None
    engine_cc: Optional[int] = None
    region: Optional[str] = None
    thumbnail_url: Optional[str] = None
    model_3d_url: Optional[str] = None
    model_3d_status: str

    model_config = {"from_attributes": True}


# --- DiagnosisReport ---
class DiagnosisOut(BaseModel):
    id: int
    vehicle_id: int
    overall_score: float
    exterior_score: float
    interior_score: float
    engine_score: float
    accident_history: Optional[str] = None
    estimated_price_low: Optional[int] = None
    estimated_price_high: Optional[int] = None
    report_summary: Optional[str] = None

    model_config = {"from_attributes": True}


# --- Listing ---
class ListingCreate(BaseModel):
    title: str
    description: Optional[str] = None
    price: int
    is_negotiable: bool = True
    vehicle_id: Optional[int] = None  # Use existing vehicle (e.g. from 3D pipeline)
    brand: str
    model: str
    year: int
    trim: Optional[str] = None
    fuel_type: str
    transmission: str
    mileage: int
    color: Optional[str] = None
    engine_cc: Optional[int] = None
    region: Optional[str] = None
    image_urls: Optional[list[str]] = None  # Uploaded image URLs

    @field_validator("price")
    @classmethod
    def price_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("가격은 0보다 커야 합니다.")
        if v > 50_000_000_000:  # 500억 상한
            raise ValueError("가격이 비정상적으로 높습니다.")
        return v

    @field_validator("year")
    @classmethod
    def year_must_be_valid(cls, v):
        if v < 1990 or v > 2027:
            raise ValueError("연식은 1990~2027 사이여야 합니다.")
        return v

    @field_validator("mileage")
    @classmethod
    def mileage_must_be_valid(cls, v):
        if v < 0:
            raise ValueError("주행거리는 0 이상이어야 합니다.")
        return v


class ListingOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    price: int
    is_negotiable: bool
    status: str
    view_count: int
    created_at: datetime
    vehicle: VehicleOut
    seller: UserOut

    model_config = {"from_attributes": True}


class ListingBrief(BaseModel):
    id: int
    title: str
    price: int
    is_negotiable: bool
    status: str
    view_count: int
    created_at: datetime
    vehicle: VehicleOut

    model_config = {"from_attributes": True}
