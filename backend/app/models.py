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
    role = Column(String(20), default="buyer")  # buyer, seller
    points = Column(Integer, default=0)
    is_verified = Column(Boolean, default=False)
    region = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    listings = relationship("Listing", back_populates="seller")
    reviews = relationship("UserReview", back_populates="author")
    point_transactions = relationship("PointTransaction", back_populates="user")


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
    reviews = relationship("UserReview", back_populates="vehicle")
    transaction_histories = relationship("TransactionHistory", back_populates="vehicle")


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


class PointTransaction(Base):
    __tablename__ = "point_transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Integer, nullable=False)  # 양수=충전, 음수=사용
    balance_after = Column(Integer, nullable=False)
    transaction_type = Column(String(30), nullable=False)  # charge, ai_usage, premium_listing, refund
    description = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="point_transactions")


class UserReview(Base):
    __tablename__ = "user_reviews"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rating = Column(Integer, nullable=False)  # 1~5
    content = Column(Text, nullable=False)
    review_type = Column(String(20), nullable=False)  # buyer, seller
    created_at = Column(DateTime, default=datetime.utcnow)

    vehicle = relationship("Vehicle", back_populates="reviews")
    author = relationship("User", back_populates="reviews")


class TransactionHistory(Base):
    __tablename__ = "transaction_histories"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    transaction_date = Column(DateTime, nullable=False)
    price = Column(Integer, nullable=False)  # 만원
    mileage_at_sale = Column(Integer, nullable=True)
    source = Column(String(50), nullable=True)  # carnerf, external
    buyer_region = Column(String(50), nullable=True)
    seller_region = Column(String(50), nullable=True)

    vehicle = relationship("Vehicle", back_populates="transaction_histories")
