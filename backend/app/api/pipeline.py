"""
3D Pipeline API - 영상 업로드 → 백그라운드 3D 변환 → 상태 조회
HQ 모드: 배경 제거 + Depth map + 60K iterations으로 최고 품질 3D 모델 생성
"""

import os
import uuid
import asyncio
import subprocess
import sys
import time
import logging
from typing import Optional

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
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

# In-memory job tracking
pipeline_jobs: dict[str, dict] = {}

# 단계별 진행률 정보
PIPELINE_STAGES = {
    "queued": {
        "label": "대기 중",
        "description": "파이프라인 대기열에 추가되었습니다.",
        "progress": 0,
        "step": 0,
        "total_steps": 7,
    },
    "extracting_frames": {
        "label": "프레임 추출",
        "description": "영상에서 선명한 프레임을 추출하고 있습니다. 흔들림 필터링 및 균등 샘플링 중...",
        "progress": 5,
        "step": 1,
        "total_steps": 7,
        "est_time": "1~3분",
    },
    "colmap": {
        "label": "카메라 위치 추정 (COLMAP)",
        "description": "Structure-from-Motion으로 각 프레임의 3D 카메라 위치를 계산하고 있습니다.",
        "progress": 15,
        "step": 2,
        "total_steps": 7,
        "est_time": "5~15분",
    },
    "removing_background": {
        "label": "배경 제거",
        "description": "rembg AI로 차량 배경을 제거하여 3D 품질을 높이고 있습니다.",
        "progress": 30,
        "step": 3,
        "total_steps": 7,
        "est_time": "3~10분",
    },
    "generating_depth": {
        "label": "Depth Map 생성",
        "description": "Depth Anything V2로 깊이 정보를 생성하여 3D 정확도를 높이고 있습니다.",
        "progress": 40,
        "step": 4,
        "total_steps": 7,
        "est_time": "2~5분",
    },
    "training": {
        "label": "3D Gaussian Splatting 학습",
        "description": "60,000 iterations으로 고품질 3D 모델을 학습하고 있습니다. 가장 오래 걸리는 단계입니다.",
        "progress": 50,
        "step": 5,
        "total_steps": 7,
        "est_time": "30~90분",
    },
    "exporting": {
        "label": "모델 변환 및 최적화",
        "description": "학습된 모델을 웹 뷰어용으로 변환하고 부유 아티팩트를 제거하고 있습니다.",
        "progress": 90,
        "step": 6,
        "total_steps": 7,
        "est_time": "1~2분",
    },
    "completed": {
        "label": "완료",
        "description": "3D 모델이 성공적으로 생성되었습니다!",
        "progress": 100,
        "step": 7,
        "total_steps": 7,
    },
    "failed": {
        "label": "실패",
        "description": "처리 중 오류가 발생했습니다.",
        "progress": 0,
        "step": 0,
        "total_steps": 7,
    },
}


def _update_job(job_id: str, status: str, message: str = "",
                training_progress: int = 0, **extra):
    """Job 상태를 업데이트한다."""
    job = pipeline_jobs[job_id]
    stage = PIPELINE_STAGES.get(status, {})

    job["status"] = status
    job["message"] = message or stage.get("description", "")
    job["label"] = stage.get("label", status)
    job["step"] = stage.get("step", 0)
    job["total_steps"] = stage.get("total_steps", 7)
    job["est_time"] = stage.get("est_time", "")

    # training 단계에서는 세부 진행률 반영
    if status == "training" and training_progress > 0:
        # training은 50~90% 구간
        job["progress"] = 50 + int(training_progress * 0.4)
    else:
        job["progress"] = stage.get("progress", 0)

    job["updated_at"] = time.time()
    for k, v in extra.items():
        job[k] = v


def _run_subprocess(cmd: list, env: dict, timeout: int = 3600,
                    cwd: str = None) -> subprocess.CompletedProcess:
    """서브프로세스를 실행하고 결과를 반환한다."""
    return subprocess.run(
        cmd,
        capture_output=True, text=True,
        env=env, timeout=timeout, cwd=cwd,
    )


def run_pipeline_hq(job_id: str, video_path: str, vehicle_id: int, quality: str = "hq"):
    """HQ 모드 3D 파이프라인 (배경제거 + depth + 60K iter)."""
    from app.database import SessionLocal

    job = pipeline_jobs[job_id]

    # 품질 설정
    if quality == "ultra":
        max_frames = 250
        iterations = 80000
        max_gaussians = 3_000_000
        densify_until = 45000
    elif quality == "hq":
        max_frames = 200
        iterations = 60000
        max_gaussians = 2_000_000
        densify_until = 35000
    else:  # standard
        max_frames = 100
        iterations = 30000
        max_gaussians = 1_000_000
        densify_until = 15000

    project_name = f"vehicle_{vehicle_id}_{job_id[:8]}"
    data_dir = os.path.join(PROJECT_ROOT, "data")
    frames_dir = os.path.join(data_dir, "frames", project_name)
    colmap_dir = os.path.join(data_dir, "colmap_output", project_name)
    gaussian_dir = os.path.join(data_dir, "gaussian_output", project_name)
    model_output_dir = os.path.join(MODELS_DIR, project_name)

    env = os.environ.copy()
    env["CUDA_HOME"] = "/usr/local/cuda-12.2"
    env["PATH"] = "/usr/local/cuda-12.2/bin:" + env.get("PATH", "")
    env["OPENBLAS_NUM_THREADS"] = "1"
    env["OMP_NUM_THREADS"] = "1"

    job["started_at"] = time.time()
    job["quality"] = quality
    job["iterations"] = iterations
    job["project_name"] = project_name

    try:
        # ──────────────────────────────────────────────────────────
        # Step 1: 프레임 추출 (블러 필터링 + 균등 샘플링)
        # ──────────────────────────────────────────────────────────
        _update_job(job_id, "extracting_frames")
        result = _run_subprocess(
            [sys.executable, os.path.join(SCRIPTS_DIR, "extract_frames.py"),
             "--input", video_path,
             "--output", frames_dir,
             "--max_frames", str(max_frames),
             "--min_blur_score", "50"],
            env=env, timeout=600,
        )
        if result.returncode != 0:
            _update_job(job_id, "failed", f"프레임 추출 실패: {result.stderr[-500:]}")
            return

        # 추출된 프레임 수 확인
        frame_count = len([f for f in os.listdir(frames_dir) if f.endswith('.jpg')]) if os.path.exists(frames_dir) else 0
        job["frame_count"] = frame_count

        # ──────────────────────────────────────────────────────────
        # Step 2: COLMAP SfM (카메라 위치 추정)
        # ──────────────────────────────────────────────────────────
        _update_job(job_id, "colmap")
        result = _run_subprocess(
            [sys.executable, os.path.join(SCRIPTS_DIR, "run_colmap.py"),
             "--image_path", frames_dir,
             "--output_path", colmap_dir],
            env=env, timeout=3600,
        )
        if result.returncode != 0:
            _update_job(job_id, "failed", f"COLMAP 실패: {result.stderr[-500:]}")
            return

        colmap_dense = os.path.join(colmap_dir, "dense")
        if not os.path.exists(colmap_dense):
            colmap_dense = colmap_dir

        # ──────────────────────────────────────────────────────────
        # Step 3: 배경 제거 (rembg)
        # ──────────────────────────────────────────────────────────
        images_dir = os.path.join(colmap_dense, "images")
        images_masked_dir = os.path.join(colmap_dense, "images_masked")
        gs_extra_args = []
        use_masked = False

        _update_job(job_id, "removing_background")
        result = _run_subprocess(
            [sys.executable, os.path.join(SCRIPTS_DIR, "remove_background.py"),
             "--input_dir", images_dir,
             "--output_dir", images_masked_dir],
            env=env, timeout=1800,
        )
        if result.returncode == 0 and os.path.isdir(images_masked_dir):
            gs_extra_args.extend(["--images", "images_masked"])
            use_masked = True
            job["bg_removed"] = True
        else:
            logger.warning("배경 제거 실패, 원본 이미지로 진행")
            job["bg_removed"] = False

        # ──────────────────────────────────────────────────────────
        # Step 4: Depth Map 생성 (Depth Anything V2)
        # ──────────────────────────────────────────────────────────
        _update_job(job_id, "generating_depth")
        use_depth = False
        result = _run_subprocess(
            [sys.executable, os.path.join(SCRIPTS_DIR, "generate_depths.py"),
             "--source_path", colmap_dense],
            env=env, timeout=1800,
        )
        depth_params = os.path.join(colmap_dense, "sparse", "0", "depth_params.json")
        if result.returncode == 0 and os.path.exists(depth_params):
            gs_extra_args.extend(["--depths", "depths"])
            use_depth = True
            job["depth_generated"] = True
        else:
            logger.warning("Depth map 생성 실패, depth 없이 진행")
            job["depth_generated"] = False

        # ──────────────────────────────────────────────────────────
        # Step 5: Gaussian Splatting 학습 (HQ 파라미터)
        # ──────────────────────────────────────────────────────────
        _update_job(job_id, "training",
                    f"3D Gaussian Splatting {iterations:,} iterations 학습 중...")

        # HQ 최적 하이퍼파라미터
        gs_extra_args.extend([
            "--antialiasing",
            "--densify_grad_threshold", "0.00007",
            "--densify_until_iter", str(densify_until),
            "--opacity_reset_interval", "3000",
            "--lambda_dssim", "0.2",
            "--position_lr_max_steps", str(iterations),
            "--test_iterations", "7000", "30000", str(iterations),
            "--save_iterations", "7000", "30000", str(iterations),
            "--disable_viewer",
        ])

        train_cmd = [
            sys.executable, os.path.join(SCRIPTS_DIR, "train_gaussian.py"),
            "--source_path", colmap_dense,
            "--output_path", gaussian_dir,
            "--iterations", str(iterations),
        ] + gs_extra_args

        # 학습을 Popen으로 실행하여 진행률 파싱
        process = subprocess.Popen(
            train_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
            cwd=PROJECT_ROOT,
        )

        for line in process.stdout:
            # 학습 로그에서 iteration 진행률 파싱
            if "iteration" in line.lower() or "PSNR" in line:
                try:
                    # "Training progress 1000/60000" 또는 유사 패턴
                    import re
                    match = re.search(r'(\d+)/(\d+)', line)
                    if match:
                        current = int(match.group(1))
                        total = int(match.group(2))
                        pct = min(int(current / total * 100), 100)
                        _update_job(job_id, "training",
                                    f"학습 진행: {current:,}/{total:,} ({pct}%)",
                                    training_progress=pct)
                except Exception:
                    pass

        process.wait()
        if process.returncode != 0:
            _update_job(job_id, "failed", "Gaussian Splatting 학습 실패")
            return

        # ──────────────────────────────────────────────────────────
        # Step 6: 모델 Export + Pruning
        # ──────────────────────────────────────────────────────────
        _update_job(job_id, "exporting")

        ply_path = os.path.join(
            gaussian_dir, "point_cloud",
            f"iteration_{iterations}", "point_cloud.ply"
        )
        if not os.path.exists(ply_path):
            # fallback: 다른 iteration 체크
            for fallback_iter in [30000, 7000]:
                fallback_ply = os.path.join(
                    gaussian_dir, "point_cloud",
                    f"iteration_{fallback_iter}", "point_cloud.ply"
                )
                if os.path.exists(fallback_ply):
                    ply_path = fallback_ply
                    break
            else:
                _update_job(job_id, "failed", "학습 결과 PLY 파일을 찾을 수 없습니다.")
                return

        os.makedirs(model_output_dir, exist_ok=True)
        result = _run_subprocess(
            [sys.executable, os.path.join(SCRIPTS_DIR, "export_model.py"),
             "--input", ply_path,
             "--output", model_output_dir,
             "--format", "both",
             "--max_gaussians", str(max_gaussians),
             "--max_scale_factor", "10.0",
             "--max_aspect_ratio", "50",
             "--spatial_iqr", "4.0"],
            env=env, timeout=600, cwd=PROJECT_ROOT,
        )
        if result.returncode != 0:
            _update_job(job_id, "failed", f"모델 변환 실패: {result.stderr[-500:]}")
            return

        # ──────────────────────────────────────────────────────────
        # Step 7: DB 업데이트
        # ──────────────────────────────────────────────────────────
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

        elapsed = time.time() - job.get("started_at", time.time())
        minutes = int(elapsed // 60)

        _update_job(job_id, "completed",
                    f"3D 모델 생성 완료! (소요: {minutes}분)",
                    model_url=model_url)

    except subprocess.TimeoutExpired:
        _update_job(job_id, "failed", "처리 시간이 초과되었습니다.")
    except Exception as e:
        _update_job(job_id, "failed", f"오류: {str(e)}")


@router.post("/start")
async def start_pipeline(
    video: UploadFile = File(...),
    vehicle_id: Optional[int] = Form(None),
    quality: Optional[str] = Form("hq"),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """영상을 업로드하고 HQ 3D 파이프라인을 시작한다."""
    # Validate file type
    if not video.filename.lower().endswith((".mp4", ".mov", ".avi", ".mkv", ".webm")):
        raise HTTPException(status_code=400, detail="지원하지 않는 영상 형식입니다. (mp4, mov, avi, mkv, webm)")

    # File size limit (2GB)
    MAX_VIDEO_SIZE = 2 * 1024 * 1024 * 1024

    # Validate quality
    if quality not in ("standard", "hq", "ultra"):
        quality = "hq"

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
    if len(content) > MAX_VIDEO_SIZE:
        raise HTTPException(status_code=400, detail="영상 크기가 2GB를 초과합니다.")
    with open(video_path, "wb") as f:
        f.write(content)

    # Initialize job with detailed tracking
    pipeline_jobs[job_id] = {
        "status": "queued",
        "message": "대기 중...",
        "label": "대기 중",
        "vehicle_id": vehicle_id,
        "user_id": user.id,
        "model_url": None,
        "progress": 0,
        "step": 0,
        "total_steps": 7,
        "est_time": "",
        "quality": quality,
        "created_at": time.time(),
        "updated_at": time.time(),
    }

    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, run_pipeline_hq, job_id, video_path, vehicle_id, quality)

    return {
        "job_id": job_id,
        "vehicle_id": vehicle_id,
        "quality": quality,
        "message": f"3D 파이프라인이 시작되었습니다. (품질: {quality})",
    }


@router.get("/status/{job_id}")
async def get_pipeline_status(
    job_id: str,
    user: User = Depends(require_user),
):
    """파이프라인 진행 상태를 상세하게 조회한다. 본인 작업만 조회 가능."""
    if job_id not in pipeline_jobs:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")

    job = pipeline_jobs[job_id]

    if job.get("user_id") and job["user_id"] != user.id:
        raise HTTPException(status_code=403, detail="접근 권한이 없습니다.")

    # 경과 시간 계산
    elapsed = 0
    if "started_at" in job:
        elapsed = int(time.time() - job["started_at"])

    return {
        "status": job.get("status"),
        "message": job.get("message"),
        "label": job.get("label", ""),
        "progress": job.get("progress", 0),
        "step": job.get("step", 0),
        "total_steps": job.get("total_steps", 7),
        "est_time": job.get("est_time", ""),
        "quality": job.get("quality", "hq"),
        "vehicle_id": job.get("vehicle_id"),
        "model_url": job.get("model_url"),
        "elapsed_seconds": elapsed,
        "frame_count": job.get("frame_count"),
        "bg_removed": job.get("bg_removed"),
        "depth_generated": job.get("depth_generated"),
        "iterations": job.get("iterations"),
    }
