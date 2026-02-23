"""
3D Pipeline API - 영상 업로드 → 백그라운드 3D 변환 → 상태 조회
"""

import os
import uuid
import asyncio
import subprocess
import sys
import logging
from typing import Optional

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from app.config import BASE_DIR
from app.dependencies import get_db, require_user
from app.models import Vehicle, User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])

PROJECT_ROOT = os.path.dirname(BASE_DIR)  # Project_2026_1/
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")
UPLOAD_VIDEO_DIR = os.path.join(BASE_DIR, "uploads", "videos")
MODELS_DIR = os.path.join(BASE_DIR, "app", "static", "models")

os.makedirs(UPLOAD_VIDEO_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)

# In-memory job tracking (simple approach, no Celery needed)
pipeline_jobs: dict[str, dict] = {}


def run_pipeline_sync(job_id: str, video_path: str, vehicle_id: int):
    """Run the full 3D pipeline synchronously (called in thread)."""
    from app.database import SessionLocal

    job = pipeline_jobs[job_id]
    job["status"] = "extracting_frames"

    project_name = f"vehicle_{vehicle_id}_{job_id[:8]}"
    data_dir = os.path.join(PROJECT_ROOT, "data")
    frames_dir = os.path.join(data_dir, "frames", project_name)
    colmap_dir = os.path.join(data_dir, "colmap_output", project_name)
    gaussian_dir = os.path.join(data_dir, "gaussian_output", project_name)
    model_output_dir = os.path.join(MODELS_DIR, project_name)

    env = os.environ.copy()
    env["CUDA_HOME"] = "/usr/local/cuda-12.2"
    env["PATH"] = "/usr/local/cuda-12.2/bin:" + env.get("PATH", "")
    env["OPENBLAS_NUM_THREADS"] = "4"
    env["OMP_NUM_THREADS"] = "4"

    try:
        # Step 1: Extract frames
        job["status"] = "extracting_frames"
        job["message"] = "영상에서 프레임을 추출하고 있습니다..."
        result = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS_DIR, "extract_frames.py"),
             "--input", video_path,
             "--output", frames_dir,
             "--max_frames", "80",
             "--min_blur_score", "50"],
            capture_output=True, text=True, env=env, timeout=300,
        )
        if result.returncode != 0:
            job["status"] = "failed"
            job["message"] = f"프레임 추출 실패: {result.stderr[-500:]}"
            return

        # Step 2: COLMAP SfM
        job["status"] = "colmap"
        job["message"] = "카메라 위치를 추정하고 있습니다 (COLMAP)..."
        result = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS_DIR, "run_colmap.py"),
             "--image_path", frames_dir,
             "--output_path", colmap_dir],
            capture_output=True, text=True, env=env, timeout=1800,
        )
        if result.returncode != 0:
            job["status"] = "failed"
            job["message"] = f"COLMAP 실패: {result.stderr[-500:]}"
            return

        # Step 3: Gaussian Splatting training
        job["status"] = "training"
        job["message"] = "3D Gaussian Splatting 학습 중..."
        colmap_dense = os.path.join(colmap_dir, "dense")
        if not os.path.exists(colmap_dense):
            colmap_dense = colmap_dir

        result = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS_DIR, "train_gaussian.py"),
             "--source_path", colmap_dense,
             "--output_path", gaussian_dir,
             "--iterations", "7000"],
            capture_output=True, text=True, env=env, timeout=3600,
            cwd=PROJECT_ROOT,
        )
        if result.returncode != 0:
            job["status"] = "failed"
            job["message"] = f"학습 실패: {result.stderr[-500:]}"
            return

        # Step 4: Export model
        job["status"] = "exporting"
        job["message"] = "웹 뷰어용 모델을 변환하고 있습니다..."
        ply_path = os.path.join(gaussian_dir, "point_cloud", "iteration_7000", "point_cloud.ply")
        if not os.path.exists(ply_path):
            job["status"] = "failed"
            job["message"] = "학습 결과 PLY 파일을 찾을 수 없습니다."
            return

        os.makedirs(model_output_dir, exist_ok=True)
        result = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS_DIR, "export_model.py"),
             "--input", ply_path,
             "--output", model_output_dir,
             "--format", "both",
             "--max_gaussians", "500000"],
            capture_output=True, text=True, env=env, timeout=600,
            cwd=PROJECT_ROOT,
        )
        if result.returncode != 0:
            job["status"] = "failed"
            job["message"] = f"모델 변환 실패: {result.stderr[-500:]}"
            return

        # Step 5: Update DB
        model_url = f"/static/models/{project_name}/model.splat"
        db = SessionLocal()
        try:
            vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
            if vehicle:
                vehicle.model_3d_url = model_url
                vehicle.model_3d_status = "ready"
                db.commit()
        finally:
            db.close()

        job["status"] = "completed"
        job["message"] = "3D 모델 생성 완료!"
        job["model_url"] = model_url

    except subprocess.TimeoutExpired:
        job["status"] = "failed"
        job["message"] = "처리 시간이 초과되었습니다."
    except Exception as e:
        job["status"] = "failed"
        job["message"] = f"오류: {str(e)}"


@router.post("/start")
async def start_pipeline(
    video: UploadFile = File(...),
    vehicle_id: Optional[int] = None,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """영상을 업로드하고 3D 파이프라인을 시작한다."""
    # Validate file type
    if not video.filename.lower().endswith((".mp4", ".mov", ".avi", ".mkv", ".webm")):
        raise HTTPException(status_code=400, detail="지원하지 않는 영상 형식입니다. (mp4, mov, avi, mkv, webm)")

    # If no vehicle_id, create a temporary vehicle
    if not vehicle_id:
        vehicle = Vehicle(
            brand="미정", model="3D 스캔 중", year=2024,
            fuel_type="미정", transmission="자동", mileage=0,
            model_3d_status="processing",
        )
        db.add(vehicle)
        db.commit()
        db.refresh(vehicle)
        vehicle_id = vehicle.id
    else:
        vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not vehicle:
            raise HTTPException(status_code=404, detail="차량을 찾을 수 없습니다.")
        vehicle.model_3d_status = "processing"
        db.commit()

    # Save video
    job_id = uuid.uuid4().hex
    video_filename = f"{job_id}_{video.filename}"
    video_path = os.path.join(UPLOAD_VIDEO_DIR, video_filename)
    content = await video.read()
    with open(video_path, "wb") as f:
        f.write(content)

    # Start background pipeline
    pipeline_jobs[job_id] = {
        "status": "queued",
        "message": "대기 중...",
        "vehicle_id": vehicle_id,
        "model_url": None,
    }

    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, run_pipeline_sync, job_id, video_path, vehicle_id)

    return {
        "job_id": job_id,
        "vehicle_id": vehicle_id,
        "message": "3D 파이프라인이 시작되었습니다.",
    }


@router.get("/status/{job_id}")
async def get_pipeline_status(job_id: str):
    """파이프라인 진행 상태를 조회한다."""
    if job_id not in pipeline_jobs:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")
    return pipeline_jobs[job_id]
