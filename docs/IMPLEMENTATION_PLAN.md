# CarNeRF 추가 기능 구현 계획서
## Feature 1: 자동차 가격 예측 회귀 모델 | Feature 2: 결함 탐지 + 3D 마커

---

## Feature 1: 자동차 가격 예측 회귀 모델

### 1-1. 개요

| 항목 | 내용 |
|------|------|
| **목표** | 차량 스펙(연식, 주행거리, 브랜드 등) + 결함 점수 → 가격 예측 |
| **산출물** | `POST /api/predict/price` API + 학습된 모델 `.pkl` |
| **모델** | LightGBM / XGBoost 비교 → 최적 모델 선택 |
| **목표 성능** | RMSE < 100만원, R² > 0.90, MAPE < 8% |

### 1-2. 데이터 확보 전략

| 우선순위 | 방법 | 소스 | 예상 건수 | 비고 |
|---------|------|------|----------|------|
| 1 | **공개 데이터셋** | Kaggle "Korean Used Car" 등 | 5,000~50,000 | 가장 빠름 |
| 2 | **엔카 크롤링** | encar.com | 10,000+ | robots.txt 준수, rate limiting 필수 |
| 3 | **K카 크롤링** | kcar.com | 5,000+ | 엔카와 구조 유사 |
| 4 | **합성 데이터** | 실제 시세 기반 통계적 생성 | 보완용 | 데이터 부족 시 |

**수집 대상 필드:**

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
| `engine_cc` | 배기량 | 2000 |
| `accident_count` | 사고 횟수 | 0, 1, 2 |
| `options` | 주요 옵션 | 썬루프, 네비, 후방카메라 |
| `trim` | 트림 | 프리미엄, 익스클루시브 |

### 1-3. 모델 개발 파이프라인

```
data/car_prices.csv
    ↓
[notebooks/01_data_cleaning.ipynb]
  - 결측치 처리 (중위값 대체)
  - 이상치 제거 (price 100~20,000만원, mileage 0~500,000km)
  - 문자열 정규화 (brand strip/upper, fuel_type 매핑)
  - 중복 제거 (brand+model+year+mileage+price 기준)
    ↓
[notebooks/02_eda.ipynb]
  - 브랜드별 평균 가격 분포 (boxplot)
  - 연식 vs 가격 상관관계 (scatter)
  - 주행거리 vs 가격 상관관계
  - 연료 타입별 가격 차이
  - 사고 이력 유무 → 가격 영향도
  - 지역별 가격 차이
    ↓
[notebooks/03_feature_engineering.ipynb]
  - car_age = 2026 - year
  - annual_mileage = mileage / (car_age + 0.5)
  - brand_tier (국산 1 / 수입일반 2 / 럭셔리 3)
  - option_score (주요 옵션 개수 합산)
    ↓
[notebooks/04_model_train.ipynb]
  - train/test split (80/20)
  - LightGBM vs XGBoost vs RandomForest 비교
  - Optuna 하이퍼파라미터 튜닝 (100 trials)
  - 교차 검증 (5-fold CV)
    ↓
joblib.dump →
  backend/app/ml_models/price_predictor.pkl
  backend/app/ml_models/scaler.pkl
  backend/app/ml_models/encoder.pkl
```

### 1-4. 모델 학습 상세

**LightGBM 기본 파라미터:**
```python
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
```

**Optuna 튜닝 범위:**
```python
{
    'num_leaves': (20, 300),
    'learning_rate': (1e-4, 0.3),     # log scale
    'feature_fraction': (0.5, 1.0),
    'bagging_fraction': (0.5, 1.0),
    'min_child_samples': (5, 100),
    'reg_alpha': (1e-8, 10.0),        # log scale
    'reg_lambda': (1e-8, 10.0),       # log scale
}
```

**평가 지표 목표:**

| 지표 | 목표값 |
|------|--------|
| RMSE | < 100만원 |
| MAE | < 70만원 |
| R² | > 0.90 |
| MAPE | < 8% |

### 1-5. API 구현

**엔드포인트:** `POST /api/predict/price`

**파일:** `backend/app/api/predict.py`

**Request:**
```json
{
    "brand": "현대",
    "model": "그랜저",
    "year": 2021,
    "mileage": 45000,
    "fuel_type": "가솔린",
    "transmission": "자동",
    "accident_count": 0,
    "options": ["썬루프", "네비"],
    "defect_score": 0.0
}
```

**Response:**
```json
{
    "predicted_price": 2850,
    "price_range_low": 2622,
    "price_range_high": 3078,
    "confidence": 0.87,
    "similar_listings": [
        {"title": "그랜저 2020 ...", "price": 2700, "mileage": 52000},
        {"title": "그랜저 2021 ...", "price": 2950, "mileage": 38000},
        {"title": "그랜저 2022 ...", "price": 3100, "mileage": 21000}
    ],
    "depreciation_curve": [
        {"year": 2026, "price": 2850},
        {"year": 2027, "price": 2600},
        {"year": 2028, "price": 2380},
        {"year": 2029, "price": 2190},
        {"year": 2030, "price": 2020}
    ]
}
```

**결함 점수 반영 로직:**
```
결함 반영 예측가 = 기본 예측가 × (1 - defect_score × 0.003)
→ defect_score 10점당 약 3% 감가
```

### 1-6. 프론트엔드 연동

- `vehicle_detail.html`의 AI 가격 구간 바에 실제 예측값 연결
- 감가상각 곡선 그래프 (Chart.js 또는 inline SVG)
- 유사 매물 비교 카드 3개 표시
- "결함 반영가 vs 무결함 예측가" 비교 UI

### 1-7. 파일 구조

```
scripts/crawling/
├── encar_crawler.py              # 엔카 크롤러
├── kcar_crawler.py               # K카 크롤러
└── save_to_db.py                 # 정제 후 DB/CSV 저장

notebooks/
├── 01_data_cleaning.ipynb        # 데이터 정제
├── 02_eda.ipynb                  # 탐색적 분석
├── 03_feature_engineering.ipynb  # 파생 변수 생성
└── 04_model_train.ipynb          # 모델 학습 + 튜닝

data/
└── car_prices.csv                # 정제된 중고차 가격 데이터셋

backend/app/
├── ml_models/
│   ├── price_predictor.pkl       # 학습된 LightGBM 모델
│   ├── scaler.pkl                # 스케일러
│   └── encoder.pkl               # 카테고리 인코더
└── api/
    └── predict.py                # 가격 예측 API 엔드포인트
```

---

## Feature 2: 결함 탐지 + 3D 모델 마커

### 2-1. 개요

| 항목 | 내용 |
|------|------|
| **목표** | 차량 영상 프레임에서 결함 자동 탐지 → 3D 뷰어에서 마커로 표시 → 클릭 시 원본 사진 확인 |
| **산출물** | YOLOv8 결함 탐지 모델 + 결함 분석 API + 3D 마커 오버레이 |
| **탐지 대상** | 6종: scratch, dent, paint_damage, rust, glass_crack, bumper_damage |
| **목표 성능** | mAP50 > 0.65, 추론 < 100ms/장 |

### 2-2. 사용자 경험 흐름 (UX Flow)

```
① 사용자가 차량 30~60초 영상 업로드 (/sell 페이지)
    ↓
② 기존 파이프라인 실행 (프레임 추출 → COLMAP → 3DGS → model.splat)
    ↓ (동시에)
③ 추출된 프레임에 YOLOv8 결함 탐지 실행
    ↓
④ 결함 2D bbox + COLMAP 카메라 포즈 → 3D 월드 좌표로 역투영
    ↓
⑤ defects.json 생성 (3D 위치, 결함 유형, 심각도, 원본 이미지 경로)
    ↓
⑥ 3D 뷰어에서 결함 위치에 마커 버튼 표시
    ↓
⑦ 마커 클릭 → 모달 팝업으로 원본 사진 + 결함 bbox 하이라이트 표시
    ↓
⑧ "이 부분에 결함 의심이 있습니다" 안내
```

### 2-3. 데이터 확보 전략

| 우선순위 | 데이터셋 | 설명 | 건수 |
|---------|---------|------|------|
| 1 | **CarDD** | CVPR Workshop 논문, bbox 어노테이션 포함 | 4,000+ |
| 2 | **Kaggle VehiDE** | 차량 손상 자동 탐지용 | 1,900+ |
| 3 | **Google 이미지 크롤링** | "차량 스크래치", "car dent" 등 검색어 | 보완용 |
| 4 | **자체 촬영** | 실제 중고차 매장 방문 촬영 | 보완용 |

**데이터셋 다운로드:**
- CarDD: https://cardd-ustc.github.io
- VehiDE: https://www.kaggle.com/datasets/hendrichscullen/vehide-dataset-automatic-vehicle-damage-detection

**6개 탐지 클래스:**

| 클래스 | 한글명 | 심각도 기준 |
|--------|-------|------------|
| `scratch` | 스크래치/긁힘 | 길이 10cm+ = 중, 30cm+ = 심각 |
| `dent` | 찌그러짐/덴트 | 지름 5cm+ = 중, 15cm+ = 심각 |
| `paint_damage` | 도색 이상/탈색 | 면적 5% = 중, 15%+ = 심각 |
| `rust` | 부식/녹 | 존재 = 중, 관통 = 심각 |
| `glass_crack` | 유리 균열 | 시야 방해 여부 |
| `bumper_damage` | 범퍼 파손 | 변형 여부 |

### 2-4. 모델 학습

**모델 선택: YOLOv8s** (속도/정확도 균형)

| 모델 | 파라미터 | 속도 | 정확도 |
|------|---------|------|--------|
| YOLOv8n | 3.2M | ★★★★★ | ★★★ |
| **YOLOv8s** | **11.2M** | **★★★★** | **★★★★** |
| YOLOv8m | 25.9M | ★★★ | ★★★★★ |

**학습 설정:**
```python
from ultralytics import YOLO

model = YOLO('yolov8s.pt')    # pretrained
results = model.train(
    data='cardd.yaml',
    epochs=100,
    imgsz=640,
    batch=32,                  # A100 80GB → 큰 배치 가능
    device=0,
    project='runs/defect',
    name='yolov8s_cardd',
    patience=20,               # early stopping
    # augmentation
    hsv_h=0.015,
    hsv_s=0.7,
    hsv_v=0.4,
    degrees=10,
    fliplr=0.5,
    mosaic=1.0,
)
```

**목표 성능:**

| 지표 | 목표 |
|------|------|
| mAP50 | > 0.65 |
| mAP50-95 | > 0.40 |
| Precision | > 0.70 |
| Recall | > 0.60 |
| 추론 속도 | < 100ms/장 (GPU) |

### 2-5. 심각도 점수 계산

```python
WEIGHTS = {
    'scratch': 1.0,
    'dent': 2.5,
    'paint_damage': 1.5,
    'rust': 3.0,
    'glass_crack': 4.0,
    'bumper_damage': 2.0,
}

# 결함별: weight × (bbox 면적 / 전체 면적) × confidence × 100
# 종합 점수: 합산 후 min(total, 100)
# 심각도: 0~20 경미 / 20~50 중간 / 50~100 심각
```

### 2-6. 핵심 구현: 2D → 3D 역투영

**COLMAP 카메라 포즈 파싱:**
```python
reconstruction = pycolmap.Reconstruction(colmap_sparse_path)
# 각 프레임의 R(회전), T(이동), K(내부파라미터) 추출
```

**역투영 로직:**
```
결함 bbox 중심점 (px, py)
    ↓
카메라 내부파라미터 K 역변환 → 카메라 좌표계 점
    ↓
깊이값 d (Depth Anything V2 결과) 곱하기
    ↓
카메라 외부파라미터 R, T 역변환 → 월드 좌표계 (x, y, z)
```

**여러 프레임에서 같은 결함 감지 시:**
- 다중 뷰 triangulation으로 3D 위치 정확도 향상
- 같은 결함의 여러 각도 사진 중 가장 선명한 것을 대표 이미지로 선택

### 2-7. defects.json 구조

```json
{
    "vehicle_id": 19,
    "total_defect_score": 34.5,
    "severity_level": "중간",
    "defect_count": 3,
    "defects": [
        {
            "id": 1,
            "type": "scratch",
            "type_kr": "스크래치",
            "severity": "중간",
            "confidence": 0.87,
            "position_3d": [0.23, -0.15, 0.41],
            "marker_color": "#F59E0B",
            "source_frame": "frame_0042.jpg",
            "bbox_2d": [120, 340, 280, 410],
            "annotated_image_url": "/static/models/vehicle_19/defect_1.jpg",
            "description": "좌측 앞 도어에 약 15cm 스크래치 발견"
        },
        {
            "id": 2,
            "type": "dent",
            "type_kr": "덴트",
            "severity": "경미",
            "confidence": 0.72,
            "position_3d": [-0.45, 0.10, 0.22],
            "marker_color": "#10B981",
            "source_frame": "frame_0078.jpg",
            "bbox_2d": [450, 200, 520, 280],
            "annotated_image_url": "/static/models/vehicle_19/defect_2.jpg",
            "description": "후면 범퍼 우측 소형 덴트"
        }
    ]
}
```

### 2-8. 3D 뷰어 마커 UI

**마커 표시:**
- Three.js 구체(Sphere) 메시를 결함 3D 위치에 배치
- 색상: 경미(#10B981 초록) / 중간(#F59E0B 노란) / 심각(#EF4444 빨강)
- 반투명 + pulse 애니메이션으로 눈에 띄게

**마커 클릭 시 모달:**
```
┌─────────────────────────────────────────┐
│  ⚠️ 결함 발견: 스크래치 (중간)            │
│                                         │
│  ┌─────────────────────────────────┐    │
│  │                                 │    │
│  │   [원본 사진 + bbox 하이라이트]    │    │
│  │                                 │    │
│  └─────────────────────────────────┘    │
│                                         │
│  유형: 스크래치 (scratch)                 │
│  심각도: 중간                             │
│  신뢰도: 87%                             │
│  설명: 좌측 앞 도어에 약 15cm 스크래치 발견  │
│                                         │
│                            [닫기]        │
└─────────────────────────────────────────┘
```

**뷰어 컨트롤:**
- "결함 마커 표시" 토글 버튼
- 결함 목록 사이드패널 (클릭하면 해당 마커로 카메라 이동)

### 2-9. API 엔드포인트

**1) 단일 이미지 분석**
```
POST /api/defect/analyze
  Input:  이미지 파일 (multipart/form-data)
  Output: defect_score, severity_level, detections[], annotated_image(base64), summary
```

**2) 다중 이미지 배치 분석**
```
POST /api/defect/analyze-batch
  Input:  이미지 파일 여러 장
  Output: 차량 전체 종합 결함 점수 + 개별 결함 목록
```

**3) 3D 뷰어용 결함 위치**
```
GET /api/vehicles/{id}/defects
  Output: defects.json 내용 (3D 위치 + 결함 정보)
```

### 2-10. 파이프라인 통합

기존 `scripts/run_pipeline.py` 흐름에 결함 분석 단계 추가:

```
영상 → extract_frames.py → run_colmap.py
                              ↓
                    [기존] train_gaussian.py → export_model.py → model.splat
                              ↓
                    [추가] defect_analysis.py
                         ├─ 각 프레임에 YOLOv8 추론
                         ├─ 결함 있는 프레임 필터링
                         ├─ COLMAP 포즈로 3D 역투영
                         ├─ 어노테이트 이미지 생성/저장
                         └─ defects.json 저장
```

### 2-11. 파일 구조

```
scripts/defect_detection/
├── datasets/
│   ├── images/
│   │   ├── train/                # 학습 이미지 (80%)
│   │   ├── val/                  # 검증 이미지 (15%)
│   │   └── test/                 # 테스트 이미지 (5%)
│   └── labels/
│       ├── train/                # YOLO 형식 레이블
│       ├── val/
│       └── test/
├── cardd.yaml                    # 데이터셋 설정 파일
├── train.py                      # YOLOv8 학습 스크립트
├── inference.py                  # 추론 + 심각도 계산
├── backproject.py                # 2D→3D 역투영 모듈
└── pipeline_integration.py       # 파이프라인 연동 (자동 결함 분석)

backend/app/
├── ml_models/
│   ├── defect_detector.pt        # 학습된 YOLOv8s 모델
│   └── sam_vit_h.pth             # SAM 가중치 (선택)
├── api/
│   └── defect.py                 # 결함 분석 API 엔드포인트
├── static/models/{vehicle_name}/
│   ├── model.splat               # 기존 3D 모델
│   ├── defects.json              # 결함 3D 위치 데이터
│   └── defect_*.jpg              # 결함 어노테이트된 원본 사진
└── templates/
    └── vehicle_detail.html       # 결함 마커 + 모달 UI 추가
```

---

## 두 Feature 연동 구조

```
Feature 2: 결함 탐지
  └─ defect_score (0~100) ──→ Feature 1: 가격 예측 API에 입력
                                  ↓
                              결함 반영 예측가 = 기본가 × (1 - defect_score × 0.003)
                                  ↓
                              차량 상세페이지에 표시:
                              ┌──────────────────────────────┐
                              │ 무결함 예측가:  2,850만원       │
                              │ 결함 반영 예측가: 2,420만원     │
                              │ 결함 감가:      -430만원       │
                              └──────────────────────────────┘
```

---

## 작업 일정 (4주)

### Week 1: 데이터 확보

| Task | Feature | 내용 | 산출물 |
|------|---------|------|--------|
| W1-1 | F1 | Kaggle 한국 중고차 데이터 탐색/다운로드 | `data/car_prices.csv` |
| W1-2 | F1 | (데이터 없으면) 엔카 크롤러 개발 | `scripts/crawling/encar_crawler.py` |
| W1-3 | F1 | 데이터 정제 + EDA | `notebooks/01~02` |
| W1-4 | F2 | CarDD 데이터셋 다운로드 + YOLO 형식 변환 | `scripts/defect_detection/datasets/` |
| W1-5 | F2 | ultralytics, segment-anything 설치 | 환경 세팅 완료 |

### Week 2: 모델 학습

| Task | Feature | 내용 | 산출물 |
|------|---------|------|--------|
| W2-1 | F1 | Feature Engineering | `notebooks/03` |
| W2-2 | F1 | LightGBM/XGBoost 학습 + Optuna 튜닝 | `notebooks/04` |
| W2-3 | F1 | 모델 저장 | `backend/app/ml_models/price_predictor.pkl` |
| W2-4 | F2 | YOLOv8s 학습 (A100, ~2시간) | `runs/defect/yolov8s_cardd/` |
| W2-5 | F2 | SAM 마스크 통합 + 심각도 알고리즘 | `scripts/defect_detection/inference.py` |

### Week 3: API 구현 + 연동

| Task | Feature | 내용 | 산출물 |
|------|---------|------|--------|
| W3-1 | F1 | `/api/predict/price` 구현 | `backend/app/api/predict.py` |
| W3-2 | F1 | 유사 매물 검색 + 감가상각 곡선 로직 | predict.py 내 함수 |
| W3-3 | F1 | main.py에 라우터 등록 + 테스트 | API 동작 확인 |
| W3-4 | F2 | `/api/defect/analyze` 구현 | `backend/app/api/defect.py` |
| W3-5 | F2 | 2D→3D 역투영 모듈 | `scripts/defect_detection/backproject.py` |
| W3-6 | F2 | 파이프라인 통합 (자동 결함 분석) | `pipeline_integration.py` |

### Week 4: 프론트엔드 + 통합

| Task | Feature | 내용 | 산출물 |
|------|---------|------|--------|
| W4-1 | F1 | vehicle_detail.html에 예측가 표시 | AI 가격 바 실데이터 연동 |
| W4-2 | F1 | 감가상각 그래프 + 유사 매물 카드 | Chart.js 그래프 |
| W4-3 | F2 | 3D 뷰어 마커 오버레이 (Three.js) | viewer.js 마커 기능 |
| W4-4 | F2 | 마커 클릭 → 원본 사진 모달 | vehicle_detail.html 모달 UI |
| W4-5 | F1+F2 | defect_score → 가격 예측 연동 | 무결함가 vs 결함반영가 비교 |
| W4-6 | 전체 | 통합 테스트 + 버그 수정 | 전체 흐름 동작 확인 |

---

## 필요 패키지

```bash
# Feature 1: 가격 예측
pip install lightgbm xgboost optuna scikit-learn joblib pandas

# Feature 2: 결함 탐지
pip install ultralytics opencv-python-headless
pip install segment-anything   # SAM (선택)

# 크롤링 (데이터 수집 시)
pip install selenium beautifulsoup4 requests playwright
```

---

## 기존 DB 모델과의 관계

현재 `DiagnosisReport` 모델에 이미 다음 필드가 존재:
- `overall_score`, `exterior_score`, `interior_score`, `engine_score`
- `accident_history`
- `estimated_price_low`, `estimated_price_high`
- `report_summary`

→ Feature 1의 예측 결과를 `estimated_price_low/high`에 저장
→ Feature 2의 결함 점수를 `exterior_score`에 반영
→ 추가 필드가 필요하면 `DiagnosisReport`에 `defect_score`, `defect_details_json` 컬럼 추가
