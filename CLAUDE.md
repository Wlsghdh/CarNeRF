# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CarNeRF — 중고차 3D 모델링 + AI 결함 탐지 플랫폼. 차량 영상 → 3D Gaussian Splatting → 웹 3D 뷰어 + AI 결함 분석.

## Environment

- **Conda env**: `jjh` (Python 3.11, PyTorch 2.5.1+cu121)
- **CUDA**: 12.2 — always set `export CUDA_HOME=/usr/local/cuda-12.2` before GPU ops
- **GPU**: A100 80GB x2
- **No sudo** access

## Common Commands

```bash
# Start web server (from Project_2026_1/)
cd backend && python run.py        # → http://localhost:8000
fuser -k 8000/tcp                  # Kill server

# Full pipeline (standard, ~45 min on A100)
conda activate jjh
export CUDA_HOME=/usr/local/cuda-12.2
python scripts/run_pipeline.py --input /path/to/video.mp4 --name my_car

# Full pipeline (HQ mode: bg removal + depth + 60K iter, ~140 min)
python scripts/run_pipeline.py --input /path/to/video.mp4 --name my_car --hq

# HQ pipeline from existing COLMAP output (skip video → COLMAP steps)
python scripts/train_hq.py \
    --source_path data/colmap_output/<name>/dense \
    --output_path data/gaussian_output/<name> \
    --iterations 60000

# Individual pipeline steps
python scripts/extract_frames.py --input video.mp4 --output data/frames/<name> --fps 2
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python scripts/run_colmap.py \
    --image_path data/frames/<name> --output_path data/colmap_output/<name>
python scripts/train_gaussian.py --source_path <colmap_dense> --output_path <out> --iterations 30000
python scripts/export_model.py --input <ply_path> --output <dir> --format both
```

## Architecture

### Backend (FastAPI + Jinja2 SSR)

The server is **fullstack SSR** — FastAPI serves both HTML pages and a REST API from the same process. Run from `backend/` with `python run.py`.

**Route structure:**
- `app/api/pages.py` — SSR HTML pages (`/`, `/listings`, `/vehicles/{id}`, `/sell`, `/login`, `/viewer/{id}`)
- `app/api/auth.py` — `POST /api/auth/login|register|logout`
- `app/api/vehicles.py` — `GET/POST /api/vehicles`
- `app/api/listings.py` — `GET/POST /api/listings`
- `app/api/upload.py` — `POST /api/upload`
- `app/api/pipeline.py` — `POST /api/pipeline/start`, `GET /api/pipeline/status/{job_id}`

**Templates**: Jinja2 in `app/templates/`. Base template: `base.html`. Pages: `home`, `listings`, `vehicle_detail`, `sell`, `login`, `viewer`.

**Auth**: Cookie-based JWT. Token stored in `httponly` cookie `access_token`. `get_current_user()` returns `None` (unauthenticated OK); `require_user()` raises 401.

**config.py `BASE_DIR`**: Points to `backend/`. `os.path.dirname(BASE_DIR)` = `Project_2026_1/`.

### 3D Pipeline

```
영상 → extract_frames.py → run_colmap.py → [remove_background.py + generate_depths.py] → train_gaussian.py → export_model.py → backend/app/static/models/<name>/model.splat
```

- `run_pipeline.py` orchestrates all steps; `train_hq.py` orchestrates steps 3–5 only (from COLMAP output)
- GS training delegates to `third_party/gaussian-splatting/train.py` via subprocess
- `export_model.py --output <dir>` writes `<dir>/model.ply` and `<dir>/model.splat`
- Web-served model path: `backend/app/static/models/<name>/model.splat` → URL `/static/models/<name>/model.splat`

**Pipeline API** (`app/api/pipeline.py`): In-memory job tracking dict (`pipeline_jobs`). Jobs run in `ThreadPoolExecutor` via `loop.run_in_executor`. No Celery/Redis.

### DB

SQLite at `backend/carnerf.db`. Auto-created on startup via `Base.metadata.create_all()` + seeded by `services/seed_data.py`.

Models: `User` → `Listing` (1:1) ← `Vehicle` → `DiagnosisReport` (1:1). `Vehicle.model_3d_status`: `none | processing | ready`.

Demo account: `demo@carnerf.kr` / `demo1234`

## Key Technical Gotchas

- **pycolmap segfault**: Must run with `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1`
- **pycolmap API**: Use `match_sequential` for video frames (not `exhaustive` — segfaults on large sets). Check `python -c "help(pycolmap.extract_features)"` if API errors occur.
- **GS alpha mask**: RGBA PNG → auto background masking. Pass `--images images_masked` to use rembg output.
- **GS depth**: Requires both `--depths depths` arg AND `sparse/0/depth_params.json`. If `depth_params.json` missing, depth regularization is silently disabled in `train_hq.py`.
- **rembg**: Falls back to CPU on this server (libcudnn.so.9 missing for onnxruntime). ~29s/image.
- **Password hashing**: Using `hashlib.sha256` with random salt (format: `{salt}${hash}`). Not bcrypt — bcrypt>=5.x broken.
- **JWT `sub` claim**: Must be `str(user.id)`, not int.
- **FastAPI Query**: Use `pattern=` not `regex=` (deprecated).
- **Pydantic email**: Use plain `str` (no `EmailStr` — email-validator not installed).

## Agent Roles

### Agent 1: 3D Pipeline
- **Files**: `scripts/`, `third_party/gaussian-splatting/` (read-only)
- **Goal**: PSNR 34+ (current best: 31.88 @ HQ 60K iter), floater removal, background masking quality

### Agent 2: AI Defect Detection
- **Files**: `scripts/defect_detection/` (new), `backend/app/api/defect.py` (new)
- **Approach**: 3D render → multi-view 2D → YOLO/SAM defect detection, or PointNet on point cloud
- **Output**: Defect location + severity JSON API

### Agent 3: Backend API
- **Files**: `backend/`
- **Focus**: FastAPI endpoints, SQLAlchemy models, JWT auth, pipeline integration

### Agent 4: Frontend/App
- **Files**: `backend/app/templates/`, `backend/app/static/`, future app project
- **Stack**: Jinja2+Tailwind (web), React Native or Flutter (mobile app)

### Agent 5: DevOps/Infra
- **Files**: `Dockerfile`, `docker-compose.yml`, nginx config (all new)
- **Focus**: Containerization, GPU job queue, model serving
