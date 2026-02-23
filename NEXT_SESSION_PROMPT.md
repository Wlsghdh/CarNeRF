# CarNeRF 다음 세션 프롬프트

## 이전 세션에서 완료한 것
1. **풀스택 프로토타입** 완성 - FastAPI + Jinja2 + Tailwind + Three.js
   - 홈/매물검색/차량상세/판매/로그인 5개 페이지
   - 12개 한국 중고차 시드 데이터 + AI 진단 리포트
   - JWT 인증, REST API, 3D 뷰어 임베드
   - 실행: `cd /home/jjh0709/Project_2026_1/backend && python run.py`

2. **3D 파이프라인 설치 완료**
   - pycolmap 3.13.0 (Python API - CLI colmap 없이 동작)
   - 3D Gaussian Splatting + CUDA 확장 (diff-gaussian-rasterization, simple-knn, fused-ssim)
   - PyTorch 2.5.1+cu121 on A100 80GB x2
   - **Truck 데이터셋 테스트 성공**: 3000 iterations / 69초 / 100만+ 가우시안 생성

3. **아직 테스트 안 한 것**
   - pycolmap API로 프레임에서 COLMAP 실행 (run_colmap.py를 pycolmap으로 개조했지만 실제 테스트 안 함)
   - 영상 → 프레임 추출 → COLMAP → 학습 전체 end-to-end 테스트
   - 학습된 3D 모델을 웹사이트에서 실시간 보기 (모델 파일은 만들어졌지만 웹 연동 안 됨)

## 이번 세션에서 할 것

### Phase 1: End-to-End 파이프라인 테스트
pycolmap API 기반 run_colmap.py가 실제로 잘 동작하는지 확인:
```bash
cd /home/jjh0709/Project_2026_1
# CUDA 환경 설정
export CUDA_HOME=/usr/local/cuda-12.2
export PATH=/usr/local/cuda-12.2/bin:$PATH

# 방법 1: 기존 truck 이미지로 COLMAP부터 직접 테스트
python scripts/run_colmap.py \
    --image_path data/raw/tandt/truck/images \
    --output_path data/colmap_output/truck_pycolmap

# 방법 2: 사용자 영상으로 전체 파이프라인 테스트
python scripts/run_pipeline.py \
    --input /path/to/car_video.mp4 \
    --name my_car \
    --iterations 7000
```

### Phase 2: 웹사이트에서 3D 모델 보기
truck 테스트 모델이 이미 있음: `/home/jjh0709/Project_2026_1/backend/app/static/models/truck_test/model.ply` (118MB), `model.splat` (15MB)

해야 할 것:
1. DB의 Vehicle 레코드에 `model_3d_url`과 `model_3d_status='ready'` 설정
2. 차량 상세 페이지에서 3D 탭 클릭하면 Three.js로 모델 렌더링
3. `/static/models/` 경로를 StaticFiles에 등록
4. 업로드 → 3D 변환 자동화 (백그라운드 태스크)

### Phase 3: 사용자 영상 → 3D 모델 자동화
사용자가 영상을 업로드하면 백그라운드에서:
1. 프레임 추출 (extract_frames.py)
2. COLMAP SfM (run_colmap.py - pycolmap API)
3. Gaussian Splatting 학습 (train_gaussian.py)
4. 모델 Export (export_model.py)
5. DB 업데이트 (model_3d_status: processing → ready)

### Phase 4 (향후): AI Defect Detection
- 3D 모델의 포인트 클라우드에서 균열, 찍힘, 부식 등 탐지
- 접근 방법: 3D 모델 렌더링 → 다각도 2D 이미지 생성 → CNN 기반 결함 탐지
- 또는: PointNet/PointNet++ 기반 3D 포인트 클라우드 직접 분석

## 핵심 파일 위치
- 파이프라인 스크립트: `scripts/run_pipeline.py`, `scripts/run_colmap.py` (pycolmap), `scripts/train_gaussian.py`, `scripts/export_model.py`
- 백엔드: `backend/app/main.py`, `backend/run.py`
- 3D 뷰어: `backend/app/static/js/viewer.js`
- Gaussian Splatting: `third_party/gaussian-splatting/`
- 테스트 모델: `backend/app/static/models/truck_test/model.ply`, `model.splat`

## 주의사항
- `CUDA_HOME=/usr/local/cuda-12.2` 반드시 설정
- sudo 없음 - 시스템 패키지 설치 불가
- pycolmap API 함수 시그니처가 버전별로 다를 수 있음 - 에러 시 `python -c "help(pycolmap.extract_features)"` 등으로 확인
- 웹 서버: `cd backend && python run.py` (포트 8000)
