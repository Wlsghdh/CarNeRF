# CLAUDE.md

## Project
CarNeRF — 중고차 3D 모델링 + AI 결함 탐지 플랫폼. 영상→3DGS→웹뷰어+AI분석.

## Env
- **Conda**: `jjh` (Python 3.11, PyTorch 2.5.1+cu121)
- **CUDA**: 12.2 → `export CUDA_HOME=/usr/local/cuda-12.2`
- **GPU**: A100 80GB (공유 서버, 1인 1GPU, GPU 4/5/6 사용금지), **No sudo**

## Commands
```bash
cd backend && python run.py                    # 서버 http://localhost:8000
fuser -k 8000/tcp                              # 서버 종료
python scripts/run_pipeline.py --input v.mp4 --name car --hq  # HQ 3D파이프라인
python scripts/train_hq.py --source_path data/colmap_output/x/dense --output_path out --iterations 60000
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

## 3D Quality (Current Best: PSNR 31.88)
HQ 파라미터: densify_grad=0.00007, densify_until=35K, lambda_dssim=0.2, antialiasing=ON
Target: PSNR 34+ → 더 낮은 densify_grad, 100K iter, sparse_adam 테스트 중

## Agents
- Agent 1 (3D Pipeline): `scripts/`, PSNR 개선, floater 제거
- Agent 2 (AI Defect): `scripts/defect_detection/`, YOLOv8/SAM
- Agent 3 (Backend): `backend/app/api/`, FastAPI, JWT, DB
- Agent 4 (Frontend): `backend/app/templates/`, `static/`, Jinja2+Tailwind
- Agent 5 (DevOps): Docker, GPU queue, model serving
