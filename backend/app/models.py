from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    listings = relationship("Listing", back_populates="seller")


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    brand = Column(String(50), nullable=False)
    model = Column(String(100), nullable=False)
    year = Column(Integer, nullable=False)
    trim = Column(String(100), nullable=True)
    fuel_type = Column(String(20), nullable=False)  # 가솔린, 디젤, 전기, 하이브리드
    transmission = Column(String(20), nullable=False)  # 자동, 수동
    mileage = Column(Integer, nullable=False)  # km
    color = Column(String(30), nullable=True)
    engine_cc = Column(Integer, nullable=True)
    region = Column(String(50), nullable=True)
    thumbnail_url = Column(String(500), nullable=True)
    model_3d_url = Column(String(500), nullable=True)
    model_3d_status = Column(String(20), default="none")  # none, processing, ready
    created_at = Column(DateTime, default=datetime.utcnow)

    listing = relationship("Listing", back_populates="vehicle", uselist=False)
    diagnosis = relationship("DiagnosisReport", back_populates="vehicle", uselist=False)


class Listing(Base):
    __tablename__ = "listings"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Integer, nullable=False)  # 만원 단위
    is_negotiable = Column(Boolean, default=True)
    status = Column(String(20), default="active")  # active, reserved, sold
    view_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    vehicle = relationship("Vehicle", back_populates="listing")
    seller = relationship("User", back_populates="listings")


class DiagnosisReport(Base):
    __tablename__ = "diagnosis_reports"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    overall_score = Column(Float, nullable=False)
    exterior_score = Column(Float, nullable=False)
    interior_score = Column(Float, nullable=False)
    engine_score = Column(Float, nullable=False)
    accident_history = Column(String(200), nullable=True)
    estimated_price_low = Column(Integer, nullable=True)  # 만원
    estimated_price_high = Column(Integer, nullable=True)  # 만원
    report_summary = Column(Text, nullable=True)

    vehicle = relationship("Vehicle", back_populates="diagnosis")
