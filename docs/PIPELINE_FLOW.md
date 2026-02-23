# CarNeRF 파이프라인 상세 흐름

본 문서는 CarNeRF 프로젝트의 전체 파이프라인을 상세히 설명합니다.

---

## 전체 파이프라인 다이어그램

```
 ┌─────────────────────────────────────────────────────────────────────────┐
 │                     CarNeRF 파이프라인 전체 흐름                         │
 └─────────────────────────────────────────────────────────────────────────┘

  [입력 데이터]          [전처리]            [3D 재구성]          [출력]
  ============       =============      ===============     ==========

  ┌──────────┐       ┌─────────────┐    ┌──────────────┐    ┌─────────┐
  │  차량    │       │  프레임      │    │  COLMAP      │    │  PLY    │
  │  영상    │──────>│  추출       │───>│  SfM         │    │  모델   │
  │ (.mp4)  │       │             │    │              │    │  파일   │
  └──────────┘       └─────────────┘    └──────┬───────┘    └────▲────┘
                                               │                 │
  ┌──────────┐              │                  │                 │
  │  차량    │              │                  ▼                 │
  │  사진    │──────────────┘           ┌──────────────┐   ┌────┴────┐
  │ (.jpg)  │                          │  Gaussian    │   │  모델   │
  └──────────┘                          │  Splatting   │──>│  내보내기│
                                        │  학습        │   │         │
                                        └──────────────┘   └────┬────┘
                                                                │
                                                                ▼
                                                          ┌──────────┐
                                                          │  웹 뷰어  │
                                                          │  시각화   │
                                                          └──────────┘
```

### 데이터 흐름 요약

```
영상/사진
   │
   ▼
data/raw/              원본 영상 또는 사진 파일
   │
   ▼  [extract_frames.py]
data/frames/           추출된 프레임 이미지 (JPEG/PNG)
   │
   ▼  [run_colmap.py]
data/colmap_output/    카메라 파라미터 + 희소 포인트 클라우드
   │
   ▼  [train_gaussian.py]
data/gaussian_output/  학습된 3D Gaussian 모델
   │
   ▼  [export_model.py]
*.ply / viewer 형식    최종 3D 모델 파일
```

---

## 단계별 상세 설명

### Step 1: 프레임 추출 (Frame Extraction)

차량 영상에서 학습에 사용할 이미지 프레임을 추출하는 단계입니다.
이미 촬영한 사진을 사용하는 경우 이 단계를 건너뛸 수 있습니다.

```
┌──────────────────────────────────────────────────────────────┐
│  Step 1: 프레임 추출                                          │
│                                                              │
│  입력: data/raw/car_video.mp4                                 │
│    │                                                         │
│    ▼                                                         │
│  OpenCV VideoCapture로 영상 디코딩                             │
│    │                                                         │
│    ▼                                                         │
│  지정된 FPS 간격으로 프레임 샘플링                               │
│    │                                                         │
│    ▼                                                         │
│  블러 감지 (Laplacian variance) → 흐린 프레임 제거              │
│    │                                                         │
│    ▼                                                         │
│  출력: data/frames/car_01/frame_00001.jpg, ...                │
└──────────────────────────────────────────────────────────────┘
```

| 항목 | 내용 |
|------|------|
| **스크립트** | `scripts/extract_frames.py` |
| **입력** | 영상 파일 (`.mp4`, `.avi`, `.mov` 등) |
| **출력** | 프레임 이미지 (`.jpg`) → `data/frames/<scene_name>/` |
| **주요 파라미터** | `--fps` (추출 프레임 레이트, 기본값: 2), `--blur_threshold` (블러 감지 임계값) |
| **소요 시간** | 약 30초 ~ 1분 (1분 영상 기준) |
| **의존성** | OpenCV (`opencv-python`) |

**실행 예시:**

```bash
python scripts/extract_frames.py \
    --video data/raw/car_video.mp4 \
    --output data/frames/car_01 \
    --fps 2 \
    --blur_threshold 100
```

**참고 사항:**
- FPS가 너무 높으면 유사한 프레임이 많아져 COLMAP이 느려질 수 있습니다.
- FPS가 너무 낮으면 시점 커버리지가 부족하여 재구성 품질이 떨어집니다.
- 권장 프레임 수: **100~300장**

---

### Step 2: COLMAP SfM (Structure-from-Motion)

추출된 이미지들로부터 카메라의 위치(포즈)와 내부 파라미터(intrinsics)를 추정하고,
희소 3D 포인트 클라우드를 생성하는 단계입니다.

```
┌──────────────────────────────────────────────────────────────┐
│  Step 2: COLMAP SfM                                          │
│                                                              │
│  입력: data/frames/car_01/*.jpg                               │
│    │                                                         │
│    ▼                                                         │
│  Feature Extraction (SIFT 특징점 추출)                         │
│    │                                                         │
│    ▼                                                         │
│  Feature Matching (특징점 매칭)                                │
│    │         ├── Exhaustive Matching (소규모)                  │
│    │         └── Sequential Matching (대규모/영상)              │
│    ▼                                                         │
│  Incremental Mapper (증분적 SfM 재구성)                        │
│    │                                                         │
│    ▼                                                         │
│  Bundle Adjustment (최적화)                                   │
│    │                                                         │
│    ▼                                                         │
│  Image Undistortion (왜곡 보정 + 이미지 정렬)                   │
│    │                                                         │
│    ▼                                                         │
│  출력: data/colmap_output/car_01/                             │
│        ├── sparse/           (카메라 포즈, 3D 포인트)          │
│        ├── images/           (왜곡 보정된 이미지)              │
│        └── database.db       (COLMAP 데이터베이스)             │
└──────────────────────────────────────────────────────────────┘
```

| 항목 | 내용 |
|------|------|
| **스크립트** | `scripts/run_colmap.py` |
| **입력** | 프레임 이미지 디렉토리 (`data/frames/<scene_name>/`) |
| **출력** | COLMAP 결과물 → `data/colmap_output/<scene_name>/` |
| **주요 파라미터** | `--matching_type` (`exhaustive` / `sequential`), `--camera_model` (`OPENCV` / `PINHOLE`) |
| **소요 시간** | 약 5~15분 (이미지 200장, A100 GPU 기준) |
| **의존성** | COLMAP (시스템 설치 필요) |

**실행 예시:**

```bash
python scripts/run_colmap.py \
    --images data/frames/car_01 \
    --output data/colmap_output/car_01 \
    --matching_type exhaustive \
    --camera_model OPENCV
```

**COLMAP 출력 디렉토리 구조:**

```
data/colmap_output/car_01/
├── sparse/
│   └── 0/
│       ├── cameras.bin      # 카메라 내부 파라미터 (intrinsics)
│       ├── images.bin       # 카메라 외부 파라미터 (extrinsics, 포즈)
│       └── points3D.bin     # 희소 3D 포인트 클라우드
├── images/                  # 왜곡 보정된 이미지
└── database.db              # 특징점 및 매칭 데이터베이스
```

**주의 사항:**
- 이미지 수가 50장 미만이면 매칭 실패 확률이 높아집니다.
- `exhaustive` 매칭은 정확하지만 이미지 수가 많으면 매우 느립니다 (O(n^2)).
- 영상에서 추출한 프레임은 `sequential` 매칭이 효율적입니다.

---

### Step 3: Gaussian Splatting 학습

COLMAP 결과를 입력으로 받아 3D Gaussian Splatting 모델을 학습하는 핵심 단계입니다.

```
┌──────────────────────────────────────────────────────────────┐
│  Step 3: Gaussian Splatting 학습                              │
│                                                              │
│  입력: data/colmap_output/car_01/ (sparse + images)           │
│    │                                                         │
│    ▼                                                         │
│  초기화: COLMAP 희소 포인트 → 초기 3D Gaussian 생성             │
│    │                                                         │
│    ▼                                                         │
│  반복 학습 (30,000 iterations):                               │
│    │                                                         │
│    │  ┌─── 랜덤 시점 선택 ──────────────────────────┐         │
│    │  │                                             │         │
│    │  │  Differentiable Rasterization               │         │
│    │  │  (미분 가능한 래스터화)                        │         │
│    │  │       │                                     │         │
│    │  │       ▼                                     │         │
│    │  │  렌더링 이미지 생성                           │         │
│    │  │       │                                     │         │
│    │  │       ▼                                     │         │
│    │  │  L1 Loss + SSIM Loss 계산                    │         │
│    │  │  (GT 이미지와 비교)                           │         │
│    │  │       │                                     │         │
│    │  │       ▼                                     │         │
│    │  │  역전파 → Gaussian 파라미터 업데이트           │         │
│    │  │  (위치, 색상, 불투명도, 공분산)                │         │
│    │  └─────────────────────────────────────────────┘         │
│    │                                                         │
│    │  Adaptive Density Control:                               │
│    │  ├── Densification (밀도 증가): 그래디언트가 큰 영역       │
│    │  └── Pruning (가지치기): 불투명도가 낮은 Gaussian 제거     │
│    │                                                         │
│    ▼                                                         │
│  출력: data/gaussian_output/car_01/                           │
│        ├── point_cloud/iteration_30000/point_cloud.ply        │
│        ├── cameras.json                                      │
│        └── cfg_args                                          │
└──────────────────────────────────────────────────────────────┘
```

| 항목 | 내용 |
|------|------|
| **스크립트** | `scripts/train_gaussian.py` |
| **입력** | COLMAP 결과 디렉토리 (`data/colmap_output/<scene_name>/`) |
| **출력** | 학습된 모델 → `data/gaussian_output/<scene_name>/` |
| **주요 파라미터** | `--iterations` (학습 반복 횟수, 기본값: 30000), `--sh_degree` (Spherical Harmonics 차수) |
| **소요 시간** | 약 20~40분 (이미지 200장, 30K iterations, A100 기준) |
| **GPU 메모리** | 약 8~16 GB (이미지 해상도 및 Gaussian 수에 따라 변동) |
| **의존성** | `third_party/gaussian-splatting/`, PyTorch, CUDA |

**실행 예시:**

```bash
python scripts/train_gaussian.py \
    --source data/colmap_output/car_01 \
    --output data/gaussian_output/car_01 \
    --iterations 30000 \
    --sh_degree 3
```

**학습 중 확인 가능한 메트릭:**

| 메트릭 | 설명 | 목표값 |
|--------|------|--------|
| PSNR | Peak Signal-to-Noise Ratio | > 25 dB (양호), > 30 dB (우수) |
| SSIM | Structural Similarity Index | > 0.85 |
| L1 Loss | 픽셀 단위 절대 오차 | 지속적으로 감소 |
| Gaussian 수 | 현재 Gaussian 포인트 총 수 | 50만~200만 |

---

### Step 4: 모델 내보내기 (Export)

학습된 Gaussian Splatting 모델을 사용 목적에 맞는 형식으로 내보내는 단계입니다.

```
┌──────────────────────────────────────────────────────────────┐
│  Step 4: 모델 내보내기                                        │
│                                                              │
│  입력: data/gaussian_output/car_01/                           │
│    │                                                         │
│    ├──> PLY 형식 (.ply)         범용 3D 포인트 클라우드 형식     │
│    │                                                         │
│    ├──> Splat 형식 (.splat)     웹 뷰어 최적화 형식             │
│    │                                                         │
│    └──> 기타 형식                커스텀 내보내기                 │
│                                                              │
│  출력: 최종 3D 모델 파일                                       │
└──────────────────────────────────────────────────────────────┘
```

| 항목 | 내용 |
|------|------|
| **스크립트** | `scripts/export_model.py` |
| **입력** | 학습된 모델 디렉토리 (`data/gaussian_output/<scene_name>/`) |
| **출력** | `.ply`, `.splat` 등 내보내기 파일 |
| **주요 파라미터** | `--format` (`ply` / `splat`), `--iteration` (사용할 체크포인트 iteration) |
| **소요 시간** | 약 30초 ~ 1분 |

**실행 예시:**

```bash
python scripts/export_model.py \
    --model data/gaussian_output/car_01 \
    --format ply \
    --iteration 30000
```

---

### Step 5: 웹 뷰어 시각화

내보낸 3D 모델을 브라우저에서 인터랙티브하게 확인할 수 있습니다.

```
┌──────────────────────────────────────────────────────────────┐
│  Step 5: 웹 뷰어                                              │
│                                                              │
│  web_viewer/                                                 │
│  ├── index.html        HTML 레이아웃                          │
│  ├── main.js           Three.js 기반 3D 렌더링 로직            │
│  └── style.css         스타일시트                              │
│                                                              │
│  사용법:                                                      │
│  $ cd web_viewer                                             │
│  $ python -m http.server 8080                                │
│  → 브라우저에서 http://localhost:8080 접속                     │
└──────────────────────────────────────────────────────────────┘
```

| 항목 | 내용 |
|------|------|
| **위치** | `web_viewer/` |
| **입력** | 내보낸 `.ply` 또는 `.splat` 파일 |
| **조작** | 마우스 드래그 (회전), 스크롤 (줌), 우클릭 드래그 (이동) |

---

## 전체 파이프라인 통합 실행

모든 단계를 한 번에 실행하려면 `run_pipeline.py`를 사용합니다.

```bash
python scripts/run_pipeline.py \
    --input data/raw/car_video.mp4 \
    --output data/gaussian_output/car_01 \
    --fps 2 \
    --iterations 30000
```

이 스크립트는 위의 Step 1~4를 순차적으로 실행하며, 각 단계의 중간 결과물을
적절한 디렉토리에 자동으로 저장합니다.

---

## 소요 시간 총정리 (A100 GPU 기준)

아래 표는 이미지 약 200장, 해상도 1920x1080 기준의 예상 소요 시간입니다.

| 단계 | 스크립트 | 최소 시간 | 일반 시간 | 최대 시간 |
|------|----------|----------|----------|----------|
| 프레임 추출 | `extract_frames.py` | 10초 | 30초 | 2분 |
| COLMAP SfM | `run_colmap.py` | 3분 | 10분 | 30분 |
| Gaussian Splatting 학습 | `train_gaussian.py` | 15분 | 30분 | 60분 |
| 모델 내보내기 | `export_model.py` | 10초 | 30초 | 2분 |
| **총 소요 시간** | - | **~20분** | **~40분** | **~90분** |

> **참고:** 이미지 수, 해상도, iteration 횟수, GPU 종류에 따라 시간이 크게 달라질 수 있습니다.

| GPU 모델 | 상대 속도 (대략) |
|----------|----------------|
| NVIDIA A100 (80GB) | 1.0x (기준) |
| NVIDIA A100 (40GB) | 1.0x |
| NVIDIA RTX 4090 | 0.8~1.0x |
| NVIDIA RTX 3090 | 0.6~0.8x |
| NVIDIA RTX 3080 | 0.4~0.6x |

---

## 트러블슈팅 가이드

### 1. 프레임 추출 관련

#### 오류: `cv2.error: ... could not open video`

**원인:** OpenCV가 해당 영상 코덱을 지원하지 않거나 파일 경로가 잘못됨

**해결 방법:**
```bash
# 영상 파일 정보 확인
ffprobe data/raw/car_video.mp4

# FFmpeg로 호환 형식으로 변환
ffmpeg -i data/raw/car_video.mov -c:v libx264 data/raw/car_video.mp4

# OpenCV 코덱 지원 확인
python -c "import cv2; print(cv2.getBuildInformation())"
```

#### 추출된 프레임이 너무 적거나 많음

**해결 방법:** `--fps` 값을 조정합니다.
- 프레임이 너무 많음 → FPS를 낮춤 (예: `--fps 1`)
- 프레임이 너무 적음 → FPS를 높임 (예: `--fps 5`)
- 권장 최종 프레임 수: 100~300장

---

### 2. COLMAP 관련

#### 오류: `COLMAP failed: No images registered`

**원인:** COLMAP이 이미지 간 특징점 매칭에 실패하여 어떤 이미지도 등록하지 못함

**해결 방법:**
```bash
# 1. 이미지 수 확인 (최소 50장 이상 권장)
ls data/frames/car_01/ | wc -l

# 2. 이미지 해상도 확인 (너무 작으면 특징점이 부족)
identify data/frames/car_01/frame_00001.jpg

# 3. 매칭 타입을 exhaustive로 변경
python scripts/run_colmap.py \
    --images data/frames/car_01 \
    --output data/colmap_output/car_01 \
    --matching_type exhaustive
```

#### 오류: `No good initial pair found`

**원인:** 초기 이미지 쌍을 찾지 못함. 이미지 간 겹치는 영역이 부족하거나 텍스처가 부족

**해결 방법:**
- 촬영 시 인접 이미지 간 60~80% 이상 겹치도록 촬영
- 단색 배경이 많은 경우 배경에 패턴을 추가하거나 다른 장소에서 촬영
- `--min_num_matches` 값을 낮추어 재시도

#### 등록된 이미지 수가 전체의 절반 미만

**원인:** 일부 시점에서의 이미지가 매칭에 실패함

**해결 방법:**
- 해당 시점 영역의 사진을 추가로 촬영
- 블러가 심한 이미지를 수동으로 제거
- 노출이 크게 다른 이미지를 제거

---

### 3. Gaussian Splatting 학습 관련

#### 오류: `CUDA out of memory`

**원인:** GPU 메모리 부족

**해결 방법:**
```bash
# 1. 현재 GPU 메모리 사용량 확인
nvidia-smi

# 2. 이미지 해상도 줄이기 (가장 효과적)
# run_colmap.py에서 --resize 옵션 사용 또는 이미지 사전 리사이즈
mogrify -resize 50% data/colmap_output/car_01/images/*.jpg

# 3. 다른 GPU 프로세스 종료
# 4. Gaussian densification 관련 파라미터 조정
```

#### PSNR이 20 dB 미만으로 낮음

**원인:** 학습이 제대로 진행되지 않거나 데이터 품질 문제

**해결 방법:**
- COLMAP 결과 확인: 등록된 이미지 비율이 90% 이상인지 확인
- 학습 iteration 수를 늘림 (예: `--iterations 50000`)
- 이미지에 과도한 모션 블러, 노출 차이가 없는지 확인
- Spherical Harmonics 차수를 높임 (예: `--sh_degree 4`)

#### 학습이 NaN으로 발산

**원인:** 수치적 불안정성

**해결 방법:**
- learning rate를 낮춤
- COLMAP 결과에서 outlier 포인트가 많은지 확인
- `--densify_grad_threshold` 값을 조정

---

### 4. 모델 내보내기 관련

#### 오류: `FileNotFoundError: point_cloud.ply not found`

**원인:** 지정된 iteration의 체크포인트가 존재하지 않음

**해결 방법:**
```bash
# 사용 가능한 체크포인트 확인
ls data/gaussian_output/car_01/point_cloud/

# 존재하는 iteration으로 지정
python scripts/export_model.py \
    --model data/gaussian_output/car_01 \
    --iteration 7000  # 실제 존재하는 iteration 사용
```

---

### 5. 웹 뷰어 관련

#### 3D 모델이 로드되지 않음

**해결 방법:**
- 브라우저 콘솔(F12)에서 오류 메시지 확인
- CORS 문제일 수 있으므로 반드시 HTTP 서버를 통해 접근 (파일 직접 열기 불가)
- 모델 파일의 경로가 올바른지 확인

#### 렌더링이 너무 느림

**해결 방법:**
- Gaussian 포인트 수가 너무 많으면 export 시 다운샘플링 적용
- 브라우저의 하드웨어 가속(WebGL)이 활성화되어 있는지 확인
- Chrome 또는 Edge 브라우저 사용 권장

---

### 6. 일반적인 환경 문제

#### CUDA 버전 불일치

```bash
# PyTorch가 인식하는 CUDA 버전 확인
python -c "import torch; print(torch.version.cuda)"

# 시스템 CUDA 버전 확인
nvcc --version

# 불일치 시 PyTorch 재설치
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

#### conda 환경 관련

```bash
# 환경이 제대로 활성화되었는지 확인
conda activate carnerf
which python
python --version

# 패키지 재설치
pip install -r requirements.txt --force-reinstall
```

---

## 파이프라인 커스터마이징 팁

### 더 높은 품질을 원하는 경우

1. 이미지 수를 **300장 이상**으로 확보
2. 학습 iteration을 `50000` 이상으로 설정
3. `--sh_degree 4` 로 Spherical Harmonics 차수 증가
4. 이미지 해상도를 높게 유지 (리사이즈 하지 않음)

### 더 빠른 처리를 원하는 경우

1. 이미지 수를 **100장 이하**로 유지
2. 학습 iteration을 `15000`으로 설정
3. 이미지를 미리 리사이즈 (예: 960x540)
4. `sequential` 매칭 사용 (영상 기반 데이터인 경우)
