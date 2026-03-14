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
            "thumbnail_url": "/static/images/placeholder-car.svg",
            "model_3d_url": "/static/models/nf_sonata/model.splat",
            "model_3d_status": "ready",
        },
        {
            "brand": "현대", "model": "그랜저", "year": 2022, "trim": "르블랑 익스클루시브",
            "fuel_type": "가솔린", "transmission": "자동", "mileage": 32000,
            "color": "어비스블랙펄", "engine_cc": 2497, "region": "서울",
            "thumbnail_url": "/static/images/placeholder-car.svg",
            "model_3d_url": "/static/models/truck_test/model.splat",
            "model_3d_status": "ready",
        },
        {
            "brand": "현대", "model": "투싼", "year": 2023, "trim": "인스퍼레이션",
            "fuel_type": "디젤", "transmission": "자동", "mileage": 18000,
            "color": "아마존그레이", "engine_cc": 1598, "region": "경기",
            "thumbnail_url": "/static/images/placeholder-car.svg",
        },
        {
            "brand": "현대", "model": "아반떼", "year": 2021, "trim": "스마트",
            "fuel_type": "가솔린", "transmission": "자동", "mileage": 45000,
            "color": "화이트크림", "engine_cc": 1598, "region": "인천",
            "thumbnail_url": "/static/images/placeholder-car.svg",
        },
        {
            "brand": "현대", "model": "팰리세이드", "year": 2023, "trim": "캘리그래피",
            "fuel_type": "디젤", "transmission": "자동", "mileage": 15000,
            "color": "문라이트블루펄", "engine_cc": 2199, "region": "서울",
            "thumbnail_url": "/static/images/placeholder-car.svg",
        },
        {
            "brand": "기아", "model": "K5", "year": 2022, "trim": "시그니처",
            "fuel_type": "가솔린", "transmission": "자동", "mileage": 28000,
            "color": "스노우화이트펄", "engine_cc": 1999, "region": "부산",
            "thumbnail_url": "/static/images/placeholder-car.svg",
        },
        {
            "brand": "기아", "model": "쏘렌토", "year": 2021, "trim": "프레스티지",
            "fuel_type": "디젤", "transmission": "자동", "mileage": 52000,
            "color": "그래비티그레이", "engine_cc": 2151, "region": "대구",
            "thumbnail_url": "/static/images/placeholder-car.svg",
        },
        {
            "brand": "기아", "model": "EV6", "year": 2023, "trim": "롱레인지 2WD",
            "fuel_type": "전기", "transmission": "자동", "mileage": 12000,
            "color": "런웨이레드", "engine_cc": 0, "region": "서울",
            "thumbnail_url": "/static/images/placeholder-car.svg",
        },
        {
            "brand": "기아", "model": "니로 EV", "year": 2022, "trim": "프레스티지",
            "fuel_type": "전기", "transmission": "자동", "mileage": 22000,
            "color": "스노우화이트펄", "engine_cc": 0, "region": "경기",
            "thumbnail_url": "/static/images/placeholder-car.svg",
        },
        {
            "brand": "제네시스", "model": "G80", "year": 2022, "trim": "3.5T 스포트",
            "fuel_type": "가솔린", "transmission": "자동", "mileage": 25000,
            "color": "마칼루그레이", "engine_cc": 3470, "region": "서울",
            "thumbnail_url": "/static/images/placeholder-car.svg",
        },
        {
            "brand": "쉐보레", "model": "트래버스", "year": 2021, "trim": "프리미어",
            "fuel_type": "가솔린", "transmission": "자동", "mileage": 38000,
            "color": "모자브브라운", "engine_cc": 3564, "region": "경기",
            "thumbnail_url": "/static/images/placeholder-car.svg",
        },
        {
            "brand": "BMW", "model": "520i", "year": 2022, "trim": "M 스포츠 패키지",
            "fuel_type": "가솔린", "transmission": "자동", "mileage": 20000,
            "color": "블랙사파이어", "engine_cc": 1998, "region": "서울",
            "thumbnail_url": "/static/images/placeholder-car.svg",
        },
        {
            "brand": "르노", "model": "QM6", "year": 2021, "trim": "RE 시그니처",
            "fuel_type": "가솔린", "transmission": "자동", "mileage": 41000,
            "color": "밀레니엄실버", "engine_cc": 1997, "region": "대전",
            "thumbnail_url": "/static/images/placeholder-car.svg",
        },
    ]

    listings_data = [
        {"title": "NF소나타 트랜스폼 실주행 관리차량", "price": 380, "description": "NF소나타 트랜스폼 GLS입니다. 14만km 주행했지만 엔진 미션 상태 매우 좋습니다. 타이밍벨트, 워터펌프 최근 교체. 실내 금연차량."},
        {"title": "그랜저 르블랑 풀옵 무사고", "price": 3250, "description": "1인 소유, 풀옵션, 무사고 차량입니다. 실내 금연차량이며 관리 잘 되어있습니다."},
        {"title": "투싼 디젤 인스퍼레이션 급매", "price": 2850, "description": "급매물입니다. 정비 이력 투명하게 공개합니다. 타이어 최근 교체."},
        {"title": "아반떼 1.6 가성비 최고", "price": 1650, "description": "가성비 좋은 아반떼입니다. 출퇴근용으로 최적. 엔진오일 방금 교체."},
        {"title": "팰리세이드 캘리그래피 7인승", "price": 4580, "description": "7인승 캘리그래피 풀옵션. 어라운드뷰, 헤드업디스플레이, 네비 등 모든 옵션 포함."},
        {"title": "K5 시그니처 2.0 무사고", "price": 2380, "description": "무사고 K5 시그니처입니다. 블랙박스 영상 확인 가능합니다."},
        {"title": "쏘렌토 디젤 7인승 패밀리카", "price": 2650, "description": "가족용으로 사용하던 쏘렌토입니다. 넓은 실내공간, 7인승."},
        {"title": "EV6 롱레인지 전기차 보조금 가능", "price": 4200, "description": "전기차 보조금 승계 가능. 1회 충전 450km 주행 가능. 완속/급속 충전 모두 가능."},
        {"title": "니로 EV 전기차 가성비 전기차", "price": 2950, "description": "가성비 전기차 니로 EV입니다. 1회 충전 380km 주행. 배터리 상태 우수."},
        {"title": "제네시스 G80 3.5T 풀옵 럭셔리", "price": 5200, "description": "제네시스 G80 최상위 트림. 3.5 터보 엔진, 스포트 패키지. VIP 시트 포함."},
        {"title": "트래버스 대형 SUV 미국차", "price": 3150, "description": "미국 대형 SUV 트래버스. 넓은 트렁크, 3열 시트. 캠핑카로도 인기."},
        {"title": "BMW 520i M스포츠 수입차", "price": 4100, "description": "BMW 520i M스포츠 패키지. 수입차 특유의 주행감. 정식 수입, 서비스 이력 투명."},
        {"title": "QM6 가성비 중형 SUV", "price": 1850, "description": "르노 QM6 가성비 좋은 중형 SUV입니다. 넓은 실내, 연비 좋음."},
    ]

    diagnosis_data = [
        {"overall_score": 72, "exterior_score": 65, "interior_score": 75, "engine_score": 76, "accident_history": "경미한 접촉사고 1회 (2015년)", "estimated_price_low": 320, "estimated_price_high": 450, "report_summary": "2008년식 NF소나타로 연식 대비 양호한 상태입니다. 외관에 사용감이 있으나 기계적 상태는 관리가 잘 되어있습니다. 타이밍벨트 교체 이력 확인."},
        {"overall_score": 92, "exterior_score": 95, "interior_score": 90, "engine_score": 91, "accident_history": "무사고", "estimated_price_low": 3050, "estimated_price_high": 3450, "report_summary": "전체적으로 매우 양호한 상태입니다. 외관 스크래치 미미하며 엔진룸 깨끗합니다."},
        {"overall_score": 88, "exterior_score": 85, "interior_score": 90, "engine_score": 89, "accident_history": "무사고", "estimated_price_low": 2650, "estimated_price_high": 3050, "report_summary": "외관에 경미한 스크래치가 있으나 실내 상태 우수합니다. 디젤 엔진 컨디션 양호."},
        {"overall_score": 78, "exterior_score": 75, "interior_score": 80, "engine_score": 79, "accident_history": "무사고", "estimated_price_low": 1450, "estimated_price_high": 1800, "report_summary": "주행거리 대비 양호한 상태. 타이어 교체 시기 임박. 전체적으로 관리 상태 보통."},
        {"overall_score": 95, "exterior_score": 96, "interior_score": 94, "engine_score": 95, "accident_history": "무사고", "estimated_price_low": 4300, "estimated_price_high": 4800, "report_summary": "거의 신차급 상태입니다. 모든 부분에서 높은 점수를 받았습니다."},
        {"overall_score": 85, "exterior_score": 83, "interior_score": 87, "engine_score": 85, "accident_history": "무사고", "estimated_price_low": 2150, "estimated_price_high": 2550, "report_summary": "전반적으로 양호합니다. 앞범퍼 미세 도색 흔적이 있으나 사고 이력은 아닙니다."},
        {"overall_score": 75, "exterior_score": 72, "interior_score": 78, "engine_score": 75, "accident_history": "경미한 접촉사고 1회", "estimated_price_low": 2350, "estimated_price_high": 2800, "report_summary": "경미한 접촉사고 이력이 있습니다. 수리 상태 양호하며 주행에 문제 없습니다."},
        {"overall_score": 96, "exterior_score": 97, "interior_score": 95, "engine_score": 96, "accident_history": "무사고", "estimated_price_low": 3900, "estimated_price_high": 4400, "report_summary": "신차급 전기차입니다. 배터리 SOH 98%, 모터 및 전장 시스템 완벽합니다."},
        {"overall_score": 87, "exterior_score": 85, "interior_score": 88, "engine_score": 88, "accident_history": "무사고", "estimated_price_low": 2700, "estimated_price_high": 3150, "report_summary": "배터리 SOH 95%. 전기차 특성상 엔진 정비가 불필요하여 관리 상태 우수."},
        {"overall_score": 93, "exterior_score": 94, "interior_score": 92, "engine_score": 93, "accident_history": "무사고", "estimated_price_low": 4800, "estimated_price_high": 5400, "report_summary": "제네시스 공식 서비스센터 정비 이력만 있는 관리 잘 된 차량입니다."},
        {"overall_score": 80, "exterior_score": 78, "interior_score": 82, "engine_score": 80, "accident_history": "무사고", "estimated_price_low": 2850, "estimated_price_high": 3350, "report_summary": "대형 SUV 특성상 외관 스크래치가 일부 있으나 기계적 상태는 양호합니다."},
        {"overall_score": 90, "exterior_score": 92, "interior_score": 88, "engine_score": 90, "accident_history": "무사고", "estimated_price_low": 3800, "estimated_price_high": 4300, "report_summary": "BMW 공식 딜러 정비 이력. 수입차 중 관리 상태 상위권입니다."},
        {"overall_score": 76, "exterior_score": 74, "interior_score": 78, "engine_score": 76, "accident_history": "무사고", "estimated_price_low": 1650, "estimated_price_high": 2050, "report_summary": "주행거리 대비 적정 상태입니다. 타이밍벨트 교체 이력 확인됨."},
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
        {"vehicle_idx": 1, "author": demo_user, "rating": 5, "review_type": "buyer",
         "content": "그랜저 르블랑 정말 만족합니다. 실내 관리가 잘 되어있고 엔진 소음도 거의 없어요. 추천합니다!"},
        {"vehicle_idx": 1, "author": seller2, "rating": 4, "review_type": "seller",
         "content": "좋은 분께 판매해서 기분이 좋습니다. 차 상태가 워낙 좋아서 빨리 팔렸어요."},
        {"vehicle_idx": 2, "author": seller2, "rating": 4, "review_type": "buyer",
         "content": "투싼 디젤 연비가 정말 좋습니다. 고속도로에서 특히 만족스러워요. 다만 DPF 관리는 신경써야 합니다."},
        {"vehicle_idx": 4, "author": demo_user, "rating": 5, "review_type": "buyer",
         "content": "팰리세이드 7인승 가족 여행에 최고입니다. 넓은 실내공간에 아이들도 편하게 탈 수 있어요."},
        {"vehicle_idx": 5, "author": seller2, "rating": 4, "review_type": "buyer",
         "content": "K5 디자인이 정말 예쁘고, 주행감도 좋습니다. 다만 뒷좌석이 약간 좁은 느낌이 있어요."},
        {"vehicle_idx": 7, "author": demo_user, "rating": 5, "review_type": "buyer",
         "content": "전기차 처음인데 EV6 정말 좋습니다. 충전도 빠르고 주행거리도 만족. 유지비가 거의 안 들어요."},
        {"vehicle_idx": 9, "author": seller2, "rating": 5, "review_type": "buyer",
         "content": "제네시스 G80 품격이 다릅니다. 조용하고 편안한 주행감, 제네시스 서비스도 최고입니다."},
        {"vehicle_idx": 11, "author": demo_user, "rating": 4, "review_type": "buyer",
         "content": "BMW 520i 주행 성능은 역시 BMW입니다. 다만 수입차라 유지비는 각오해야 합니다."},
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

    # 거래 이력 데이터 — 풍부한 더미데이터 (특히 NF소나타)
    now = datetime.utcnow()
    transactions_data = [
        # NF소나타 (idx 0) — 12개월간 거래 이력
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
        # 그랜저 (idx 1)
        {"vehicle_idx": 1, "days_ago": 20, "price": 3180, "mileage": 30000, "source": "carnerf", "buyer_region": "서울", "seller_region": "서울"},
        {"vehicle_idx": 1, "days_ago": 55, "price": 3250, "mileage": 27000, "source": "external", "buyer_region": "경기", "seller_region": "서울"},
        {"vehicle_idx": 1, "days_ago": 90, "price": 3100, "mileage": 35000, "source": "carnerf", "buyer_region": "경기", "seller_region": "서울"},
        {"vehicle_idx": 1, "days_ago": 140, "price": 3350, "mileage": 22000, "source": "external", "buyer_region": "서울", "seller_region": "인천"},
        {"vehicle_idx": 1, "days_ago": 200, "price": 3400, "mileage": 18000, "source": "carnerf", "buyer_region": "서울", "seller_region": "서울"},
        {"vehicle_idx": 1, "days_ago": 270, "price": 3500, "mileage": 12000, "source": "external", "buyer_region": "경기", "seller_region": "서울"},
        # 투싼 (idx 2)
        {"vehicle_idx": 2, "days_ago": 30, "price": 2750, "mileage": 20000, "source": "carnerf", "buyer_region": "서울", "seller_region": "경기"},
        {"vehicle_idx": 2, "days_ago": 75, "price": 2800, "mileage": 17000, "source": "external", "buyer_region": "경기", "seller_region": "경기"},
        {"vehicle_idx": 2, "days_ago": 150, "price": 2900, "mileage": 12000, "source": "carnerf", "buyer_region": "인천", "seller_region": "서울"},
        {"vehicle_idx": 2, "days_ago": 240, "price": 3000, "mileage": 8000, "source": "external", "buyer_region": "서울", "seller_region": "경기"},
        # 팰리세이드 (idx 4)
        {"vehicle_idx": 4, "days_ago": 25, "price": 4500, "mileage": 16000, "source": "carnerf", "buyer_region": "서울", "seller_region": "서울"},
        {"vehicle_idx": 4, "days_ago": 80, "price": 4550, "mileage": 13000, "source": "external", "buyer_region": "경기", "seller_region": "서울"},
        {"vehicle_idx": 4, "days_ago": 160, "price": 4650, "mileage": 9000, "source": "carnerf", "buyer_region": "서울", "seller_region": "경기"},
        {"vehicle_idx": 4, "days_ago": 250, "price": 4800, "mileage": 5000, "source": "external", "buyer_region": "부산", "seller_region": "서울"},
        # K5 (idx 5)
        {"vehicle_idx": 5, "days_ago": 40, "price": 2300, "mileage": 30000, "source": "carnerf", "buyer_region": "부산", "seller_region": "부산"},
        {"vehicle_idx": 5, "days_ago": 120, "price": 2200, "mileage": 32000, "source": "external", "buyer_region": "부산", "seller_region": "부산"},
        {"vehicle_idx": 5, "days_ago": 200, "price": 2450, "mileage": 20000, "source": "carnerf", "buyer_region": "서울", "seller_region": "경기"},
        {"vehicle_idx": 5, "days_ago": 310, "price": 2550, "mileage": 14000, "source": "external", "buyer_region": "대구", "seller_region": "부산"},
        # EV6 (idx 7)
        {"vehicle_idx": 7, "days_ago": 18, "price": 4150, "mileage": 13000, "source": "carnerf", "buyer_region": "서울", "seller_region": "서울"},
        {"vehicle_idx": 7, "days_ago": 60, "price": 4050, "mileage": 15000, "source": "carnerf", "buyer_region": "서울", "seller_region": "서울"},
        {"vehicle_idx": 7, "days_ago": 130, "price": 4250, "mileage": 9000, "source": "external", "buyer_region": "경기", "seller_region": "서울"},
        {"vehicle_idx": 7, "days_ago": 220, "price": 4400, "mileage": 5000, "source": "carnerf", "buyer_region": "서울", "seller_region": "인천"},
        # G80 (idx 9)
        {"vehicle_idx": 9, "days_ago": 45, "price": 5100, "mileage": 27000, "source": "carnerf", "buyer_region": "서울", "seller_region": "서울"},
        {"vehicle_idx": 9, "days_ago": 100, "price": 5000, "mileage": 30000, "source": "external", "buyer_region": "서울", "seller_region": "서울"},
        {"vehicle_idx": 9, "days_ago": 180, "price": 5300, "mileage": 20000, "source": "carnerf", "buyer_region": "경기", "seller_region": "서울"},
        # BMW 520i (idx 11)
        {"vehicle_idx": 11, "days_ago": 50, "price": 4000, "mileage": 22000, "source": "carnerf", "buyer_region": "서울", "seller_region": "서울"},
        {"vehicle_idx": 11, "days_ago": 150, "price": 3900, "mileage": 25000, "source": "carnerf", "buyer_region": "경기", "seller_region": "서울"},
        {"vehicle_idx": 11, "days_ago": 280, "price": 4200, "mileage": 15000, "source": "external", "buyer_region": "서울", "seller_region": "서울"},
        # QM6 (idx 12)
        {"vehicle_idx": 12, "days_ago": 60, "price": 1800, "mileage": 43000, "source": "external", "buyer_region": "대전", "seller_region": "대전"},
        {"vehicle_idx": 12, "days_ago": 180, "price": 1900, "mileage": 38000, "source": "carnerf", "buyer_region": "서울", "seller_region": "대전"},
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
