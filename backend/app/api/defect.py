"""
AI 결함 탐지 API
- 3D 뷰어용 결함 위치 데이터 반환
- 학습된 YOLOv8 모델 + COLMAP 역투영 결과를 서빙
- 현재는 데모 데이터 (실제 모델 학습 후 교체)
"""

import json
import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import Vehicle
from app.config import BASE_DIR

router = APIRouter(prefix="/api/defect", tags=["defect"])


# 데모용 결함 데이터 (실제로는 YOLOv8 + backprojection 결과)
DEMO_DEFECTS = {
    1: {
        "vehicle_id": 1,
        "total_defect_score": 23.5,
        "severity_level": "중간",
        "defect_count": 3,
        "defects": [
            {
                "id": 1,
                "type": "scratch",
                "type_kr": "스크래치",
                "severity": "중간",
                "confidence": 0.87,
                "position_3d": [2.1, -0.8, 1.5],
                "marker_color": "#F59E0B",
                "source_frame": "frame_0042.jpg",
                "description": "좌측 앞 도어에 약 15cm 스크래치 발견",
                "annotated_image_url": "/static/images/placeholder-car.svg",
            },
            {
                "id": 2,
                "type": "dent",
                "type_kr": "덴트",
                "severity": "경미",
                "confidence": 0.72,
                "position_3d": [-1.8, -0.5, -1.2],
                "marker_color": "#10B981",
                "source_frame": "frame_0078.jpg",
                "description": "후면 범퍼 우측 소형 덴트",
                "annotated_image_url": "/static/images/placeholder-car.svg",
            },
            {
                "id": 3,
                "type": "paint_damage",
                "type_kr": "도색 손상",
                "severity": "경미",
                "confidence": 0.65,
                "position_3d": [0.5, -1.0, 2.8],
                "marker_color": "#10B981",
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

    # 1) 파일 기반 결함 데이터 확인 (실제 파이프라인 결과)
    if vehicle.model_3d_url:
        model_dir = vehicle.model_3d_url.rsplit("/", 1)[0]  # /static/models/xxx
        defects_path = os.path.join(BASE_DIR, model_dir.lstrip("/"), "defects.json")
        if os.path.exists(defects_path):
            with open(defects_path, "r", encoding="utf-8") as f:
                return json.load(f)

    # 2) 데모 데이터 반환
    if vehicle_id in DEMO_DEFECTS:
        return DEMO_DEFECTS[vehicle_id]

    # 3) 결함 없음
    return {
        "vehicle_id": vehicle_id,
        "total_defect_score": 0,
        "severity_level": "양호",
        "defect_count": 0,
        "defects": [],
    }
