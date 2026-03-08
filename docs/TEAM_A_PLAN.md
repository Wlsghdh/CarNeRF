# 팀원 A 업무 계획서
## 담당: 데이터 크롤링 + 가격 예측 (ML)

---

## 1. 역할 요약

| 항목 | 내용 |
|------|------|
| **담당 분야** | 중고차 데이터 수집 + ML 기반 가격 예측 API |
| **최종 산출물** | ① 중고차 DB 1만 건+ ② 가격 예측 API (`POST /api/predict/price`) |
| **연동 대상** | 팀장(백엔드 API 연동), 팀원 B(결함 점수 → 가격 보정 입력) |
| **주요 기술** | Python, Selenium/BeautifulSoup, Pandas, LightGBM, FastAPI |

---

## 2. 전체 개발 흐름

```
[1단계] 데이터 수집
 엔카 / K카 / 차차차 크롤링
        ↓
[2단계] 데이터 정제
 결측치 처리, 이상치 제거, 특징 정규화
        ↓
[3단계] EDA + Feature Engineering
 가격에 영향 주는 변수 분석, 파생 변수 생성
        ↓
[4단계] 모델 학습 + 검증
 LightGBM / XGBoost / Random Forest 비교
        ↓
[5단계] API 배포
 FastAPI 엔드포인트 → 팀장 백엔드에 연동
```

---

## 3. Sprint 계획 (4주)

### Week 1: 크롤러 개발 + 데이터 수집

#### 목표
- 엔카(encar.com) 크롤러 완성
- 1,000건 이상 수집 → DB 저장 확인

#### 세부 Task

**[Task A-1-1] 크롤링 환경 세팅**
```bash
pip install selenium beautifulsoup4 requests pandas sqlalchemy
# Chrome + chromedriver 설치 (headless 모드)
# 또는 playwright 사용 (더 안정적)
pip install playwright && playwright install chromium
```

**[Task A-1-2] 엔카 크롤러 구현** (`scripts/crawling/encar_crawler.py`)

수집 대상 필드:
| 필드명 | 설명 | 예시 |
|--------|------|------|
| `brand` | 브랜드 | 현대, 기아, BMW |
| `model` | 모델명 | 그랜저, K5, 5시리즈 |
| `year` | 연식 | 2021 |
| `mileage` | 주행거리(km) | 45000 |
| `price` | 가격(만원) | 2850 |
| `fuel_type` | 연료 | 가솔린, 디젤, 전기, 하이브리드 |
| `transmission` | 변속기 | 자동, 수동 |
| `region` | 지역 | 서울, 경기, 부산 |
| `color` | 색상 | 흰색, 검정, 은색 |
| `accident_count` | 사고 횟수 | 0, 1, 2 |
| `options` | 주요 옵션 목록 | 썬루프, 네비, 후방카메라 |
| `thumbnail_url` | 썸네일 이미지 URL | https://... |
| `source_url` | 원본 매물 링크 | https://encar.com/... |
| `crawled_at` | 수집 시각 | 2026-02-23 10:00 |

**[Task A-1-3] K카(kcar.com) 크롤러 구현**
- 엔카와 구조 유사, 클래스명만 다름
- 데이터 통합 시 중복 제거 (브랜드+모델+연식+주행거리 기준)

**[Task A-1-4] robots.txt 준수 + Rate Limiting**
```python
import time, random
# 요청 간 1~3초 랜덤 대기 (서버 부하 방지, 차단 예방)
time.sleep(random.uniform(1, 3))
# User-Agent 설정
headers = {'User-Agent': 'Mozilla/5.0 ...'}
```

**[Task A-1-5] 수집 데이터 → SQLite 저장**
```python
# scripts/crawling/save_to_db.py
# carnerf.db의 Vehicle 테이블에 upsert
```

---

### Week 2: 데이터 정제 + EDA

#### 목표
- 수집 데이터 5,000건 이상
- 분석용 정제 데이터셋 완성
- EDA 노트북 완성

#### 세부 Task

**[Task A-2-1] 데이터 정제** (`notebooks/01_data_cleaning.ipynb`)

처리 사항:
```python
# 1. 결측치 처리
df['mileage'].fillna(df['mileage'].median(), inplace=True)

# 2. 이상치 제거
df = df[(df['price'] > 100) & (df['price'] < 20000)]   # 100~2억
df = df[(df['mileage'] >= 0) & (df['mileage'] < 500000)]

# 3. 문자열 정규화
df['brand'] = df['brand'].str.strip().str.upper()
df['fuel_type'] = df['fuel_type'].map({'가솔린':'gasoline', '디젤':'diesel', ...})

# 4. 중복 제거
df = df.drop_duplicates(subset=['brand', 'model', 'year', 'mileage', 'price'])
```

**[Task A-2-2] EDA 분석** (`notebooks/02_eda.ipynb`)

분석 항목:
- 브랜드별 평균 가격 분포 (boxplot)
- 연식 vs 가격 상관관계 (scatter)
- 주행거리 vs 가격 상관관계
- 연료 타입별 가격 차이
- 사고 이력 유무 → 가격 영향도
- 지역별 가격 차이
- 인기 옵션 순위 (원핫 인코딩 후 상관계수)

**[Task A-2-3] Feature Engineering** (`notebooks/03_feature_engineering.ipynb`)

파생 변수 생성:
```python
# 차량 나이 (현재 연도 - 연식)
df['car_age'] = 2026 - df['year']

# 연간 주행거리 (주행거리 / 차량 나이)
df['annual_mileage'] = df['mileage'] / (df['car_age'] + 0.5)

# 브랜드 등급 (국산/수입, 럭셔리/일반)
df['brand_tier'] = df['brand'].map({'현대': 1, 'BMW': 3, ...})

# 옵션 점수 (주요 옵션 개수 합산)
key_options = ['썬루프', '네비', '열선시트', '통풍시트', '스마트키']
df['option_score'] = df['options'].apply(lambda x: sum(1 for o in key_options if o in x))
```

---

### Week 3: ML 모델 학습 + 최적화

#### 목표
- RMSE 100만원 이하 달성
- 모델 저장 + 로딩 코드 완성

#### 세부 Task

**[Task A-3-1] 데이터 분할**
```python
from sklearn.model_selection import train_test_split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
```

**[Task A-3-2] 모델 1: LightGBM** (`notebooks/04_model_lgbm.ipynb`)
```python
import lightgbm as lgb
params = {
    'objective': 'regression',
    'metric': 'rmse',
    'num_leaves': 127,
    'learning_rate': 0.05,
    'feature_fraction': 0.8,
    'bagging_fraction': 0.8,
    'bagging_freq': 5,
    'n_estimators': 1000,
}
model = lgb.LGBMRegressor(**params)
model.fit(X_train, y_train,
          eval_set=[(X_test, y_test)],
          callbacks=[lgb.early_stopping(50)])
```

**[Task A-3-3] 모델 2: XGBoost 비교**
```python
from xgboost import XGBRegressor
model_xgb = XGBRegressor(n_estimators=1000, learning_rate=0.05, ...)
```

**[Task A-3-4] 모델 3: Optuna 하이퍼파라미터 튜닝**
```python
import optuna
def objective(trial):
    params = {
        'num_leaves': trial.suggest_int('num_leaves', 20, 300),
        'learning_rate': trial.suggest_float('learning_rate', 1e-4, 0.3, log=True),
        ...
    }
    # cross-validation RMSE 반환
study = optuna.create_study(direction='minimize')
study.optimize(objective, n_trials=100)
```

**[Task A-3-5] 모델 평가 지표**
| 지표 | 목표값 |
|------|--------|
| RMSE | < 100만원 |
| MAE | < 70만원 |
| R² | > 0.90 |
| MAPE | < 8% |

**[Task A-3-6] 모델 저장**
```python
import joblib
joblib.dump(model, 'backend/app/models/price_predictor.pkl')
joblib.dump(scaler, 'backend/app/models/scaler.pkl')
joblib.dump(encoder, 'backend/app/models/encoder.pkl')
```

---

### Week 4: API 구현 + 연동

#### 목표
- `POST /api/predict/price` 엔드포인트 완성
- 팀장 백엔드와 통합 완료
- 차량 상세 페이지에 예측가격 표시

#### 세부 Task

**[Task A-4-1] 예측 API 구현** (`backend/app/api/predict.py`)

```python
from fastapi import APIRouter
import joblib, numpy as np

router = APIRouter()
model = joblib.load('app/models/price_predictor.pkl')

class PriceRequest(BaseModel):
    brand: str
    model: str
    year: int
    mileage: int
    fuel_type: str
    transmission: str
    accident_count: int
    options: list[str] = []
    # 팀원 B에서 받는 결함 점수 (선택)
    defect_score: float = 0.0   # 0~100, 결함 심각도

class PriceResponse(BaseModel):
    predicted_price: int        # 예측 중간값 (만원)
    price_range_low: int        # 하한 (만원)
    price_range_high: int       # 상한 (만원)
    confidence: float           # 신뢰도 (0~1)
    similar_listings: list      # 유사 매물 3개
    depreciation_curve: list    # 감가상각 곡선 데이터

@router.post('/api/predict/price', response_model=PriceResponse)
async def predict_price(req: PriceRequest):
    features = preprocess(req)
    pred = model.predict(features)[0]
    # 결함 점수 반영: defect_score 10점당 3% 감가
    adj = pred * (1 - req.defect_score * 0.003)
    return PriceResponse(
        predicted_price=int(adj),
        price_range_low=int(adj * 0.92),
        price_range_high=int(adj * 1.08),
        confidence=0.87,
        ...
    )
```

**[Task A-4-2] 입력 전처리 함수**
```python
def preprocess(req: PriceRequest) -> np.ndarray:
    # 인코딩, 스케일링, 파생변수 계산
    car_age = 2026 - req.year
    annual_mileage = req.mileage / (car_age + 0.5)
    ...
```

**[Task A-4-3] 유사 매물 검색**
```python
# DB에서 비슷한 조건의 매물 3개 반환 (참고 가격)
# brand + model 동일, 연식 ±2년, 주행거리 ±2만km
```

**[Task A-4-4] 감가상각 곡선**
```python
# 현재 차량의 향후 5년 예측 가격 데이터 반환
# [{year: 2026, price: 2850}, {year: 2027, price: 2600}, ...]
# 팀장이 차량 상세페이지 그래프에 표시
```

**[Task A-4-5] 팀장 백엔드 연동 확인**
- `/api/predict/price` 라우터를 `backend/app/main.py`에 include
- 차량 상세 페이지(`vehicle_detail.html`)의 AI 가격 구간 바에 실제 예측값 연결

---

## 4. 최종 산출물 목록

| 산출물 | 경로 | 설명 |
|--------|------|------|
| 크롤러 | `scripts/crawling/encar_crawler.py` | 엔카 크롤러 |
| 크롤러 | `scripts/crawling/kcar_crawler.py` | K카 크롤러 |
| 데이터셋 | `data/car_prices.csv` | 정제된 중고차 가격 데이터 |
| EDA 노트북 | `notebooks/02_eda.ipynb` | 분석 결과 시각화 |
| 학습 노트북 | `notebooks/04_model_lgbm.ipynb` | 모델 학습 코드 |
| 모델 파일 | `backend/app/models/price_predictor.pkl` | 학습된 모델 |
| API | `backend/app/api/predict.py` | 예측 엔드포인트 |

---

## 5. 팀원 B와 협업 포인트

팀원 B가 제공하는 결함 점수를 가격 예측에 반영:
```
팀원 B: AI 결함 분석 → defect_score (0~100)
                        ↓
팀원 A: 가격 예측 API에 defect_score 입력 파라미터 추가
        → 결함 심각도 비례 가격 하향 조정
        → "결함 없을 때 예측가" vs "현재 결함 반영가" 비교 출력
```

---

## 6. 참고 자료

- **엔카 API**: https://api.encar.com (공식 API 아닌 경우 크롤링)
- **데이터셋 대안**: Kaggle "Used Car Price Prediction" (해외, 구조 참고용)
- **LightGBM 문서**: https://lightgbm.readthedocs.io
- **Optuna**: https://optuna.org
- **참고 논문**: "XGBoost: A Scalable Tree Boosting System" (Chen & Guestrin, 2016)
