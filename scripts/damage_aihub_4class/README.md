# AI Hub 차량 파손 4-class Segmentation

AI Hub 공개 차량 파손 이미지 데이터셋(dataSetSn=581)을 활용한 **4-class instance segmentation + 분류 시스템**.

기존 `train_damage_detector.py` (VeHiDE 1-class binary)와는 **별도 라인**의 모델로, 더 세밀한 클래스 분류(scratch / dent / breakage / separation)와 polygon mask를 출력합니다.

---

## 주요 결과

### Detection 성능

| 모델 | Box mAP50 | AI Hub mIoU |
|------|-----------|-------------|
| **YOLOv8l-seg 60k (4-class) — Best** | **0.4499** | **0.6347** |
| AI Hub 공식 baseline (UNet 4-binary, 참고) | — | 0.6555 |
| 격차 | — | **-2.1%p (95.3% 재현)** |

> 단일 GPU 환경(A6000 48GB, 48h 제약)에서 AI Hub 공식 baseline 대비 **2%p 이내 격차로 동등 성능 재현** 달성.

### Classification 성능 (4-class)

| 모델 | Macro F1 | 비고 |
|------|----------|------|
| **Multi-backbone Concat — Best** | **0.8307** | ResNet50 + ConvNeXtV2-Base + Swin-Base |
| 참고: 동일 데이터셋 ViT baseline (논문) | 0.64 | **+19.5%p 개선** |

### 실험적 시도 (Approach A / B) — 결과 정리

| Approach | 설명 | Box mAP50 | AI Hub mIoU |
|----------|------|-----------|-------------|
| **Baseline (Best)** | 4-class YOLOv8l-seg 직접 학습 | **0.4499** | **0.6347** |
| Approach A | 1-class YOLO + 5-class Concat (normal FP filter, 논문 1 방식) | 0.2904 | 0.6042 |
| Approach B | 4-binary YOLO ensemble (AI Hub 방식 모방) | 0.2765 | 0.6034 |

> 2-stage refinement / 4-binary ensemble 방식 모두 직접 4-class detection 대비 성능 저하됨을 정량적으로 확인. **데이터셋 특성에 따라 simple > complex pipeline**이라는 인사이트 확보.

---

## AI Hub 평가 메트릭 (자체 구현)

AI Hub 공식 보고서의 mIoU 정의:

```
mIoU = (background_IoU + target_IoU) / 2     # per class
최종 = 4 클래스 평균
```

이 정의가 표준 IoU와 달라 직접 구현 (`eval/01_eval_aihub_metric.py`):

1. **GT polygon → semantic mask** (cv2.fillPoly)
2. **YOLO instance mask → semantic mask** (painter's algorithm: 낮은 conf부터 그려서 높은 conf가 덮어쓰게)
3. **클래스별 binary 분해 → fg/bg IoU 각각 계산**
4. **(fg_IoU + bg_IoU) / 2** 산출 후 클래스 평균

**인사이트**: 차량 이미지에서 손상 영역은 전체 픽셀의 5% 미만이라 background IoU가 항상 0.95+로 1에 수렴 → mIoU가 부풀려 보임. AI Hub baseline도 동일 부풀림을 받으므로 상대 비교는 공정.

---

## 디렉토리 구조

```
damage_aihub_4class/
├── README.md
├── data_prep/                              # 데이터 처리
│   ├── 01_aihub_zip_to_yolo.py        # AI Hub zip → YOLO format
│   ├── 02_build_yolo_1class.py        # 4-class → 1-class 변환 (file-level symlink fix 포함)
│   ├── 03_extract_normal_crops.py     # Hard negative mining (20k normal crops)
│   └── 04_build_concat_5class_dataset.py  # 5-class crop dataset (with normal)
│
├── train/                             # 학습
│   ├── 01_train_yolov8l_seg_4class.py    # ⭐ Best detection (4-class, mAP 0.4499)
│   ├── 02_train_concat_4class.py         # ⭐ Best classification (F1 0.8307)
│   ├── 03_train_yolo_1class.py           # 1-class detection (Approach A Stage 1)
│   ├── 04_train_concat_5class.py         # 5-class Concat (resume-capable)
│   └── 05_train_binary_yolo_per_class.py # 4-binary YOLO (Approach B)
│
├── eval/                              # 평가
│   ├── 01_eval_aihub_metric.py        # ⭐ AI Hub mIoU 직접 구현
│   ├── 02_pipeline_approach_a.py      # Approach A e2e
│   └── 03_pipeline_approach_b.py      # Approach B ensemble
│
└── results/                           # JSON 결과
    ├── approach_a_report.json
    └── approach_b_report.json
```

---

## 데이터셋 준비

AI Hub에서 직접 다운로드:
- 데이터셋: [차량 파손 이미지 (dataSetSn=581)](https://aihub.or.kr/)
- 다운로드 후 zip 압축 해제 → `data_prep/01_aihub_zip_to_yolo.py` 실행

```bash
# YOLO format으로 변환 (60k images, 4-class polygon)
python data_prep/01_aihub_zip_to_yolo.py \
  --src-root /path/to/aihub_extracted \
  --dst-root ./datasets/yolo_seg
```

---

## Best 모델 사용 방법

### 1. Detection (YOLOv8l-seg 4-class)

```bash
# 학습
python train/01_train_yolov8l_seg_4class.py \
  --data ./datasets/yolo_seg/data.yaml \
  --device 0 --epochs 80 --imgsz 1280 --batch 16

# 평가 (AI Hub mIoU)
python eval/01_eval_aihub_metric.py \
  --weights ./runs/segment/best.pt \
  --val-images ./datasets/yolo_seg/images/val \
  --val-labels ./datasets/yolo_seg/labels/val \
  --device cuda:0
```

### 2. Classification (Multi-backbone Concat)

```bash
# 4-class crop 학습 (best)
python train/02_train_concat_4class.py \
  --data-root ./datasets/cls_crops_4class \
  --device cuda:0
```

---

## 기술 스택

- **Framework**: PyTorch, Ultralytics YOLO
- **Backbones**: timm (ResNet50, ConvNeXtV2-Base, Swin-Base)
- **Vision**: OpenCV, PIL, NumPy
- **Optimization**: AMP, AdamW, Cosine Annealing, Class-weighted Loss, MixUp, Label Smoothing, RandAugment

---

## 시도했으나 채택 안 된 모델 (참고)

| 모델 | 결과 | 폐기 사유 |
|------|------|----------|
| YOLO11l-seg / YOLO26l-seg | NaN crash | AMP+attention 불안정 |
| Mask2Former Swin-L | mIoU 0.258 | YOLO 못 따라잡음 |
| Faster R-CNN | mAP 0.347 | YOLO 보다 낮음 |
| Mask R-CNN cascade | mIoU 악화 | YOLO보다 mask 품질 떨어짐 |
| U-Net (SOCAR-style) | mIoU 0.303 | YOLO 못 따라잡음 |
| YOLOv8l-seg img1536 fine-tune | mAP 0.40 | 원본 해상도 학습이 더 좋음 |

---

## 핵심 인사이트

1. **AI Hub 메트릭 정의 분석** — `(bg+target)/2` 정의가 background 영향으로 mIoU를 부풀림. 동일 정의로 baseline과 비교해야 공정.
2. **단순 > 복잡** — 데이터셋 특성에 따라 2-stage refinement보다 직접 4-class 학습이 더 강함 (negative result).
3. **Multi-backbone ensemble 효과** — 3개 backbone concat이 단일 ViT 대비 분류 F1 +19.5%p 향상.
4. **YOLOv8 안정성** — YOLO11/26 대비 AMP 환경에서 NaN 없이 안정적 수렴.
5. **Symlink 버그 (ultralytics)** — 폴더 단위 symlink는 라벨 경로 오인식 → **파일 단위 symlink**로 해결.

---

## Pre-trained Weights

레포 크기 제한으로 본 디렉토리에 포함되지 않음. 별도 요청 시 제공:
- `yolov8l_seg_60k_best.pt` (89MB) — Box mAP50 0.4499
- `concat_paper_v1_best.pt` (764MB) — Macro F1 0.8307
