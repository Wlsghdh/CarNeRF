from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.dependencies import hash_password
from app.models import User, Vehicle, Listing, DiagnosisReport, UserReview, TransactionHistory


def seed_database(db: Session):
    if db.query(User).first():
        return

    # Demo user
    demo_user = User(
        email="demo@carnerf.kr",
        username="데모사용자",
        hashed_password=hash_password("demo1234"),
        phone="010-1234-5678",
        role="buyer",
        points=5000,
        region="서울",
    )
    seller2 = User(
        email="seller@carnerf.kr",
        username="김판매",
        hashed_password=hash_password("seller1234"),
        phone="010-9876-5432",
        role="seller",
        is_verified=True,
        points=12000,
        region="경기",
    )
    db.add_all([demo_user, seller2])
    db.flush()

    vehicles_data = [
        {
            "brand": "현대", "model": "NF소나타", "year": 2008, "trim": "트랜스폼 GLS",
            "fuel_type": "가솔린", "transmission": "자동", "mileage": 142000,
            "color": "실버", "engine_cc": 1998, "region": "경기",
            "thumbnail_url": "/static/images/nf_sonata_thumb.jpg",
            "model_3d_url": "/static/models/nf_sonata/model.splat",
            "model_3d_status": "ready",
        },
    ]

    listings_data = [
        {"title": "NF소나타 트랜스폼 실주행 관리차량", "price": 380, "description": "NF소나타 트랜스폼 GLS입니다. 14만km 주행했지만 엔진 미션 상태 매우 좋습니다. 타이밍벨트, 워터펌프 최근 교체. 실내 금연차량."},
    ]

    diagnosis_data = [
        {"overall_score": 72, "exterior_score": 65, "interior_score": 75, "engine_score": 76, "accident_history": "경미한 접촉사고 1회 (2015년)", "estimated_price_low": 320, "estimated_price_high": 450, "report_summary": "2008년식 NF소나타로 연식 대비 양호한 상태입니다. 외관에 사용감이 있으나 기계적 상태는 관리가 잘 되어있습니다. 타이밍벨트 교체 이력 확인."},
    ]

    vehicles = []
    for vdata in vehicles_data:
        v = Vehicle(**vdata)
        db.add(v)
        db.flush()
        vehicles.append(v)

    for i, (ldata, ddata) in enumerate(zip(listings_data, diagnosis_data)):
        seller = demo_user if i % 2 == 0 else seller2
        listing = Listing(
            vehicle_id=vehicles[i].id,
            seller_id=seller.id,
            title=ldata["title"],
            description=ldata["description"],
            price=ldata["price"],
            is_negotiable=(i % 3 != 0),
            view_count=(i + 1) * 17,
        )
        db.add(listing)

        report = DiagnosisReport(vehicle_id=vehicles[i].id, **ddata)
        db.add(report)

    # 리뷰 데이터
    reviews_data = [
        {"vehicle_idx": 0, "author": demo_user, "rating": 4, "review_type": "buyer",
         "content": "NF소나타 가성비 정말 좋습니다. 14만km 타도 엔진 튼튼하고 연비도 괜찮아요. 출퇴근용으로 최고!"},
        {"vehicle_idx": 0, "author": seller2, "rating": 3, "review_type": "buyer",
         "content": "소나타 NF 중고로 샀는데 전체적으로 괜찮아요. 다만 연식이 있어서 서스펜션 소음이 좀 있고, 도어 고무패킹이 좀 낡았어요."},
    ]
    for rd in reviews_data:
        review = UserReview(
            vehicle_id=vehicles[rd["vehicle_idx"]].id,
            author_id=rd["author"].id,
            rating=rd["rating"],
            content=rd["content"],
            review_type=rd["review_type"],
        )
        db.add(review)

    # 거래 이력 데이터 — NF소나타 12개월간
    now = datetime.utcnow()
    transactions_data = [
        {"vehicle_idx": 0, "days_ago": 15, "price": 390, "mileage": 138000, "source": "carnerf", "buyer_region": "서울", "seller_region": "경기"},
        {"vehicle_idx": 0, "days_ago": 35, "price": 410, "mileage": 125000, "source": "external", "buyer_region": "경기", "seller_region": "인천"},
        {"vehicle_idx": 0, "days_ago": 58, "price": 370, "mileage": 150000, "source": "carnerf", "buyer_region": "인천", "seller_region": "경기"},
        {"vehicle_idx": 0, "days_ago": 82, "price": 420, "mileage": 118000, "source": "external", "buyer_region": "서울", "seller_region": "서울"},
        {"vehicle_idx": 0, "days_ago": 105, "price": 450, "mileage": 105000, "source": "carnerf", "buyer_region": "경기", "seller_region": "서울"},
        {"vehicle_idx": 0, "days_ago": 130, "price": 400, "mileage": 132000, "source": "external", "buyer_region": "대전", "seller_region": "경기"},
        {"vehicle_idx": 0, "days_ago": 160, "price": 480, "mileage": 95000, "source": "carnerf", "buyer_region": "서울", "seller_region": "서울"},
        {"vehicle_idx": 0, "days_ago": 195, "price": 430, "mileage": 120000, "source": "external", "buyer_region": "부산", "seller_region": "경기"},
        {"vehicle_idx": 0, "days_ago": 225, "price": 500, "mileage": 88000, "source": "carnerf", "buyer_region": "서울", "seller_region": "서울"},
        {"vehicle_idx": 0, "days_ago": 260, "price": 460, "mileage": 110000, "source": "external", "buyer_region": "경기", "seller_region": "인천"},
        {"vehicle_idx": 0, "days_ago": 300, "price": 520, "mileage": 82000, "source": "carnerf", "buyer_region": "서울", "seller_region": "경기"},
        {"vehicle_idx": 0, "days_ago": 340, "price": 550, "mileage": 75000, "source": "external", "buyer_region": "인천", "seller_region": "서울"},
    ]
    for td in transactions_data:
        tx = TransactionHistory(
            vehicle_id=vehicles[td["vehicle_idx"]].id,
            transaction_date=now - timedelta(days=td["days_ago"]),
            price=td["price"],
            mileage_at_sale=td["mileage"],
            source=td["source"],
            buyer_region=td["buyer_region"],
            seller_region=td["seller_region"],
        )
        db.add(tx)

    db.commit()
