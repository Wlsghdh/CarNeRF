# CarNeRF - 차량 3D 재구성 프로젝트

> Gaussian Splatting 기반 차량 3D 재구성 파이프라인

## 프로젝트 소개

CarNeRF는 차량 영상 또는 사진으로부터 고품질 3D 모델을 생성하는 프로젝트입니다.
기존 NeRF(Neural Radiance Fields) 방식 대비 훨씬 빠른 학습과 렌더링 속도를 제공하는
**3D Gaussian Splatting** 기술을 핵심으로 활용합니다.

### 주요 특징

- **빠른 학습 속도**: A100 GPU 기준 차량 1대당 약 20~40분 학습 완료
- **고품질 렌더링**: 차량 외관의 세밀한 디테일(도장, 반사, 곡면)까지 재현
- **웹 뷰어 제공**: 학습된 3D 모델을 브라우저에서 바로 확인 가능
- **자동화 파이프라인**: 영상 입력부터 3D 모델 내보내기까지 단일 스크립트로 실행

---

## 디렉토리 구조

```
Project_2026_1/
├── README.md                   # 프로젝트 개요 (현재 문서)
├── requirements.txt            # Python 의존성 패키지 목록
│
├── docs/                       # 문서
│   ├── PIPELINE_FLOW.md        #   파이프라인 상세 흐름
│   ├── DATA_GUIDE.md           #   데이터 수집 가이드
│   └── SETUP.md                #   환경 설정 가이드
│
├── scripts/                    # 실행 스크립트
│   ├── run_pipeline.py         #   전체 파이프라인 통합 실행
│   ├── extract_frames.py       #   영상에서 프레임 추출
│   ├── run_colmap.py           #   COLMAP SfM 실행
│   ├── train_gaussian.py       #   Gaussian Splatting 학습
│   ├── export_model.py         #   학습된 모델 내보내기
│   └── setup_env.sh            #   환경 설정 자동화 스크립트
│
├── data/                       # 데이터 디렉토리
│   ├── raw/                    #   원본 영상/사진
│   ├── frames/                 #   추출된 프레임 이미지
│   ├── colmap_output/          #   COLMAP SfM 결과물
│   └── gaussian_output/        #   Gaussian Splatting 학습 결과물
│
├── third_party/                # 외부 라이브러리
│   └── gaussian-splatting/     #   3D Gaussian Splatting 공식 저장소
│
└── web_viewer/                 # 웹 기반 3D 뷰어
    ├── index.html
    ├── main.js
    └── style.css
```

---

## 빠른 시작 가이드

### 1. 환경 설정

```bash
# conda 환경 생성 및 활성화
conda create -n carnerf python=3.10 -y
conda activate carnerf

# 의존성 설치
pip install -r requirements.txt

# 환경 설정 스크립트 실행 (COLMAP, Gaussian Splatting 등)
bash scripts/setup_env.sh
```

> 상세한 설정 방법은 [docs/SETUP.md](docs/SETUP.md)를 참고하세요.

### 2. 데이터 준비

차량 영상 또는 사진을 `data/raw/` 디렉토리에 배치합니다.

```bash
# 예시: 영상 파일 복사
cp /path/to/car_video.mp4 data/raw/
```

> 데이터 촬영 가이드는 [docs/DATA_GUIDE.md](docs/DATA_GUIDE.md)를 참고하세요.

### 3. 전체 파이프라인 실행

```bash
conda activate carnerf

# 전체 파이프라인 한 번에 실행
python scripts/run_pipeline.py \
    --input data/raw/car_video.mp4 \
    --output data/gaussian_output/car_01
```

### 4. 개별 단계 실행 (선택사항)

필요한 경우 각 단계를 개별적으로 실행할 수 있습니다.

```bash
# Step 1: 프레임 추출
python scripts/extract_frames.py \
    --video data/raw/car_video.mp4 \
    --output data/frames/car_01 \
    --fps 2

# Step 2: COLMAP SfM 실행
python scripts/run_colmap.py \
    --images data/frames/car_01 \
    --output data/colmap_output/car_01

# Step 3: Gaussian Splatting 학습
python scripts/train_gaussian.py \
    --source data/colmap_output/car_01 \
    --output data/gaussian_output/car_01 \
    --iterations 30000

# Step 4: 모델 내보내기
python scripts/export_model.py \
    --model data/gaussian_output/car_01 \
    --format ply
```

### 5. 결과 확인 (웹 뷰어)

```bash
# 간단한 HTTP 서버로 웹 뷰어 실행
cd web_viewer
python -m http.server 8080
```

브라우저에서 `http://localhost:8080`으로 접속하여 3D 모델을 확인합니다.

---

## 파이프라인 개요

```
입력 영상/사진 → 프레임 추출 → COLMAP SfM → Gaussian Splatting 학습 → 3D 모델 내보내기 → 웹 뷰어
```

| 단계 | 설명 | 소요 시간 (A100) |
|------|------|------------------|
| 프레임 추출 | 영상에서 학습용 이미지 프레임 추출 | ~1분 |
| COLMAP SfM | 카메라 포즈 추정 및 희소 포인트 클라우드 생성 | 5~15분 |
| Gaussian Splatting 학습 | 3D Gaussian 표현 최적화 | 20~40분 |
| 모델 내보내기 | PLY 또는 뷰어 호환 형식으로 변환 | ~1분 |

> 파이프라인 상세 흐름은 [docs/PIPELINE_FLOW.md](docs/PIPELINE_FLOW.md)를 참고하세요.

---

## 기술 스택

| 구분 | 기술 |
|------|------|
| 3D 재구성 | 3D Gaussian Splatting |
| Structure-from-Motion | COLMAP |
| 딥러닝 프레임워크 | PyTorch 2.0+ |
| GPU | NVIDIA A100 (권장) |
| 웹 뷰어 | Three.js 기반 커스텀 뷰어 |
| 언어 | Python 3.10+ |

---

## 참고 문헌 및 크레딧

### 핵심 논문

1. **3D Gaussian Splatting for Real-Time Radiance Field Rendering**
   - Kerbl, B., Kopanas, G., Leimkuehler, T., & Drettakis, G. (2023)
   - ACM Transactions on Graphics (SIGGRAPH 2023)
   - [논문 링크](https://repo-sam.inria.fr/fungraph/3d-gaussian-splatting/)

2. **NeRF: Representing Scenes as Neural Radiance Fields for View Synthesis**
   - Mildenhall, B. et al. (2020)
   - ECCV 2020
   - [논문 링크](https://www.matthewtancik.com/nerf)

3. **COLMAP - Structure-from-Motion and Multi-View Stereo**
   - Schoenberger, J.L., & Frahm, J.M. (2016)
   - CVPR 2016
   - [공식 문서](https://colmap.github.io/)

### 오픈소스 프로젝트

- [3D Gaussian Splatting 공식 저장소](https://github.com/graphdeco-inria/gaussian-splatting) - INRIA
- [COLMAP](https://github.com/colmap/colmap) - ETH Zurich
- [Tanks and Temples Benchmark](https://www.tanksandtemples.org/)

### 라이선스

본 프로젝트는 연구 목적으로 개발되었습니다.
사용된 외부 라이브러리 및 모델의 라이선스를 각각 확인해 주세요.

---

## 문의

프로젝트 관련 문의사항이 있으시면 이슈를 등록해 주세요.
