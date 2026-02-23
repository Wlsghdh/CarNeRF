# CarNeRF 다음 세션 가이드

## 최종 업데이트: 2026-02-15

---

## 1. 현재 상태 요약

### 배포된 3D 모델 (NF소나타, vehicle_id=19)
- **파일**: `backend/app/static/models/nf_sonata/model.splat` (86MB, 2.8M 가우시안)
- **뷰어**: http://localhost:8000/viewer/19
- **원본 3DGS**: PSNR 31.88, 4.4M 가우시안
- **현재 적용**: 공간 pruning (반경 5) + 가벼운 스케일 필터 → 2,805,937 가우시안
- **사용자 피드백**: "배경이 좀 방해하고 차가 좀 흐려졌어" → **반경 좁히기 + 선명도 개선 필요**

### 현재 HQ 설정
| 항목 | 값 |
|------|-----|
| 영상 | `backend/uploads/videos/NF소나타.mp4` (13MB, 1080x1920, 32.2초) |
| 프레임 수 | 200장 (`data/frames/nf_sonata_hq/`) |
| 해상도 | 원본 1080x1920 |
| COLMAP | sequential matching, 200/200 등록, 193,445 3D 포인트 |
| GS 학습 | 60K iterations (3DGS) |
| 하이퍼파라미터 | `densify_grad_threshold=0.0001`, `densify_until_iter=25000`, `lambda_dssim=0.4`, `opacity_reset_interval=2000` |
| 원본 가우시안 수 | 4,416,141 |
| 총 소요 시간 | 140.8분 (COLMAP 36.1분 + GS 104.3분 + Export 0.3분) |

---

## 2. 이번 세션에서 한 것 (2026-02-15)

### 2DGS (2D Gaussian Splatting) 시도 → 실패
- `third_party/2d-gaussian-splatting/` 설치 (CUDA extensions 컴파일 완료)
- 60K iterations 학습 → 396,707 surfels, 93MB PLY, 58분
- **결과**: 매우 흐리고 안개 낀 렌더링. 차 인식 불가 수준
- **원인**: 가우시안 수 부족 (3DGS의 1/10), lambda_dist=100 과도한 정규화
- **교훈**: 2DGS는 이 데이터셋에 그대로 적용 불가. 하이퍼파라미터 대폭 조정 필요하거나 포기

### 3DGS 모델 floater 제거 시도들
1. **과도한 scale+aspect 기반 pruning** (max_scale_factor=5, max_aspect_ratio=20)
   - 4.4M → 1.5M 가우시안, 46MB SPLAT
   - **결과**: floater 줄었으나 차도 흐려짐 → 차 표면 가우시안까지 제거됨

2. **공간 기반 pruning** (반경 5, 가벼운 스케일 필터만)
   - 4.4M → 2.8M 가우시안, 86MB SPLAT
   - **결과**: 배경 일부 제거, 디테일 보존 나아짐. 하지만 여전히 배경 방해 + 약간 흐림

### 가우시안 공간 분포 (참고)
```
중심 (median): X=-0.12, Y=0.64, Z=1.30
반경별 가우시안 수:
  반경 3: 2,323,624 (52.6%)
  반경 4: 2,673,260 (60.5%)  ← 추천 (차량 대부분 포함)
  반경 5: 3,252,437 (73.6%)  ← 현재 적용
  반경 6: 3,300,710 (74.7%)
```

---

## 3. 다음 세션에서 할 일 ★

### 즉시 해야 할 것: 반경 좁히기 + 차 선명도 개선

#### Step 1: 공간 pruning 반경 4로 좁히기
- 현재 반경 5 (2.8M) → **반경 4** (2.67M, 배경 더 많이 제거)
- 반경 3도 시도 가능 (2.32M, 차량 본체만 거의 남음)
- 바닥을 완전히 제거하면 사용자가 싫어하므로 약간의 바닥은 유지

#### Step 2: 선명도 개선 방안
아래 방법 중 효과적인 것 조합:

**A. 더 높은 iteration으로 재학습 (3DGS)**
```bash
# 100K iterations 학습 (현재 60K → 100K)
CUDA_HOME=/usr/local/cuda-12.2 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
python third_party/gaussian-splatting/train.py \
  -s data/colmap_output/nf_sonata_hq/dense \
  -m data/gaussian_output/nf_sonata_100k \
  --iterations 100000 \
  --densify_grad_threshold 0.00005 \
  --densify_until_iter 35000 \
  --lambda_dssim 0.4 \
  --opacity_reset_interval 2000 \
  --position_lr_max_steps 100000 \
  --test_iterations 99999 \
  --save_iterations 30000 60000 100000
```
- `densify_grad_threshold` 0.00005 (더 세밀한 densification → 가우시안 더 많이 생성)
- `densify_until_iter` 35000 (더 오래 densify)
- 100K iterations (완전 수렴)

**B. SH degree 확인/증가**
- 기본 `sh_degree=3`. 이미 최대값이므로 view-dependent 효과는 충분
- 차체 반사가 잘 나오는지 확인

**C. Antialiasing 활성화**
- 3DGS에서 `--antialiasing` 옵션 확인 (버전에 따라 지원)
- 화면 크기 변화에 따른 aliasing 줄임

**D. 영상 재촬영 (근본 해결)**
- 현재 32초 → **60초 이상**, 360도 천천히 회전
- 다양한 높이/각도 포함
- 400-500 프레임 추출 가능
- 더 많은 시점 = 더 완전한 3D 복원

#### Step 3: 공간 pruning 적용 후 Export
```python
# 공간 pruning 스크립트 (인라인 실행)
# center = (-0.12, 0.64, 1.30), radius = 4
# opacity >= 0.005 (매우 가벼운 필터만)
# scale <= 15x median (극단적 floater만)
# → model.splat로 저장
```

---

## 4. 지금까지 시도한 것들 (전체 이력)

| # | 설명 | 가우시안 | PSNR | 결과 |
|---|------|---------|------|------|
| 1 | 축소 해상도 + 7K | - | 26.77 | floater 심함 |
| 2 | 축소 해상도 + 30K | - | 31.62 | 형태 ok, floater 있음 |
| 3 | 검정 배경 rembg | - | 32.19 | 검정 가우시안 발생 |
| 4 | 흰배경 + 5단계 필터 | - | 33.10 | 약간 개선 |
| 5 | 과도한 후처리 | 76K | - | "퀄리티 훨씬 안좋아" |
| 6 | DBSCAN 클러스터링 | 207K | - | 바닥 없어짐, 이상해짐 |
| 7 | HD원본 + 30K | 1.47M | 30.54 | 디테일 향상 |
| 8 | HQ 200프레임 60K ★ | 4.4M→2M | 31.88 | 현재 기준 최고 |
| 9 | 2DGS 60K | 396K | 미측정 | 매우 흐림, 실패 |
| 10 | 3DGS scale pruning | 1.5M | - | 차도 흐려짐 |
| 11 | 3DGS 공간 pruning r=5 | 2.8M | - | 배경 줄었으나 아직 부족 |

---

## 5. 데이터 디렉토리 맵

```
data/
├── frames/
│   ├── nf_sonata/             # 80프레임, 576x1024 (축소)
│   ├── nf_sonata_hd/          # 80프레임, 1080x1920 (원본)
│   ├── nf_sonata_hq/          # 200프레임, 1080x1920 (현재 최고) ★
│   ├── nf_sonata_nobg/        # 80프레임, 검정 배경 제거
│   └── nf_sonata_whitebg/     # 80프레임, 흰색 배경 제거
├── colmap_output/
│   ├── nf_sonata/             # 80프레임 축소 해상도 COLMAP
│   │   ├── dense_nobg/        # 하이브리드: 기존 포즈 + 검정배경 이미지
│   │   └── dense_whitebg/     # 하이브리드: 기존 포즈 + 흰배경 이미지
│   ├── nf_sonata_hd/          # 80프레임 원본 해상도 COLMAP
│   └── nf_sonata_hq/          # 200프레임 원본 해상도 COLMAP ★
└── gaussian_output/
    ├── nf_sonata/             # 7K iter (축소)
    ├── nf_sonata_30k/         # 30K iter (축소)
    ├── nf_sonata_nobg/        # 배경 제거 버전
    ├── nf_sonata_whitebg/     # 흰배경 버전
    ├── nf_sonata_hd/          # 30K iter (원본 해상도)
    ├── nf_sonata_hq/          # 60K iter (현재 최고 3DGS) ★
    │   └── point_cloud/
    │       ├── iteration_7000/
    │       ├── iteration_30000/
    │       └── iteration_60000/  # 최종 모델
    └── nf_sonata_2dgs/        # 2DGS 60K (실패 - 흐림)
        └── point_cloud/
            ├── iteration_7000/
            ├── iteration_30000/
            └── iteration_60000/

third_party/
├── gaussian-splatting/         # 공식 3DGS
└── 2d-gaussian-splatting/      # 2DGS (설치됨, CUDA extensions 빌드 완료)

backend/app/static/models/nf_sonata/
├── model.splat                 # 현재 배포 (공간 pruning r=5, 2.8M, 86MB)
├── model.ply                   # 현재 배포 PLY
├── model_3dgs_backup.splat     # 원본 3DGS (pruning 전, 2M, 62MB)
└── model_3dgs_backup.ply       # 원본 3DGS PLY
```

---

## 6. 현재 배포된 파일

| 파일 | 경로 | 크기 |
|------|------|------|
| 3D 모델 (SPLAT) | `backend/app/static/models/nf_sonata/model.splat` | 86MB |
| 3D 모델 (PLY) | `backend/app/static/models/nf_sonata/model.ply` | 663MB |
| 3DGS 원본 백업 | `backend/app/static/models/nf_sonata/model_3dgs_backup.splat` | 62MB |
| 원본 영상 | `backend/uploads/videos/NF소나타.mp4` | 13MB |

DB에서 vehicle_id=19의 `model_3d_url`은 `/static/models/nf_sonata/model.splat`, `model_3d_status`는 `ready`.

---

## 7. 핵심 교훈 (반드시 기억)

1. **해상도를 줄이면 안 됨** - 576x1024 축소가 품질 저하의 근본 원인이었음
2. **배경 제거 후 학습은 위험** - COLMAP 특징점 감소 + 배경색 가우시안 발생
3. **후처리(pruning)는 최소화** - 과도한 필터링이 오히려 품질 파괴 (시도 5, 10에서 확인)
4. **프레임 수가 핵심** - 80 → 200으로 늘리니 3D 포인트 5배 증가
5. **sequential matching 사용** - exhaustive는 고해상도에서 segfault
6. **바닥/주변 맥락 유지** - 바닥 제거하면 떠있는 느낌, 사용자가 싫어함
7. **공간 기반 pruning이 가장 효과적** - scale/aspect pruning은 차 표면까지 손상시킴
8. **2DGS는 이 데이터셋에서 실패** - lambda_dist=100 과도, 가우시안 수 1/10 부족
9. **반경 4가 최적 후보** - 차량 대부분 포함(60.5%), 배경 대부분 제거

---

## 8. 다음 세션 우선순위

1. **공간 pruning 반경 4로 좁히기** → 배경 더 제거
2. **3DGS 100K iterations 재학습** → densify 더 세밀하게, 완전 수렴으로 선명도 향상
3. **재학습 모델에 공간 pruning 적용** → 반경 3-4, 배경 깔끔하게 제거
4. **더 긴 영상 재촬영 고려** (60초+, 다양한 각도) → 근본적 품질 개선
5. **SAM 기반 3D 마스크** (optional) → 차량 영역만 정밀하게 남기기
6. **AI 결함 탐지 개발** (3D 모델 품질 안정화 후)
