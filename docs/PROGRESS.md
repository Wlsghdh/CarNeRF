# CarNeRF 프로젝트 진행 상황

## 최종 업데이트: 2026-02-14

---

## 1. 완료된 작업

### 1.1 풀스택 웹 프로토타입 (100% 완료)
- **기술 스택**: FastAPI + Jinja2 SSR + Tailwind CSS CDN + Pretendard 폰트
- **실행**: `cd /home/jjh0709/Project_2026_1/backend && nohup python run.py > server.log 2>&1 &`
- **접속**: http://localhost:8000
- **구현된 페이지**:
  | 경로 | 설명 | 상태 |
  |------|------|------|
  | `/` | 홈 - 히어로, 이용방법, 추천매물, 핵심기능 | 완료 |
  | `/listings` | 매물 검색 - 필터(브랜드/연료/가격/연식), 정렬, 페이지네이션 | 완료 |
  | `/vehicles/{id}` | 차량 상세 - 사진/3D 탭, 스펙, AI 진단 리포트 | 완료 |
  | `/sell` | 내 차 팔기 - 다단계 등록 폼 + 3D 영상 업로드 | 완료 |
  | `/login` | 로그인/회원가입 | 완료 |
  | `/viewer/{id}` | 전체화면 3D 뷰어 | 완료 |

- **REST API**:
  | 엔드포인트 | 설명 |
  |-----------|------|
  | `GET /api/vehicles/` | 차량 목록 (필터 지원) |
  | `GET /api/vehicles/{id}` | 차량 상세 |
  | `GET /api/vehicles/{id}/diagnosis` | AI 진단 리포트 |
  | `GET /api/listings/` | 매물 목록 (필터/정렬/페이지네이션) |
  | `POST /api/listings/` | 매물 등록 (로그인 필요) |
  | `POST /api/auth/login` | 로그인 (JWT httpOnly cookie) |
  | `POST /api/auth/register` | 회원가입 |
  | `POST /api/auth/logout` | 로그아웃 |
  | `POST /api/pipeline/start` | 3D 파이프라인 시작 (영상 업로드) |
  | `GET /api/pipeline/status/{job_id}` | 파이프라인 진행 상태 조회 |

- **DB**: SQLite, 4개 테이블 (User, Vehicle, Listing, DiagnosisReport)
- **시드 데이터**: 12개 한국 중고차, 2명 사용자, 12개 진단 리포트
- **데모 계정**: demo@carnerf.kr / demo1234

### 1.2 3D 파이프라인 설치 (100% 완료)
- **pycolmap 3.13.0** - COLMAP Python API (CLI colmap 바이너리 없이 동작)
- **3D Gaussian Splatting** - `third_party/gaussian-splatting/` 에 클론
- **CUDA 확장 빌드 완료**: diff-gaussian-rasterization, simple-knn, fused-ssim
- **PyTorch 2.5.1+cu121** (원래 cu118이었으나 CUDA 12.2 호환을 위해 재설치)
- **환경**: A100 80GB x2, CUDA 12.2, Ubuntu 22.04

### 1.3 전체 파이프라인 End-to-End 테스트 (완료)
- **데이터**: Tanks & Temples truck 데이터셋 (251장 중 30장 선택)
- **CLI 실행 결과**:
  | 단계 | 소요 시간 | 결과 |
  |------|----------|------|
  | 프레임 추출 (251장 → 30장) | 5.4초 | 성공 |
  | COLMAP SfM (카메라 위치 추정) | 21.5초 | 30/30 이미지 등록, 8,875 3D 포인트 |
  | Gaussian Splatting (3000 iter) | 69.3초 | 1M+ 가우시안 생성 |
  | 모델 Export (PLY + SPLAT) | 4.2초 | PLY 108MB, SPLAT 14MB |
  | **총 소요 시간** | **1분 40초** | **성공** |
- **웹사이트 연동**: 첫 번째 차량(현대 그랜저) 상세 페이지에서 3D 뷰어 탭 클릭으로 확인 가능

### 1.4 웹 영상 업로드 → 3D 자동 변환 (구현 완료)
- `/sell` 페이지에서 영상 업로드 → 백그라운드 3D 변환 → 완료 시 뷰어 링크
- 프론트엔드: 진행률 표시 (프레임 추출 15% → COLMAP 35% → 학습 65% → 변환 85% → 완료 100%)
- 백엔드: asyncio run_in_executor로 백그라운드 실행, 상태 폴링 API 제공
- **API 동작 확인 완료**

### 1.5 NF소나타 실제 차량 3D 모델 생성 (완료)
- **영상**: `NF소나타.mp4` (13MB, 1080x1920, 32.2초)
- **최종 HQ 설정**: 200프레임, 원본 해상도, sequential matching, 60K iterations
- **튜닝된 하이퍼파라미터**: `densify_grad_threshold=0.0001`, `lambda_dssim=0.4`, `densify_until_iter=25000`
- **결과**: PSNR 31.88, L1 0.0156, 2M 가우시안, 61MB SPLAT
- **배포**: vehicle_id=19, http://localhost:8000/viewer/19
- **총 8회 반복 실험** (해상도/배경제거/후처리 등 다양한 시도)
- **소요 시간**: 140.8분 (COLMAP 36.1분 + GS 104.3분)

---

## 2. 다음에 할 것

### 2.1 3D 품질 추가 향상 (최우선)
- 현재 사용자 피드백: "아직 더 필요해보인다"
- **접근 방안**:
  - 영상 길이 늘리기 (32초 → 60초+, 다양한 각도)
  - 배경 제거 (SAM 기반 마스크 → post-processing 또는 masked training)
  - GS 100K iterations (완전 수렴)
  - 대안 기술 검토 (2DGS, Mip-Splatting, SuGaR)
- **상세**: `docs/NEXT_SESSION_PROMPT.md` 참조

### 2.2 AI 결함 탐지 (미구현)
- 목표: 3D 모델/이미지에서 균열, 찍힘, 부식, 도장 벗겨짐 등 자동 탐지
- 접근법 후보:
  - A) 프레임 이미지에서 YOLOv8 등으로 결함 탐지
  - B) 다각도 2D 렌더링 → CNN 결함 탐지
  - C) PointNet/PointNet++ 기반 3D 포인트 클라우드 분석

---

## 3. 빠른 시작 가이드

### 서버 실행
```bash
cd /home/jjh0709/Project_2026_1/backend
nohup python run.py > server.log 2>&1 &
# http://localhost:8000 접속
```

### 서버 종료
```bash
fuser -k 8000/tcp
```

### CLI로 3D 파이프라인 실행
```bash
cd /home/jjh0709/Project_2026_1
export CUDA_HOME=/usr/local/cuda-12.2
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1

# 영상 파일 입력
python scripts/run_pipeline.py \
  --input /path/to/video.mp4 \
  --name my_car \
  --max_frames 60 \
  --iterations 7000

# 이미지 폴더 입력
python scripts/run_pipeline.py \
  --input /path/to/images/ \
  --name my_car \
  --max_frames 60 \
  --iterations 7000
```

### 웹사이트에서 3D 업로드
1. http://localhost:8000/login → demo@carnerf.kr / demo1234
2. http://localhost:8000/sell → 차량 정보 입력 → "3D 스캔" 섹션에서 영상 선택
3. 자동으로 파이프라인 실행, 진행률 표시

---

## 4. 프로젝트 파일 구조

```
Project_2026_1/
├── backend/                          # 웹 프로토타입
│   ├── run.py                        # 서버 실행
│   ├── server.log                    # 서버 로그
│   ├── carnerf.db                    # SQLite DB (자동 생성)
│   └── app/
│       ├── main.py                   # FastAPI 앱
│       ├── config.py                 # 설정
│       ├── database.py               # SQLAlchemy
│       ├── models.py                 # DB 모델 4개
│       ├── schemas.py                # Pydantic 스키마
│       ├── dependencies.py           # 인증, DB 세션
│       ├── api/
│       │   ├── pages.py              # HTML 페이지 라우트
│       │   ├── vehicles.py           # 차량 API
│       │   ├── listings.py           # 매물 API
│       │   ├── auth.py               # 인증 API
│       │   ├── upload.py             # 파일 업로드 API
│       │   └── pipeline.py           # 3D 파이프라인 API
│       ├── services/
│       │   └── seed_data.py          # 12개 시드 데이터
│       ├── templates/                # Jinja2 HTML 7개
│       └── static/
│           ├── css/custom.css
│           ├── js/
│           │   ├── viewer.js         # Three.js 3D 뷰어
│           │   ├── listings.js       # 매물 검색 필터
│           │   └── sell.js           # 매물 등록 + 3D 업로드
│           ├── images/
│           └── models/truck_test/    # 3D 모델 (PLY + SPLAT)
├── scripts/                          # 3D 파이프라인 스크립트
│   ├── run_pipeline.py               # 전체 파이프라인 통합
│   ├── extract_frames.py             # 영상 → 프레임 추출
│   ├── run_colmap.py                 # pycolmap SfM
│   ├── train_gaussian.py             # Gaussian Splatting 학습
│   └── export_model.py              # PLY/SPLAT 변환
├── third_party/
│   └── gaussian-splatting/           # 3D GS 공식 레포
├── data/
│   ├── raw/tandt/truck/              # 벤치마크 데이터
│   ├── frames/                       # 추출된 프레임
│   ├── colmap_output/                # COLMAP 결과
│   └── gaussian_output/              # 학습 결과
├── web_viewer/                       # 독립 3D 뷰어 (참고용)
└── docs/
    └── PROGRESS.md                   # 이 파일
```

---

## 5. 환경 정보

| 항목 | 값 |
|------|-----|
| OS | Ubuntu 22.04.5 LTS |
| GPU | NVIDIA A100 80GB PCIe x 2 |
| CUDA | 12.2 (드라이버 535.183.01) |
| Python | 3.11 (conda env: jjh) |
| PyTorch | 2.5.1+cu121 |
| COLMAP | pycolmap 3.13.0 (Python API) |
| CUDA_HOME | `/usr/local/cuda-12.2` |
| sudo | 없음 |

---

## 6. 알려진 이슈 & 해결법

| 이슈 | 해결 |
|------|------|
| passlib + bcrypt 5.x 호환 안 됨 | sha256 + salt 방식으로 대체 |
| email-validator 미설치 | Pydantic EmailStr 대신 plain str |
| JWT sub은 반드시 str | python-jose 요구사항, `str(user.id)` 사용 |
| pycolmap matching segfault | `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1` 설정 |
| pycolmap undistort 출력 구조 | `dense/sparse/` → `dense/sparse/0/` 자동 변환 (run_colmap.py) |
| CUDA_HOME 미설정 | `export CUDA_HOME=/usr/local/cuda-12.2` |
