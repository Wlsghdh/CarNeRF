# CarNeRF Project Instructions

## Project Overview
중고차 3D 모델링 + AI 결함 탐지 플랫폼. 차량 영상 → 3D Gaussian Splatting → 웹 3D 뷰어 + AI 결함 분석.

## Environment
- **Conda env**: `jjh` (Python 3.11, PyTorch 2.5.1+cu121)
- **CUDA**: 12.2 (`CUDA_HOME=/usr/local/cuda-12.2`)
- **GPU**: A100 80GB x2
- **No sudo** access
- **Server**: `cd backend && python run.py` → http://localhost:8000

## Project Structure
```
Project_2026_1/
├── backend/          # FastAPI + Jinja2 SSR + Tailwind (fullstack)
│   ├── app/
│   │   ├── static/models/   # 3D .splat 모델 서빙 위치
│   │   ├── templates/       # Jinja2 HTML 템플릿
│   │   └── static/js/viewer.js  # Three.js 3D 뷰어
│   └── carnerf.db           # SQLite DB
├── scripts/          # 파이프라인 스크립트
│   ├── remove_background.py  # rembg 배경 제거 → RGBA PNG
│   ├── generate_depths.py    # Depth Anything V2 depth map
│   ├── train_gaussian.py     # GS 학습 래퍼
│   ├── export_model.py       # PLY→SPLAT 변환 + pruning
│   ├── train_hq.py           # HQ 오케스트레이터
│   ├── run_pipeline.py       # 전체 파이프라인 (--hq 모드)
│   ├── extract_frames.py     # 영상 → 프레임 추출
│   └── run_colmap.py         # pycolmap SfM
├── third_party/gaussian-splatting/  # 공식 GS (수정하지 않음)
├── data/             # COLMAP/GS 데이터
└── docs/             # 프로젝트 문서
```

## Agent Roles (프로젝트 작업 분류)

### Agent 1: 3D Pipeline (최우선)
- **역할**: 3D 모델링 품질 향상, 파이프라인 최적화
- **파일**: `scripts/`, `third_party/gaussian-splatting/` (읽기만)
- **핵심 명령**: `python scripts/train_hq.py --source_path ... --output_path ...`
- **목표**: PSNR 34+ (현재 31.88), floater 제거, 배경 제거 품질

### Agent 2: AI Defect Detection
- **역할**: 차량 외관 결함 자동 탐지 (스크래치, 찌그러짐, 도색)
- **파일**: `scripts/defect_detection/` (신규), `backend/app/api/defect.py` (신규)
- **기술**: YOLO / Segment Anything / 커스텀 모델
- **산출물**: 결함 위치 + 심각도 JSON API

### Agent 3: Backend API
- **역할**: FastAPI REST API, DB, JWT 인증, 파이프라인 연동
- **파일**: `backend/`
- **주의**: python-jose sub=str, passlib→hashlib, plain str for email

### Agent 4: Frontend/App
- **역할**: 웹 UI + 3D 뷰어 + 모바일 앱
- **파일**: `backend/app/templates/`, `backend/app/static/`, 앱 프로젝트 (신규)
- **기술**: Jinja2+Tailwind (웹), React Native or Flutter (앱)

### Agent 5: DevOps/Infra
- **역할**: Docker, CI/CD, GPU 작업 큐, 모델 서빙
- **파일**: `Dockerfile`, `docker-compose.yml`, nginx 설정

## Key Technical Gotchas
- pycolmap segfault: `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1`
- pycolmap: `match_sequential` (not exhaustive)
- GS alpha_mask: RGBA PNG → 자동 배경 마스킹 (cameras.py:44-48)
- GS depth: `--depths depths` + `sparse/0/depth_params.json`
- SPLAT 모델 서빙: `backend/app/static/models/<name>/model.splat`
- Demo account: demo@carnerf.kr / demo1234
