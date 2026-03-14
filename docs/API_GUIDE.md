# CarNeRF AI 모델 & API 가이드

## 디렉토리 구조

```
Project_2026_1/
├── scripts/                          # 🔧 학습 스크립트 (Agent 1, 2 작업)
│   ├── train_price_model.py          # 가격예측 모델 학습
│   ├── train_defect_model.py         # 결함탐지 모델 학습
│   └── crawling/
│       └── encar_crawler.py          # 엔카 크롤링 (학습 데이터)
│
├── data/                             # 📊 학습 데이터
│   ├── car_prices.csv                # 가격예측 학습 데이터 (5만건, 엔카)
│   └── defect_detection/
│       └── vehide/                   # 결함탐지 학습 데이터 (VeHIDE)
│
├── backend/
│   └── app/
│       ├── ml_models/                # 🎯 모델 파일 저장 위치 (여기에 .pt/.pkl 넣기)
│       │   ├── price_predictor.pkl   # 가격예측 모델 (LightGBM/XGBoost)
│       │   ├── price_encoders.pkl    # 라벨 인코더
│       │   ├── price_features.pkl    # 피처 컬럼 목록
│       │   ├── price_meta.pkl        # 모델 메타 (R², RMSE 등)
│       │   ├── defect_detector.pt    # 결함탐지 모델 (YOLOv8)
│       │   └── defect_meta.pkl       # 클래스 정보
│       └── api/
│           ├── predict.py            # 가격예측 API (Agent 3)
│           └── defect.py             # 결함탐지 API (Agent 3)
│
└── runs/                             # 학습 로그/결과
    └── defect/
        └── yolov8s_vehide/           # YOLOv8 학습 결과
```

---

## 1. 가격예측 모델 (회귀)

### 현재 상태
- **모델**: LightGBM (R²=0.614, MAPE=19.08%)
- **학습 데이터**: 엔카 크롤링 50,277건
- **API 자동 연동**: `.pkl` 파일이 있으면 ML, 없으면 mock

### 모델 파일 위치 & 이름 (반드시 이 경로/이름)

```
backend/app/ml_models/
├── price_predictor.pkl    ← 모델 파일 (필수)
├── price_encoders.pkl     ← LabelEncoder dict (필수)
├── price_features.pkl     ← feature 컬럼 list (필수)
└── price_meta.pkl         ← 메타정보 dict (선택, 권장)
```

### 모델 교체 방법

1. `scripts/train_price_model.py` 수정 → 학습 실행
2. 학습 완료 시 자동으로 `backend/app/ml_models/`에 저장됨
3. **서버 재시작하면 자동으로 새 모델 로드**

```bash
# 학습 실행
conda activate jjh
cd /home/jjh0709/Project_2026_1
python scripts/train_price_model.py

# 서버 재시작 (새 모델 자동 로드)
fuser -k 8000/tcp
cd backend && python run.py
```

### 직접 .pkl 교체하기

다른 모델(예: XGBoost, Random Forest 등)로 교체하려면:

```python
import joblib

# 1. 모델 저장
joblib.dump(your_model, "backend/app/ml_models/price_predictor.pkl")

# 2. 인코더 저장 (brand, model, fuel_type, region의 LabelEncoder dict)
encoders = {
    'brand': brand_le,      # sklearn.preprocessing.LabelEncoder
    'model': model_le,
    'fuel_type': fuel_type_le,
    'region': region_le,
}
joblib.dump(encoders, "backend/app/ml_models/price_encoders.pkl")

# 3. 피처 컬럼 목록 저장
feature_cols = ['year', 'mileage', 'car_age', 'annual_mileage',
                'brand_tier', 'fuel_encoded', 'engine_cc',
                'brand_avg_price', 'model_avg_price',
                'brand_le', 'model_le', 'fuel_type_le', 'region_le']
joblib.dump(feature_cols, "backend/app/ml_models/price_features.pkl")

# 4. 메타 정보 (선택)
meta = {'best_model': 'lgbm', 'r2': 0.61, 'rmse': 924.0, 'mape': 19.08}
joblib.dump(meta, "backend/app/ml_models/price_meta.pkl")
```

### 요구 사항
- 모델은 `.predict(X)` 메서드가 있어야 함 (scikit-learn 호환)
- X는 2D numpy array, 컬럼 순서 = `price_features.pkl`의 리스트 순서
- 출력: 가격(만원) 1D array

### API 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/predict/price` | JSON body로 차량 정보 전달 → 가격 예측 |
| GET | `/api/predict/vehicle/{id}` | 차량 ID → DB에서 정보 조회 → 가격 예측 |

**응답 예시:**
```json
{
  "predicted_price": 1354,
  "price_range_low": 1095,
  "price_range_high": 1612,
  "confidence": 0.6138,
  "model_type": "ml",
  "depreciation_curve": [{"year": 2026, "price": 1354}, ...],
  "similar_listings": [...]
}
```

---

## 2. 결함탐지 모델 (CNN / YOLOv8)

### 현재 상태
- **모델**: YOLOv8s (mAP50=0.522, Precision=63.9%)
- **학습 데이터**: VeHIDE 데이터셋
- **5개 클래스**: dent, scratch, paint_damage, glass_crack, missing_part
- **API 자동 연동**: `.pt` 파일이 있으면 YOLO, 없으면 데모 데이터

### 모델 파일 위치 & 이름 (반드시 이 경로/이름)

```
backend/app/ml_models/
├── defect_detector.pt     ← YOLOv8 모델 (필수)
└── defect_meta.pkl        ← 클래스 정보 (선택)
```

### 모델 교체 방법

1. `scripts/train_defect_model.py` 수정 → 학습 실행
2. 학습 완료 시 `runs/defect/yolov8s_vehide/weights/best.pt` 생성
3. 자동으로 `backend/app/ml_models/defect_detector.pt`에 복사됨
4. **서버 재시작하면 자동으로 새 모델 로드**

```bash
# 학습 실행 (GPU 필요)
conda activate jjh
export CUDA_HOME=/usr/local/cuda-12.2
cd /home/jjh0709/Project_2026_1
python scripts/train_defect_model.py

# 서버 재시작
fuser -k 8000/tcp
cd backend && python run.py
```

### 직접 .pt 교체하기

다른 YOLOv8 모델로 교체하려면:

```bash
# 방법 1: 직접 복사
cp /path/to/your/best.pt backend/app/ml_models/defect_detector.pt

# 방법 2: 학습 결과에서 복사
cp runs/defect/your_run/weights/best.pt backend/app/ml_models/defect_detector.pt

# 메타 정보 업데이트 (선택)
python -c "
import joblib
meta = {
    'classes': ['dent', 'scratch', 'paint_damage', 'glass_crack', 'missing_part'],
    'model_type': 'yolov8s',
}
joblib.dump(meta, 'backend/app/ml_models/defect_meta.pkl')
"
```

### 요구 사항
- **ultralytics YOLO 호환** `.pt` 파일
- `YOLO(path).predict(image)` 로 추론 가능해야 함
- 클래스 인덱스: 0=dent, 1=scratch, 2=paint_damage, 3=glass_crack, 4=missing_part
- 클래스를 변경하면 `defect_meta.pkl`도 업데이트

### API 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/defect/vehicles/{id}` | 차량 ID → 결함 데이터 반환 |
| POST | `/api/defect/detect` | 이미지 업로드 → 실시간 결함 탐지 |

**결함 데이터 우선순위:**
1. `defects.json` 파일 (3D 파이프라인 결과) → 최우선
2. YOLOv8 실시간 추론 (프레임 이미지 존재 시)
3. 데모 데이터 (vehicle_id=1)
4. 빈 결과

**응답 예시:**
```json
{
  "vehicle_id": 1,
  "total_defect_score": 23.5,
  "severity_level": "중간",
  "defect_count": 3,
  "source": "yolov8",
  "defects": [
    {
      "type": "scratch",
      "type_kr": "스크래치",
      "severity": "중간",
      "confidence": 0.87,
      "bbox": [120, 80, 350, 200],
      "marker_color": "#F59E0B"
    }
  ]
}
```

---

## 3. 팀별 작업 브랜치 & 담당 파일

### Agent 1: 3D Pipeline
```
브랜치: feature/3d-pipeline
담당 파일:
  scripts/extract_frames.py
  scripts/run_colmap.py
  scripts/train_gaussian.py
  scripts/export_model.py
  scripts/run_pipeline.py
  scripts/train_hq.py
  scripts/remove_background.py
  scripts/generate_depths.py
```

### Agent 2: AI 결함탐지 + 가격예측
```
브랜치: feature/ai-models
담당 파일:
  scripts/train_price_model.py      ← 가격예측 모델 학습
  scripts/train_defect_model.py     ← 결함탐지 모델 학습
  scripts/crawling/                 ← 크롤링 스크립트
  data/                             ← 학습 데이터

모델 저장 위치:
  backend/app/ml_models/price_predictor.pkl
  backend/app/ml_models/price_encoders.pkl
  backend/app/ml_models/price_features.pkl
  backend/app/ml_models/price_meta.pkl
  backend/app/ml_models/defect_detector.pt
  backend/app/ml_models/defect_meta.pkl
```

### Agent 3: Backend API
```
브랜치: feature/backend-api
담당 파일:
  backend/app/api/predict.py        ← 가격예측 API (모델 로드 & 서빙)
  backend/app/api/defect.py         ← 결함탐지 API (모델 로드 & 서빙)
  backend/app/api/                  ← 기타 API
  backend/app/models.py
  backend/app/schemas.py
  backend/app/main.py
```

### Agent 4: Frontend
```
브랜치: feature/frontend
담당 파일:
  backend/app/templates/
  backend/app/static/js/
  backend/app/static/css/
```

### Agent 5: DevOps
```
브랜치: feature/devops
담당 파일:
  Dockerfile
  docker-compose.yml
  nginx/
```

---

## 4. 모델 교체 체크리스트

### 가격예측 모델 교체 시
- [ ] `price_predictor.pkl` 교체 (scikit-learn `.predict()` 호환)
- [ ] `price_encoders.pkl` 교체 (brand, model, fuel_type, region LabelEncoder)
- [ ] `price_features.pkl` 교체 (피처 컬럼 리스트, 순서 중요)
- [ ] `price_meta.pkl` 업데이트 (R², RMSE 등)
- [ ] 서버 재시작 → 자동 로드

### 결함탐지 모델 교체 시
- [ ] `defect_detector.pt` 교체 (ultralytics YOLO `.pt`)
- [ ] 클래스가 변경되면 `defect_meta.pkl`도 업데이트
- [ ] 서버 재시작 → 자동 로드

### 확인 방법
```bash
# 가격예측 모델 동작 확인
curl http://localhost:8000/api/predict/vehicle/1 | python3 -m json.tool
# → "model_type": "ml" 이면 실제 모델 사용 중
# → "model_type": "mock" 이면 폴백 모드

# 결함탐지 모델 동작 확인
curl http://localhost:8000/api/defect/vehicles/1 | python3 -m json.tool
# → "source": "yolov8" 이면 실제 모델 사용 중
# → "source": "demo" 이면 폴백 모드
```

---

## 5. 자동 연동 로직 요약

```
서버 시작
  ├── predict.py: price_predictor.pkl 있으면 → joblib.load() → ML 모드
  │                없으면 → mock 모드 (하드코딩 감가상각)
  │
  └── defect.py:  defect_detector.pt 있으면 → YOLO() → YOLOv8 모드
                  없으면 → DEMO_DEFECTS dict → 데모 모드

API 호출 시
  ├── predict: _predict(req) → ML 또는 mock 자동 선택
  └── defect:  defects.json > YOLOv8 추론 > 데모 > 빈 결과 (우선순위)
```

**핵심: `.pkl`/`.pt` 파일만 교체하고 서버 재시작하면 끝.**
