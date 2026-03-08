# 팀원 B 업무 계획서
## 담당: 2D/3D 결함 탐지 (Vision AI)

---

## 1. 역할 요약

| 항목 | 내용 |
|------|------|
| **담당 분야** | 차량 외관 결함 자동 탐지 (2D → 3D 연동) |
| **최종 산출물** | ① 결함 탐지 API (`POST /api/defect/analyze`) ② 3D 뷰어 결함 마커 |
| **연동 대상** | 팀장(API 연동, 3D 뷰어), 팀원 A(결함 점수 → 가격 예측 보정) |
| **주요 기술** | Python, YOLOv8, SAM, OpenCV, PyTorch, COLMAP 포즈 활용 |

---

## 2. 결함 탐지 범위

| 결함 종류 | 설명 | 심각도 기준 |
|-----------|------|-------------|
| `scratch` | 스크래치 / 긁힘 | 길이 10cm+ = 중, 30cm+ = 심각 |
| `dent` | 찌그러짐 / 덴트 | 지름 5cm+ = 중, 15cm+ = 심각 |
| `paint_damage` | 도색 이상 / 탈색 | 면적 5% = 중, 15%+ = 심각 |
| `rust` | 부식 / 녹 | 존재하면 중, 관통 = 심각 |
| `glass_crack` | 유리 균열 | 시야 방해 여부 기준 |
| `bumper_damage` | 범퍼 파손 | 변형 여부 기준 |

---

## 3. 전체 개발 흐름

```
[Phase 1] 2D 결함 탐지  ← 3주
  차량 이미지 → YOLOv8 → 결함 bbox + 분류 + 심각도
        ↓
[Phase 2] 3D 투영  ← 1주
  결함 bbox + COLMAP 카메라 포즈 → 3D 위치 역투영
  → 3DGS 뷰어에 결함 마커 오버레이
        ↓
[Phase 3] 고도화 (선택)
  PointNet++ 기반 3D 형상 이상 탐지
```

---

## 4. Sprint 계획 (4주)

### Week 1: 데이터셋 준비 + 환경 세팅

#### 목표
- 학습 데이터셋 확보 및 정리
- YOLOv8 학습 환경 세팅 완료

#### 세부 Task

**[Task B-1-1] 데이터셋 확보**

우선순위별 데이터셋:

1. **CarDD (Car Damage Detection)** - 최우선
   ```
   논문: "CarDD: A New Dataset for Vision-based Car Damage Detection"
   데이터: 4,000+ 손상 차량 이미지, bbox 어노테이션
   클래스: 손상 유형 6종
   다운로드: https://cardd-ustc.github.io
   ```

2. **Vehicle Damage Dataset (Kaggle)**
   ```
   링크: https://www.kaggle.com/datasets/hendrichscullen/vehide-dataset-automatic-vehicle-damage-detection
   데이터: 1,900+ 이미지
   ```

3. **자체 수집 (보완용)**
   ```python
   # 구글 이미지 검색으로 추가 수집
   # 검색어: "차량 스크래치", "자동차 덴트", "car scratch damage"
   # selenium + google images crawling
   ```

**[Task B-1-2] 데이터 레이블링 도구 세팅**
```bash
# Roboflow 사용 (웹 기반 어노테이션 툴)
# 또는 LabelImg (로컬)
pip install labelImg

# YOLO 형식으로 export
# classes.txt, images/, labels/ 구조
```

**[Task B-1-3] 데이터셋 폴더 구조**
```
scripts/defect_detection/
├── datasets/
│   ├── images/
│   │   ├── train/   (80%)
│   │   ├── val/     (15%)
│   │   └── test/    (5%)
│   └── labels/
│       ├── train/
│       ├── val/
│       └── test/
├── cardd.yaml         # 데이터셋 설정 파일
├── train.py           # 학습 스크립트
├── inference.py       # 추론 스크립트
└── backproject.py     # 3D 투영 모듈
```

**[Task B-1-4] cardd.yaml 작성**
```yaml
path: scripts/defect_detection/datasets
train: images/train
val: images/val
test: images/test

nc: 6
names: ['scratch', 'dent', 'paint_damage', 'rust', 'glass_crack', 'bumper_damage']
```

**[Task B-1-5] 환경 세팅**
```bash
conda activate jjh
pip install ultralytics opencv-python-headless
pip install segment-anything
# SAM 가중치 다운로드
wget https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth \
     -O scripts/defect_detection/sam_vit_h.pth
```

---

### Week 2: YOLOv8 학습 + 검증

#### 목표
- mAP50 > 0.65 달성
- 실시간 추론 (< 100ms/장) 확인

#### 세부 Task

**[Task B-2-1] Baseline 학습** (`scripts/defect_detection/train.py`)
```python
from ultralytics import YOLO

# Baseline: YOLOv8n (nano, 빠름)
model = YOLO('yolov8n.pt')
results = model.train(
    data='cardd.yaml',
    epochs=100,
    imgsz=640,
    batch=32,           # A100 80GB → 큰 배치 가능
    device=0,           # GPU 0
    project='runs/defect',
    name='baseline',
    patience=20,        # early stopping
)
```

**[Task B-2-2] 모델 크기 비교 실험**

| 모델 | 파라미터 | 속도 | 정확도 |
|------|---------|------|--------|
| YOLOv8n | 3.2M | ★★★★★ | ★★★ |
| YOLOv8s | 11.2M | ★★★★ | ★★★★ |
| YOLOv8m | 25.9M | ★★★ | ★★★★★ |

→ 최종 선택: **YOLOv8s** (속도/정확도 균형)

**[Task B-2-3] Data Augmentation 설정**
```python
# ultralytics augmentation params
augment=True,
hsv_h=0.015,      # 색상 조정
hsv_s=0.7,        # 채도 조정
hsv_v=0.4,        # 밝기 조정
degrees=10,       # 회전
translate=0.1,
scale=0.5,
flipud=0.0,
fliplr=0.5,       # 좌우 반전
mosaic=1.0,       # 모자이크 증강
```

**[Task B-2-4] 학습 결과 목표치**

| 지표 | 목표 |
|------|------|
| mAP50 | > 0.65 |
| mAP50-95 | > 0.40 |
| Precision | > 0.70 |
| Recall | > 0.60 |
| 추론 속도 | < 100ms / 장 (GPU) |

**[Task B-2-5] SAM 결함 세그멘테이션 (마스크)**
```python
from segment_anything import SamPredictor, sam_model_registry

# YOLOv8 bbox → SAM으로 정밀 마스크 생성
sam = sam_model_registry['vit_h'](checkpoint='sam_vit_h.pth')
predictor = SamPredictor(sam)

def get_defect_mask(image, bbox):
    predictor.set_image(image)
    masks, scores, _ = predictor.predict(
        box=np.array(bbox),
        multimask_output=False
    )
    return masks[0]   # 결함 정밀 마스크
```

**[Task B-2-6] 심각도 점수 계산 알고리즘**
```python
def calculate_severity(detections, image_shape):
    """
    returns: defect_score (0~100), severity_level ('경미'/'중간'/'심각')
    """
    h, w = image_shape[:2]
    image_area = h * w
    total_score = 0

    WEIGHTS = {
        'scratch': 1.0,
        'dent': 2.5,
        'paint_damage': 1.5,
        'rust': 3.0,
        'glass_crack': 4.0,
        'bumper_damage': 2.0
    }

    for det in detections:
        cls = det['class']
        bbox_area = det['w'] * det['h']
        area_ratio = bbox_area / image_area
        confidence = det['confidence']
        score = WEIGHTS[cls] * area_ratio * confidence * 100
        total_score += score

    total_score = min(total_score, 100)

    if total_score < 20:
        level = '경미'
    elif total_score < 50:
        level = '중간'
    else:
        level = '심각'

    return round(total_score, 1), level
```

---

### Week 3: 결함 탐지 API 구현

#### 목표
- `POST /api/defect/analyze` 완성
- 팀장 백엔드에 연동

#### 세부 Task

**[Task B-3-1] API 구현** (`backend/app/api/defect.py`)

```python
from fastapi import APIRouter, UploadFile, File, HTTPException
from ultralytics import YOLO
import cv2, numpy as np, base64, io
from PIL import Image

router = APIRouter()
model = YOLO('app/models/defect_detector.pt')

class DefectResult(BaseModel):
    defect_score: float          # 0~100 종합 점수
    severity_level: str          # '경미' / '중간' / '심각'
    detections: list[DefectItem] # 탐지된 결함 목록
    annotated_image: str         # base64 인코딩된 결과 이미지
    summary: str                 # 자연어 요약

class DefectItem(BaseModel):
    class_name: str              # 결함 종류
    confidence: float            # 탐지 신뢰도
    bbox: list[float]            # [x1, y1, x2, y2] (0~1 정규화)
    area_ratio: float            # 전체 이미지 대비 면적 비율 (%)
    severity: str                # 해당 결함의 심각도

@router.post('/api/defect/analyze')
async def analyze_defects(file: UploadFile = File(...)):
    # 이미지 읽기
    contents = await file.read()
    img = Image.open(io.BytesIO(contents))
    img_np = np.array(img)

    # YOLOv8 추론
    results = model(img_np, conf=0.4, iou=0.45)[0]

    # 결과 파싱
    detections = []
    for box in results.boxes:
        detections.append(DefectItem(
            class_name=model.names[int(box.cls)],
            confidence=float(box.conf),
            bbox=box.xyxyn[0].tolist(),   # 정규화 좌표
            area_ratio=float((box.xywhn[0][2] * box.xywhn[0][3]) * 100),
            severity=get_item_severity(model.names[int(box.cls)], box)
        ))

    # 종합 점수 계산
    score, level = calculate_severity(detections, img_np.shape)

    # 결과 이미지 (bbox 그려진)
    annotated = results.plot()
    _, buffer = cv2.imencode('.jpg', annotated)
    img_b64 = base64.b64encode(buffer).decode()

    # 자연어 요약 생성
    summary = generate_summary(detections, score, level)

    return DefectResult(
        defect_score=score,
        severity_level=level,
        detections=detections,
        annotated_image=img_b64,
        summary=summary
    )
```

**[Task B-3-2] 다중 이미지 배치 분석 (차량 전체 진단)**
```python
@router.post('/api/defect/analyze-batch')
async def analyze_batch(files: list[UploadFile] = File(...)):
    """
    차량 여러 각도 사진 (정면/측면/후면) 일괄 분석
    → 전체 차량 종합 결함 점수 반환
    """
    all_detections = []
    for file in files:
        result = await analyze_defects(file)
        all_detections.extend(result.detections)

    # 중복 결함 병합 (같은 부위 여러 이미지에서 탐지된 경우)
    merged = merge_duplicate_detections(all_detections)
    total_score, level = calculate_severity(merged, ...)
    return {...}
```

**[Task B-3-3] 자연어 요약 생성**
```python
def generate_summary(detections, score, level):
    if not detections:
        return "외관 결함이 발견되지 않았습니다. 양호한 상태입니다."

    cls_counts = {}
    for d in detections:
        cls_counts[d.class_name] = cls_counts.get(d.class_name, 0) + 1

    parts = []
    label_map = {
        'scratch': '스크래치',
        'dent': '덴트/찌그러짐',
        'paint_damage': '도색 이상',
        'rust': '부식',
        'glass_crack': '유리 균열',
        'bumper_damage': '범퍼 손상'
    }
    for cls, cnt in cls_counts.items():
        parts.append(f"{label_map.get(cls, cls)} {cnt}건")

    summary = f"{', '.join(parts)}이 탐지되었습니다. "
    summary += f"종합 결함 점수는 {score:.0f}점으로 '{level}' 수준입니다."
    return summary
```

**[Task B-3-4] 모델 파일 저장**
```python
# 학습 완료 후 best.pt를 backend/app/models/에 복사
import shutil
shutil.copy('runs/defect/train/weights/best.pt',
            'backend/app/models/defect_detector.pt')
```

**[Task B-3-5] 팀장 백엔드 연동**
- `backend/app/main.py`에 defect 라우터 include
- 차량 등록(`/sell`) 시 업로드 이미지 자동 분석
- `DiagnosisReport` DB 테이블에 결과 저장

---

### Week 4: 3D 결함 투영 + 마커 오버레이

#### 목표
- 2D 결함 위치 → 3D 공간 투영
- 3DGS 뷰어에 결함 마커 표시

#### 세부 Task

**[Task B-4-1] COLMAP 카메라 포즈 파싱** (`scripts/defect_detection/backproject.py`)
```python
import pycolmap
import numpy as np

def load_camera_poses(colmap_path):
    """
    COLMAP sparse/0/ 에서 카메라 내/외부 파라미터 로드
    """
    reconstruction = pycolmap.Reconstruction(colmap_path)
    cameras = {}
    for img_id, image in reconstruction.images.items():
        cam = reconstruction.cameras[image.camera_id]
        cameras[image.name] = {
            'R': image.rotmat(),        # 3x3 회전 행렬
            'T': image.tvec,            # 3 이동 벡터
            'K': cam.calibration_matrix(),  # 3x3 내부 파라미터
        }
    return cameras
```

**[Task B-4-2] 2D bbox → 3D Ray Casting**
```python
def backproject_bbox_to_3d(bbox_2d, depth, camera_params):
    """
    2D 결함 bbox 중심점 → 3D 공간 위치

    bbox_2d: [x1, y1, x2, y2] (픽셀 좌표)
    depth: 해당 픽셀의 깊이값 (Depth Anything V2 결과)
    """
    cx = (bbox_2d[0] + bbox_2d[2]) / 2
    cy = (bbox_2d[1] + bbox_2d[3]) / 2

    K = camera_params['K']
    R = camera_params['R']
    T = camera_params['T']

    # 픽셀 → 카메라 좌표계
    point_cam = np.linalg.inv(K) @ np.array([cx, cy, 1.0]) * depth

    # 카메라 → 월드 좌표계
    point_world = R.T @ (point_cam - T)
    return point_world
```

**[Task B-4-3] 결함 위치 JSON 저장**
```python
# 차량 1대당 결함 3D 위치 데이터
defect_3d = {
    "vehicle_id": 19,
    "defects": [
        {
            "type": "scratch",
            "severity": "중간",
            "position_3d": [0.23, -0.15, 0.41],   # XYZ (미터)
            "color": "#F59E0B"                       # 표시 색상
        },
        ...
    ]
}
# backend/app/static/models/{vehicle_name}/defects.json 저장
```

**[Task B-4-4] 3DGS 뷰어에 결함 마커 오버레이**

팀장(`viewer.js`)에 전달할 코드:
```javascript
// vehicle_detail.html의 3D 뷰어 탭에 추가
async function loadDefectMarkers(vehicleId) {
    const res = await fetch(`/api/vehicles/${vehicleId}/defects`);
    const data = await res.json();

    data.defects.forEach(defect => {
        // Three.js 구체 마커 생성
        const geometry = new THREE.SphereGeometry(0.02, 16, 16);
        const material = new THREE.MeshBasicMaterial({
            color: defect.color,
            transparent: true,
            opacity: 0.8
        });
        const marker = new THREE.Mesh(geometry, material);
        marker.position.set(...defect.position_3d);

        // 클릭 시 툴팁 표시
        marker.userData = { type: defect.type, severity: defect.severity };
        scene.add(marker);
    });
}
```

**[Task B-4-5] 결함 3D 위치 API**
```python
@router.get('/api/vehicles/{vehicle_id}/defects')
async def get_defect_positions(vehicle_id: int):
    """3D 뷰어용 결함 위치 데이터 반환"""
    path = f'app/static/models/{vehicle_id}/defects.json'
    if not os.path.exists(path):
        return {"defects": []}
    with open(path) as f:
        return json.load(f)
```

---

## 5. 최종 산출물 목록

| 산출물 | 경로 | 설명 |
|--------|------|------|
| 학습 스크립트 | `scripts/defect_detection/train.py` | YOLOv8 학습 |
| 추론 스크립트 | `scripts/defect_detection/inference.py` | 단일 이미지 테스트 |
| 3D 투영 모듈 | `scripts/defect_detection/backproject.py` | 2D→3D 역투영 |
| 탐지 모델 | `backend/app/models/defect_detector.pt` | 학습된 YOLOv8s |
| API | `backend/app/api/defect.py` | 결함 분석 엔드포인트 |
| 데이터셋 | `scripts/defect_detection/datasets/` | 학습 데이터 |

---

## 6. 팀원 A와 협업 포인트

```
팀원 B 산출물:
  defect_score: 67.3      → 팀원 A의 가격 예측 API에 입력
  severity_level: '중간'   → 가격 하향 조정 트리거

팀원 A 처리:
  predicted_price = base_price * (1 - defect_score * 0.003)
  → "결함 반영 예측가: 2,420만원"
  → "결함 없을 시 예측가: 2,850만원"
  → "결함으로 인한 감가: 약 430만원"
```

---

## 7. 데이터셋 및 참고 자료

| 자료 | 링크/출처 |
|------|-----------|
| CarDD 데이터셋 | https://cardd-ustc.github.io |
| YOLOv8 공식 문서 | https://docs.ultralytics.com |
| Segment Anything (SAM) | https://github.com/facebookresearch/segment-anything |
| 참고 논문 | "CarDD: A New Dataset for Vision-based Car Damage Detection" (CVPR Workshop 2023) |
| Depth Anything V2 | `scripts/generate_depths.py` (기존 코드 활용 가능) |
