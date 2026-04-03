# Backend API Skill

## 역할
FastAPI 엔드포인트 관리, DB 모델, 인증, 비즈니스 로직

## 구조
```
backend/app/
├── api/           # 라우터 (auth, vehicles, listings, pipeline, predict, defect, ai_summary, market_price, wishlist, upload, points, reviews, transactions, seller)
├── models.py      # SQLAlchemy (User, Vehicle, Listing, DiagnosisReport, Wishlist, LoginHistory, ...)
├── schemas.py     # Pydantic 스키마
├── dependencies.py # JWT, 비밀번호, get_current_user
├── config.py      # SECRET_KEY, DB URL, CORS
├── services/      # seed_data.py
└── templates/     # Jinja2 SSR
```

## 서버 실행
```bash
cd backend && python run.py  # http://localhost:8000
```

## DB
SQLite `backend/carnerf.db`, 자동 생성 + 시드 (12대 차량, 5명 유저)

## 인증
Cookie JWT (`access_token`), SHA256+salt, 24시간 만료
