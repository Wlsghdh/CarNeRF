from datetime import datetime
from typing import Optional

from pydantic import BaseModel


# --- Auth ---
class UserCreate(BaseModel):
    email: str
    username: str
    password: str
    phone: Optional[str] = None


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
