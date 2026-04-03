from datetime import datetime, timedelta
import random

from sqlalchemy.orm import Session

from app.dependencies import hash_password
from app.models import User, Vehicle, Listing, DiagnosisReport, UserReview, TransactionHistory


def seed_database(db: Session):
    if db.query(User).first():
        return

    # ── Users ──
    users = [
        User(
            email="demo@carnerf.kr", username="데모사용자",
            hashed_password=hash_password("demo1234"),
            phone="010-1234-5678", role="buyer", points=5000, region="서울",
        ),
        User(
            email="seller@carnerf.kr", username="김판매",
            hashed_password=hash_password("seller1234"),
            phone="010-9876-5432", role="seller", is_verified=True, points=12000, region="경기",
        ),
        User(
            email="park@carnerf.kr", username="박중고",
            hashed_password=hash_password("park1234"),
            phone="010-5555-1234", role="seller", is_verified=True, points=8000, region="부산",
        ),
        User(
            email="lee@carnerf.kr", username="이차차",
            hashed_password=hash_password("lee1234"),
            phone="010-3333-4444", role="seller", is_verified=True, points=15000, region="대전",
        ),
        User(
            email="buyer2@carnerf.kr", username="최구매",
            hashed_password=hash_password("buyer1234"),
            phone="010-7777-8888", role="buyer", points=3000, region="인천",
        ),
    ]
    db.add_all(users)
    db.flush()

    demo_user, seller2, seller3, seller4, buyer2 = users

    # ── Vehicles & Listings ──
    vehicles_listings = [
        # 1. 현대 NF소나타 (기존 3D 모델 있는 차량)
        {
            "v": {"brand": "현대", "model": "NF소나타", "year": 2008, "trim": "트랜스폼 GLS",
                  "fuel_type": "가솔린", "transmission": "자동", "mileage": 142000,
                  "color": "실버", "engine_cc": 1998, "region": "경기",
                  "thumbnail_url": "/static/images/nf_sonata_thumb.jpg",
                  "model_3d_url": "/static/models/nf_sonata/model.splat", "model_3d_status": "ready"},
            "l": {"title": "NF소나타 트랜스폼 실주행 관리차량", "price": 380,
                  "description": "NF소나타 트랜스폼 GLS입니다. 14만km 주행했지만 엔진 미션 상태 매우 좋습니다. 타이밍벨트, 워터펌프 최근 교체. 실내 금연차량."},
            "d": {"overall_score": 72, "exterior_score": 65, "interior_score": 75, "engine_score": 76,
                  "accident_history": "경미한 접촉사고 1회 (2015년)",
                  "estimated_price_low": 320, "estimated_price_high": 450,
                  "report_summary": "2008년식 NF소나타로 연식 대비 양호한 상태입니다. 외관에 사용감이 있으나 기계적 상태는 관리가 잘 되어있습니다."},
            "seller": demo_user,
        },
        # 2. 현대 그랜저
        {
            "v": {"brand": "현대", "model": "그랜저", "year": 2022, "trim": "르블랑",
                  "fuel_type": "가솔린", "transmission": "자동", "mileage": 32000,
                  "color": "화이트", "engine_cc": 2497, "region": "서울",
                  "thumbnail_url": "/static/images/car2_test_thumb.jpg",
                  "model_3d_url": "/static/models/car2_test/model.splat", "model_3d_status": "ready"},
            "l": {"title": "그랜저 르블랑 풀옵 무사고 직거래", "price": 3200,
                  "description": "2022년식 그랜저 르블랑입니다. 무사고, 1인 소유, 금연차량. 풀옵션(HUD, 서라운드뷰, 통풍시트, JBL 사운드). 정비이력 투명공개."},
            "d": {"overall_score": 92, "exterior_score": 95, "interior_score": 90, "engine_score": 91,
                  "accident_history": "무사고",
                  "estimated_price_low": 2900, "estimated_price_high": 3500,
                  "report_summary": "2022년식 그랜저 르블랑으로 전반적으로 매우 우수한 상태입니다. 정비이력이 체계적이고 실내외 상태 양호."},
            "seller": seller2,
        },
        # 3. 기아 K5
        {
            "v": {"brand": "기아", "model": "K5", "year": 2021, "trim": "시그니처",
                  "fuel_type": "가솔린", "transmission": "자동", "mileage": 48000,
                  "color": "그레이", "engine_cc": 1999, "region": "경기",
                  "thumbnail_url": "/static/images/placeholder-car.svg", "model_3d_status": "none"},
            "l": {"title": "K5 시그니처 1인신조 완전무사고", "price": 2100,
                  "description": "K5 시그니처 트림. 1인 신조, 완전 무사고. 네비, 후방카메라, 열선시트 등 옵션 다수. 타이어 최근 4개 교체."},
            "d": {"overall_score": 88, "exterior_score": 90, "interior_score": 85, "engine_score": 89,
                  "accident_history": "무사고",
                  "estimated_price_low": 1900, "estimated_price_high": 2400,
                  "report_summary": "2021년식 K5로 실주행 적고 상태 우수. 타이어 교체 이력 확인."},
            "seller": seller3,
        },
        # 4. 기아 쏘렌토
        {
            "v": {"brand": "기아", "model": "쏘렌토", "year": 2023, "trim": "프레스티지",
                  "fuel_type": "디젤", "transmission": "자동", "mileage": 18000,
                  "color": "블랙", "engine_cc": 2199, "region": "부산",
                  "thumbnail_url": "/static/images/placeholder-car.svg", "model_3d_status": "none"},
            "l": {"title": "쏘렌토 프레스티지 디젤 18000km 급매", "price": 3400,
                  "description": "2023년식 쏘렌토 프레스티지 디젤. 이전 필요하여 급매합니다. 상태 최상급. 모든 정비 공식 센터에서 진행."},
            "d": {"overall_score": 95, "exterior_score": 96, "interior_score": 94, "engine_score": 95,
                  "accident_history": "무사고",
                  "estimated_price_low": 3200, "estimated_price_high": 3800,
                  "report_summary": "거의 신차급 상태. 1년 미만 차량으로 감가상각 대비 가성비 우수."},
            "seller": seller3,
        },
        # 5. 제네시스 G80
        {
            "v": {"brand": "제네시스", "model": "G80", "year": 2021, "trim": "스포츠",
                  "fuel_type": "가솔린", "transmission": "자동", "mileage": 55000,
                  "color": "블루", "engine_cc": 2497, "region": "서울",
                  "thumbnail_url": "/static/images/placeholder-car.svg", "model_3d_status": "none"},
            "l": {"title": "제네시스 G80 스포츠 풀옵 에어서스", "price": 4800,
                  "description": "G80 스포츠 트림 풀옵션. 에어서스펜션, HUD, 스포츠 배기, 렉시콘 사운드. 서울 직거래 가능."},
            "d": {"overall_score": 86, "exterior_score": 84, "interior_score": 88, "engine_score": 86,
                  "accident_history": "단순 수리 1회 (범퍼 도색)",
                  "estimated_price_low": 4500, "estimated_price_high": 5200,
                  "report_summary": "제네시스 G80 스포츠로 주행 성능과 편의 사양 우수. 범퍼 도색 이력 있으나 구조적 문제 없음."},
            "seller": seller4,
        },
        # 6. BMW 520i
        {
            "v": {"brand": "BMW", "model": "520i", "year": 2020, "trim": "M스포츠",
                  "fuel_type": "가솔린", "transmission": "자동", "mileage": 62000,
                  "color": "화이트", "engine_cc": 1998, "region": "경기",
                  "thumbnail_url": "/static/images/placeholder-car.svg", "model_3d_status": "none"},
            "l": {"title": "BMW 520i M스포츠 패키지 정비완료", "price": 3800,
                  "description": "520i M스포츠 패키지. 정식 수입, 공식 서비스센터에서만 정비. 엔진오일, 브레이크 패드 최근 교체. 냉각수 누수 점검 완료."},
            "d": {"overall_score": 82, "exterior_score": 80, "interior_score": 85, "engine_score": 81,
                  "accident_history": "무사고",
                  "estimated_price_low": 3500, "estimated_price_high": 4200,
                  "report_summary": "BMW 520i M스포츠로 주행 감성 우수. B48 엔진 상태 양호하며 냉각수 누수 없음 확인."},
            "seller": seller2,
        },
        # 7. 현대 투싼
        {
            "v": {"brand": "현대", "model": "투싼", "year": 2023, "trim": "인스퍼레이션",
                  "fuel_type": "하이브리드", "transmission": "자동", "mileage": 12000,
                  "color": "그린", "engine_cc": 1598, "region": "대전",
                  "thumbnail_url": "/static/images/placeholder-car.svg", "model_3d_status": "none"},
            "l": {"title": "투싼 하이브리드 인스퍼 1.2만km 여성운전", "price": 3100,
                  "description": "투싼 하이브리드 최상위 트림. 여성 1인 운전, 비흡연. 사고이력 전혀 없음. 연비 리터당 16km 이상."},
            "d": {"overall_score": 96, "exterior_score": 97, "interior_score": 96, "engine_score": 95,
                  "accident_history": "무사고",
                  "estimated_price_low": 2800, "estimated_price_high": 3400,
                  "report_summary": "신차급 상태의 투싼 하이브리드. 주행거리 매우 적고 관리 상태 최상."},
            "seller": seller4,
        },
        # 8. 기아 EV6
        {
            "v": {"brand": "기아", "model": "EV6", "year": 2022, "trim": "롱레인지 AWD",
                  "fuel_type": "전기", "transmission": "자동", "mileage": 28000,
                  "color": "화이트", "engine_cc": 0, "region": "서울",
                  "thumbnail_url": "/static/images/placeholder-car.svg", "model_3d_status": "none"},
            "l": {"title": "EV6 롱레인지 AWD 보조금 승계 가능", "price": 4200,
                  "description": "EV6 롱레인지 AWD. 보조금 승계 가능. 77.4kWh 배터리, 잔여 SOH 97%. V2L 어댑터 포함. 충전 시 350kW 울트라 급속 지원."},
            "d": {"overall_score": 91, "exterior_score": 92, "interior_score": 90, "engine_score": 91,
                  "accident_history": "무사고",
                  "estimated_price_low": 3800, "estimated_price_high": 4600,
                  "report_summary": "EV6 AWD로 배터리 상태 우수(SOH 97%). 전기차 특성상 유지비 매우 저렴."},
            "seller": seller2,
        },
        # 9. 현대 아반떼
        {
            "v": {"brand": "현대", "model": "아반떼", "year": 2024, "trim": "인스퍼레이션",
                  "fuel_type": "가솔린", "transmission": "자동", "mileage": 5000,
                  "color": "레드", "engine_cc": 1598, "region": "인천",
                  "thumbnail_url": "/static/images/placeholder-car.svg", "model_3d_status": "none"},
            "l": {"title": "아반떼 24년식 5천km 신차급 급매", "price": 2000,
                  "description": "2024년식 아반떼 인스퍼레이션. 사정으로 급매합니다. 5천km 신차급. 보험이력 없음."},
            "d": {"overall_score": 98, "exterior_score": 99, "interior_score": 98, "engine_score": 97,
                  "accident_history": "무사고",
                  "estimated_price_low": 1800, "estimated_price_high": 2200,
                  "report_summary": "거의 신차 상태의 아반떼. 주행거리 5천km, 모든 항목 최상."},
            "seller": seller3,
        },
        # 10. 쉐보레 트레일블레이저
        {
            "v": {"brand": "쉐보레", "model": "트레일블레이저", "year": 2022, "trim": "LT",
                  "fuel_type": "가솔린", "transmission": "자동", "mileage": 35000,
                  "color": "블루", "engine_cc": 1332, "region": "부산",
                  "thumbnail_url": "/static/images/placeholder-car.svg", "model_3d_status": "none"},
            "l": {"title": "트레일블레이저 LT 1.35터보 실매물", "price": 1800,
                  "description": "쉐보레 트레일블레이저 LT. 1.35 터보 엔진으로 출력 좋고 연비도 양호. 부산 직거래만 가능합니다."},
            "d": {"overall_score": 84, "exterior_score": 82, "interior_score": 85, "engine_score": 85,
                  "accident_history": "무사고",
                  "estimated_price_low": 1600, "estimated_price_high": 2000,
                  "report_summary": "트레일블레이저 LT로 소형 SUV 중 가성비 우수. 전반적 상태 양호."},
            "seller": seller4,
        },
        # 11. 현대 캐스퍼
        {
            "v": {"brand": "현대", "model": "캐스퍼", "year": 2023, "trim": "인스퍼레이션",
                  "fuel_type": "가솔린", "transmission": "자동", "mileage": 15000,
                  "color": "오렌지", "engine_cc": 998, "region": "서울",
                  "thumbnail_url": "/static/images/placeholder-car.svg", "model_3d_status": "none"},
            "l": {"title": "캐스퍼 인스퍼 1.5만km 통학용 최적", "price": 1350,
                  "description": "캐스퍼 인스퍼레이션 트림. 통학용으로 사용, 시내 주행만 했습니다. 주차 편리하고 유지비 저렴."},
            "d": {"overall_score": 90, "exterior_score": 88, "interior_score": 92, "engine_score": 90,
                  "accident_history": "무사고",
                  "estimated_price_low": 1200, "estimated_price_high": 1500,
                  "report_summary": "캐스퍼 최상위 트림으로 소형차 중 편의사양 우수. 상태 양호."},
            "seller": demo_user,
        },
        # 12. 기아 카니발
        {
            "v": {"brand": "기아", "model": "카니발", "year": 2021, "trim": "노블레스",
                  "fuel_type": "디젤", "transmission": "자동", "mileage": 65000,
                  "color": "블랙", "engine_cc": 2199, "region": "경기",
                  "thumbnail_url": "/static/images/placeholder-car.svg", "model_3d_status": "none"},
            "l": {"title": "카니발 노블레스 디젤 9인승 가족용", "price": 2900,
                  "description": "카니발 노블레스 9인승 디젤. 가족 여행용으로 사용. 실내 넓고 2,3열 모두 상태 좋습니다. 정기 점검 철저히 진행."},
            "d": {"overall_score": 83, "exterior_score": 80, "interior_score": 82, "engine_score": 87,
                  "accident_history": "경미한 접촉 1회 (주차장)",
                  "estimated_price_low": 2600, "estimated_price_high": 3200,
                  "report_summary": "카니발 노블레스로 패밀리카 수요 높음. 디젤 엔진 상태 양호, 주차장 접촉 흔적 경미."},
            "seller": seller2,
        },
    ]

    vehicles = []
    for i, item in enumerate(vehicles_listings):
        v = Vehicle(**item["v"])
        db.add(v)
        db.flush()
        vehicles.append(v)

        listing = Listing(
            vehicle_id=v.id,
            seller_id=item["seller"].id,
            title=item["l"]["title"],
            description=item["l"]["description"],
            price=item["l"]["price"],
            is_negotiable=(i % 3 != 0),
            view_count=random.randint(5, 150),
        )
        db.add(listing)

        if "d" in item:
            report = DiagnosisReport(vehicle_id=v.id, **item["d"])
            db.add(report)

    # ── Reviews ──
    review_texts = [
        (0, demo_user, 4, "buyer", "NF소나타 가성비 정말 좋습니다. 14만km 타도 엔진 튼튼하고 연비도 괜찮아요."),
        (0, seller2, 3, "buyer", "소나타 NF 중고로 샀는데 전체적으로 괜찮아요. 다만 연식이 있어서 서스펜션 소음이 좀 있어요."),
        (1, buyer2, 5, "buyer", "그랜저 르블랑 사서 너무 만족합니다. 판매자분도 친절하시고 차 상태 실물이 더 좋아요."),
        (1, demo_user, 4, "buyer", "그랜저 역시 편안합니다. 장거리 출장 때 진가를 발휘해요. 연비만 좀 아쉬움."),
        (2, buyer2, 5, "buyer", "K5 시그니처 디자인 진짜 예쁘고 옵션도 많아서 만족해요. 추천합니다!"),
        (3, demo_user, 5, "buyer", "쏘렌토 디젤 토크 좋고 고속도로에서 안정적. 가족 여행에 딱!"),
        (4, buyer2, 4, "buyer", "G80 역시 제네시스. 승차감이 다릅니다. 에어서스 진짜 좋아요."),
        (6, demo_user, 5, "buyer", "투싼 하이브리드 연비 미쳤어요. 리터 17km 나옵니다. 강추!"),
        (7, buyer2, 4, "buyer", "EV6 충전 빠르고 실내 넓어서 좋아요. 다만 겨울 주행거리는 좀 줄어요."),
        (8, seller3, 5, "seller", "구매자분이 꼼꼼하게 확인하시고 깔끔하게 거래 마무리. 감사합니다."),
    ]
    for vidx, author, rating, rtype, content in review_texts:
        review = UserReview(
            vehicle_id=vehicles[vidx].id,
            author_id=author.id,
            rating=rating,
            content=content,
            review_type=rtype,
        )
        db.add(review)

    # ── Transaction History ──
    now = datetime.utcnow()
    regions = ["서울", "경기", "인천", "부산", "대전", "대구", "광주"]

    # NF소나타 거래 이력
    for days_ago, price, mileage in [
        (15, 390, 138000), (35, 410, 125000), (58, 370, 150000),
        (82, 420, 118000), (105, 450, 105000), (130, 400, 132000),
        (160, 480, 95000), (195, 430, 120000), (225, 500, 88000),
        (260, 460, 110000), (300, 520, 82000), (340, 550, 75000),
    ]:
        db.add(TransactionHistory(
            vehicle_id=vehicles[0].id,
            transaction_date=now - timedelta(days=days_ago),
            price=price, mileage_at_sale=mileage,
            source=random.choice(["carnerf", "external"]),
            buyer_region=random.choice(regions),
            seller_region=random.choice(regions),
        ))

    # 그랜저 거래 이력
    for days_ago, price, mileage in [
        (10, 3100, 30000), (30, 3300, 25000), (50, 3000, 38000),
        (80, 3200, 28000), (120, 3400, 20000), (180, 3500, 15000),
    ]:
        db.add(TransactionHistory(
            vehicle_id=vehicles[1].id,
            transaction_date=now - timedelta(days=days_ago),
            price=price, mileage_at_sale=mileage,
            source=random.choice(["carnerf", "external"]),
            buyer_region=random.choice(regions),
            seller_region=random.choice(regions),
        ))

    # K5 거래 이력
    for days_ago, price, mileage in [
        (20, 2050, 45000), (45, 2200, 38000), (75, 1950, 52000),
        (110, 2100, 40000), (150, 2300, 32000),
    ]:
        db.add(TransactionHistory(
            vehicle_id=vehicles[2].id,
            transaction_date=now - timedelta(days=days_ago),
            price=price, mileage_at_sale=mileage,
            source=random.choice(["carnerf", "external"]),
            buyer_region=random.choice(regions),
            seller_region=random.choice(regions),
        ))

    # EV6 거래 이력
    for days_ago, price, mileage in [
        (25, 4100, 25000), (60, 4300, 20000), (100, 4500, 15000),
        (140, 4700, 10000),
    ]:
        db.add(TransactionHistory(
            vehicle_id=vehicles[7].id,
            transaction_date=now - timedelta(days=days_ago),
            price=price, mileage_at_sale=mileage,
            source=random.choice(["carnerf", "external"]),
            buyer_region=random.choice(regions),
            seller_region=random.choice(regions),
        ))

    db.commit()
