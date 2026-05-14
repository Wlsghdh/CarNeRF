# CLAUDE.md

## Project
CarNeRF — 중고차 3D 모델링 + AI 결함 탐지 플랫폼. 영상→3DGS→웹뷰어+AI분석.

## Env
- **Conda**: `jjh` (Python 3.11, PyTorch 2.5.1+cu121) — 메인 환경 (래퍼/Backend/CV)
- **Conda**: `fastgs` (Python 3.7, PyTorch 1.12.1+cu116, conda nvcc 11.8) — FastGS 학습 전용
- **CUDA**: 시스템 12.2 / FastGS 빌드는 `CUDA_HOME=$CONDA_PREFIX` (env 내 nvcc 11.8)
- **GPU**: A100 80GB (공유 서버, 1인 1GPU, GPU 4/5/6 사용금지), **No sudo**

## Commands
```bash
cd backend && python run.py                    # 서버 http://localhost:5199
fuser -k 5199/tcp                              # 서버 종료
python scripts/run_pipeline.py --input v.mp4 --name car --hq  # HQ 파이프라인 (기본 engine=fastgs)
python scripts/train_hq.py --source_path data/colmap_output/x/dense --output_path out  # FastGS 30K iter 기본
python scripts/train_fastgs.py --source_path .../dense --output_path out --iterations 30000  # FastGS 직접
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python scripts/run_colmap.py --image_path frames --output_path out
```

## Architecture
- **Backend**: FastAPI + Jinja2 SSR, SQLite, Cookie JWT auth
- **API prefix**: `/api/auth|vehicles|listings|pipeline|predict|defect|ai|market|wishlist|upload|points|reviews|transactions|seller|search|stats`
- **Templates**: `app/templates/` (base,home,listings,vehicle_detail,sell,login,mypage,viewer,error)
- **3D Pipeline**: extract_frames→COLMAP→[rembg+depth]→GaussianSplatting→export→web
- **ML**: YOLOv8 결함탐지, LightGBM 가격예측, ChatGPT 요약(OPENAI_API_KEY)

## DB Models
User→Listing(1:1)←Vehicle→DiagnosisReport, Wishlist, LoginHistory, PointTransaction, UserReview, TransactionHistory

## Key Gotchas
- pycolmap: `OPENBLAS_NUM_THREADS=1` 필수 (segfault 방지)
- Password: `hashlib.sha256` + salt (bcrypt 아님)
- JWT sub: `str(user.id)`, FastAPI Query: `pattern=` not `regex=`
- GS depth: `depth_params.json` 없으면 depth 자동 비활성화
- rembg: CPU fallback (~29s/img), export_model.py: 2DGS는 scale_2 없음

## 3D Engine (기본: FastGS — CVPR 2026)
- **FastGS** 기본 활성. 30K iter ≈ 2~3분 (A100, vanilla 60K 대비 15× 가속). 별도 `fastgs` conda env에서 실행.
- 주요 파라미터: `--grad_abs_thresh 0.0009`, `--densification_interval 500`, `--mult 0.7`, `--highfeature_lr 0.04`
- `--engine vanilla` 로 기존 vanilla 3DGS 사용 가능 (HQ 파라미터: densify_grad=0.00007, densify_until=35K, lambda_dssim=0.2)
- 2DGS/MCMC 변형은 `scripts/train_2dgs.py`, `scripts/train_mcmc.py` 그대로 보존 (옵션 엔진)
- PLY 포맷은 vanilla GS와 100% 동일 — `export_model.py` 무수정 호환

## Agents
- Agent 1 (3D Pipeline): `scripts/`, PSNR 개선, floater 제거
- Agent 2 (AI Defect): `scripts/defect_detection/`, YOLOv8/SAM
- Agent 3 (Backend): `backend/app/api/`, FastAPI, JWT, DB
- Agent 4 (Frontend): `backend/app/templates/`, `static/`, Jinja2+Tailwind
- Agent 5 (DevOps): Docker, GPU queue, model serving
