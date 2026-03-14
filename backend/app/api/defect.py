"""
AI 결함 탐지 API
- .pt 모델이 있으면 실제 YOLOv8 추론
- 없으면 데모 데이터로 폴백
"""

import json
import os
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import Vehicle
from app.config import BASE_DIR

router = APIRouter(prefix="/api/defect", tags=["defect"])
logger = logging.getLogger(__name__)

# ── 모델 경로 ──
MODEL_DIR = os.path.join(os.path.dirname(BASE_DIR), "backend", "app", "ml_models")
DEFECT_MODEL_PATH = os.path.join(MODEL_DIR, "defect_detector.pt")
DEFECT_META_PATH = os.path.join(MODEL_DIR, "defect_meta.pkl")

# ── 모델 로드 (서버 시작 시 1회) ──
_defect_model = None
_defect_meta = None
_model_loaded = False

# 클래스 정보
CLASSES = ['dent', 'scratch', 'paint_damage', 'glass_crack', 'missing_part']
CLASS_KR = {
    'dent': '덴트',
    'scratch': '스크래치',
    'paint_damage': '도색 손상',
    'glass_crack': '유리 파손',
    'missing_part': '부품 손실',
}
SEVERITY_MAP = {
    'dent': {'default': '중간', 'large': '심각'},
    'scratch': {'default': '경미', 'large': '중간'},
    'paint_damage': {'default': '경미', 'large': '중간'},
    'glass_crack': {'default': '심각', 'large': '심각'},
    'missing_part': {'default': '심각', 'large': '심각'},
}
MARKER_COLORS = {
    '경미': '#10B981',
    '중간': '#F59E0B',
    '심각': '#EF4444',
}


def _load_defect_model():
    """YOLOv8 결함 탐지 모델 로드"""
    global _defect_model, _defect_meta, _model_loaded
    if _model_loaded:
        return _defect_model is not None

    _model_loaded = True
    try:
        if not os.path.exists(DEFECT_MODEL_PATH):
            logger.info(f"[결함탐지] 모델 파일 없음: {DEFECT_MODEL_PATH} → 데모 모드")
            return False

        from ultralytics import YOLO
        _defect_model = YOLO(DEFECT_MODEL_PATH)
        logger.info(f"[결함탐지] YOLOv8 모델 로드 성공: {DEFECT_MODEL_PATH}")

        if os.path.exists(DEFECT_META_PATH):
            import joblib
            _defect_meta = joblib.load(DEFECT_META_PATH)
            logger.info(f"[결함탐지] 메타 로드: classes={_defect_meta.get('classes', [])}")

        return True
    except Exception as e:
        logger.warning(f"[결함탐지] 모델 로드 실패: {e} → 데모 모드")
        _defect_model = None
        return False


def _detect_from_image(image_path: str, conf_threshold: float = 0.3) -> list:
    """이미지에서 결함 탐지 (실제 YOLOv8 추론)"""
    results = _defect_model(image_path, conf=conf_threshold, verbose=False)
    detections = []

    classes = (_defect_meta or {}).get('classes', CLASSES)

    for r in results:
        if r.boxes is None:
            continue
        for box in r.boxes:
            cls_idx = int(box.cls[0])
            conf = float(box.conf[0])
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            cls_name = classes[cls_idx] if cls_idx < len(classes) else f"class_{cls_idx}"

            # bbox 크기로 심각도 판단
            area = (x2 - x1) * (y2 - y1)
            img_area = r.orig_shape[0] * r.orig_shape[1]
            area_ratio = area / img_area if img_area > 0 else 0
            severity = SEVERITY_MAP.get(cls_name, {}).get(
                'large' if area_ratio > 0.05 else 'default', '중간'
            )

            detections.append({
                "type": cls_name,
                "type_kr": CLASS_KR.get(cls_name, cls_name),
                "severity": severity,
                "confidence": round(conf, 3),
                "bbox": [round(x1), round(y1), round(x2), round(y2)],
                "area_ratio": round(area_ratio, 4),
                "marker_color": MARKER_COLORS.get(severity, '#F59E0B'),
            })

    return detections


def _build_defect_response(vehicle_id: int, detections: list, source: str = "yolov8") -> dict:
    """탐지 결과를 API 응답 포맷으로 변환"""
    if not detections:
        return {
            "vehicle_id": vehicle_id,
            "total_defect_score": 0,
            "severity_level": "양호",
            "defect_count": 0,
            "defects": [],
            "source": source,
        }

    # 결함 점수 계산
    score_map = {'경미': 5, '중간': 15, '심각': 30}
    total_score = sum(score_map.get(d['severity'], 10) * d['confidence'] for d in detections)
    total_score = round(min(100, total_score), 1)

    if total_score >= 50:
        severity_level = "심각"
    elif total_score >= 20:
        severity_level = "중간"
    else:
        severity_level = "경미"

    defects_with_id = []
    for i, d in enumerate(detections):
        defect = {
            "id": i + 1,
            **d,
            "position_3d": [0, 0, 0],  # 3D 역투영 미적용 시 기본값
            "source_frame": f"frame_{i:04d}.jpg",
            "description": f"{d['type_kr']} 발견 (신뢰도 {d['confidence']*100:.0f}%)",
            "annotated_image_url": "/static/images/placeholder-car.svg",
        }
        defects_with_id.append(defect)

    return {
        "vehicle_id": vehicle_id,
        "total_defect_score": total_score,
        "severity_level": severity_level,
        "defect_count": len(detections),
        "defects": defects_with_id,
        "source": source,
    }


# ── 데모 데이터 (모델 없을 때 폴백) ──
DEMO_DEFECTS = {
    1: {
        "vehicle_id": 1,
        "total_defect_score": 23.5,
        "severity_level": "중간",
        "defect_count": 3,
        "source": "demo",
        "defects": [
            {
                "id": 1, "type": "scratch", "type_kr": "스크래치",
                "severity": "중간", "confidence": 0.87,
                "position_3d": [2.1, -0.8, 1.5], "marker_color": "#F59E0B",
                "source_frame": "frame_0042.jpg",
                "description": "좌측 앞 도어에 약 15cm 스크래치 발견",
                "annotated_image_url": "/static/images/placeholder-car.svg",
            },
            {
                "id": 2, "type": "dent", "type_kr": "덴트",
                "severity": "경미", "confidence": 0.72,
                "position_3d": [-1.8, -0.5, -1.2], "marker_color": "#10B981",
                "source_frame": "frame_0078.jpg",
                "description": "후면 범퍼 우측 소형 덴트",
                "annotated_image_url": "/static/images/placeholder-car.svg",
            },
            {
                "id": 3, "type": "paint_damage", "type_kr": "도색 손상",
                "severity": "경미", "confidence": 0.65,
                "position_3d": [0.5, -1.0, 2.8], "marker_color": "#10B981",
                "source_frame": "frame_0103.jpg",
                "description": "전면 후드 미세 도색 벗겨짐",
                "annotated_image_url": "/static/images/placeholder-car.svg",
            },
        ],
    }
}


@router.get("/vehicles/{vehicle_id}")
async def get_vehicle_defects(vehicle_id: int, db: Session = Depends(get_db)):
    """3D 뷰어용 결함 위치 데이터 반환"""
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(404, "차량을 찾을 수 없습니다.")

    # 1) 파일 기반 결함 데이터 (파이프라인 결과 defects.json)
    if vehicle.model_3d_url:
        model_dir = vehicle.model_3d_url.rsplit("/", 1)[0]
        defects_path = os.path.join(BASE_DIR, model_dir.lstrip("/"), "defects.json")
        if os.path.exists(defects_path):
            with open(defects_path, "r", encoding="utf-8") as f:
                return json.load(f)

    # 2) 실제 YOLOv8 모델로 추론 (프레임 이미지가 있으면)
    if _load_defect_model() and vehicle.model_3d_url:
        model_dir = vehicle.model_3d_url.rsplit("/", 1)[0]
        frames_dir = os.path.join(BASE_DIR, model_dir.lstrip("/"), "frames")
        if os.path.exists(frames_dir):
            import glob
            frames = sorted(glob.glob(os.path.join(frames_dir, "*.jpg")))[:20]  # 최대 20장
            all_detections = []
            for frame in frames:
                dets = _detect_from_image(frame)
                all_detections.extend(dets)
            return _build_defect_response(vehicle_id, all_detections, source="yolov8")

    # 3) 데모 데이터
    if vehicle_id in DEMO_DEFECTS:
        return DEMO_DEFECTS[vehicle_id]

    # 4) 결함 없음
    return {
        "vehicle_id": vehicle_id,
        "total_defect_score": 0,
        "severity_level": "양호",
        "defect_count": 0,
        "defects": [],
        "source": "none",
    }


@router.post("/detect")
async def detect_defects_from_upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """업로드된 이미지에서 결함 탐지 (실시간)"""
    if not _load_defect_model():
        raise HTTPException(503, "결함 탐지 모델이 로드되지 않았습니다. defect_detector.pt 파일을 확인하세요.")

    import tempfile
    suffix = os.path.splitext(file.filename or "img.jpg")[1]
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        detections = _detect_from_image(tmp_path)
        return _build_defect_response(0, detections, source="yolov8_upload")
    finally:
        os.unlink(tmp_path)
