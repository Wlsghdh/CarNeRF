#!/usr/bin/env python3
"""
AI Hub 평가 메트릭으로 우리 YOLOv8l-seg 측정

AI Hub mIoU = (background IoU + target IoU) / 2
  - background: 해당 클래스가 아닌 모든 픽셀
  - target: 해당 클래스 픽셀
  - 4개 클래스 각각 binary로 측정 후 평균

비교 기준:
  - AI Hub 보고 (Crushed label 2): mIoU 0.5988
    └ background IoU 0.9431, target IoU 0.2545
  - AI Hub 평균 보고: mIoU 0.6555
"""

import argparse
import os
from pathlib import Path

import cv2
import numpy as np
import torch
from ultralytics import YOLO


CLASS_NAMES = ["scratch", "dent", "breakage", "separation"]
NUM_CLASSES = 4


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--weights", default="./runs/segment/outputs/yolov8l_seg_60k/weights/best.pt")
    p.add_argument("--val-images", default="./datasets/yolo_seg/images/val")
    p.add_argument("--val-labels", default="./datasets/yolo_seg/labels/val")
    p.add_argument("--device", default="cuda:2")
    p.add_argument("--imgsz", type=int, default=1280)
    p.add_argument("--conf", type=float, default=0.25)
    p.add_argument("--iou", type=float, default=0.5)
    p.add_argument("--max-images", type=int, default=2000)
    return p.parse_args()


def load_gt_semantic_mask(label_path, h, w):
    """Polygon 라벨 → semantic mask (HxW with class indices 1-4, 0=bg)"""
    mask = np.zeros((h, w), dtype=np.uint8)
    if not os.path.exists(label_path):
        return mask
    with open(label_path) as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) < 7:
                continue
            cls_id = int(parts[0])  # 0-3
            coords = list(map(float, parts[1:]))
            xs = np.array(coords[0::2]) * w
            ys = np.array(coords[1::2]) * h
            pts = np.stack([xs, ys], axis=1).astype(np.int32)
            cv2.fillPoly(mask, [pts], cls_id + 1)  # 1-4 (0=bg)
    return mask


def build_pred_semantic_mask(yolo_result, h, w):
    """YOLO instance 결과 → semantic mask (HxW)"""
    mask = np.zeros((h, w), dtype=np.uint8)
    if yolo_result.boxes is None or len(yolo_result.boxes) == 0:
        return mask
    if yolo_result.masks is None:
        return mask

    masks_data = yolo_result.masks.data.cpu().numpy()  # (N, H_pred, W_pred)
    classes = yolo_result.boxes.cls.cpu().numpy().astype(int)
    confs = yolo_result.boxes.conf.cpu().numpy()

    # confidence 낮은 순으로 정렬해서 높은 conf가 마지막에 덮어쓰게
    order = np.argsort(confs)
    for i in order:
        m = cv2.resize(masks_data[i], (w, h), interpolation=cv2.INTER_NEAREST)
        m_bool = m > 0.5
        cls_id = classes[i] + 1  # 1-4
        mask[m_bool] = cls_id
    return mask


def compute_binary_iou(gt_binary, pred_binary):
    """단일 binary mask IoU"""
    inter = np.logical_and(gt_binary, pred_binary).sum()
    union = np.logical_or(gt_binary, pred_binary).sum()
    if union == 0:
        return None
    return inter / union


def compute_aihub_metric(gt_semantic, pred_semantic, num_classes=4):
    """AI Hub 방식: 클래스별로 binary 분해 후 (bg + target) / 2"""
    results = {}
    for cls_id in range(1, num_classes + 1):
        gt_target = (gt_semantic == cls_id)
        pred_target = (pred_semantic == cls_id)

        gt_bg = ~gt_target
        pred_bg = ~pred_target

        target_iou = compute_binary_iou(gt_target, pred_target)
        bg_iou = compute_binary_iou(gt_bg, pred_bg)

        results[cls_id] = {
            "target_iou": target_iou,
            "bg_iou": bg_iou,
            "mIoU_aihub": ((target_iou or 0) + (bg_iou or 0)) / 2 if (target_iou is not None and bg_iou is not None) else None,
        }
    return results


def main():
    args = parse_args()

    print(f"Loading YOLO from {args.weights}")
    model = YOLO(args.weights)

    img_dir = Path(args.val_images)
    label_dir = Path(args.val_labels)
    img_files = sorted([p for p in img_dir.iterdir()
                        if p.suffix.lower() in (".jpg", ".jpeg", ".png")])
    if args.max_images > 0:
        img_files = img_files[:args.max_images]
    print(f"Evaluating {len(img_files):,} images")

    # 클래스별 누적
    per_class_stats = {
        c: {"target_ious": [], "bg_ious": []}
        for c in range(1, NUM_CLASSES + 1)
    }

    for idx, img_file in enumerate(img_files):
        if (idx + 1) % 200 == 0:
            print(f"  ...{idx+1:,}/{len(img_files):,}")

        img = cv2.imread(str(img_file))
        if img is None:
            continue
        h, w = img.shape[:2]

        # GT semantic mask
        gt_semantic = load_gt_semantic_mask(
            label_dir / (img_file.stem + ".txt"), h, w
        )

        # YOLO predict
        result = model.predict(
            img, imgsz=args.imgsz, conf=args.conf,
            iou=args.iou, device=args.device, verbose=False
        )[0]

        pred_semantic = build_pred_semantic_mask(result, h, w)

        # Per-class metric
        per_class = compute_aihub_metric(gt_semantic, pred_semantic, NUM_CLASSES)
        for c, m in per_class.items():
            if m["target_iou"] is not None:
                per_class_stats[c]["target_ious"].append(m["target_iou"])
            if m["bg_iou"] is not None:
                per_class_stats[c]["bg_ious"].append(m["bg_iou"])

    # ── 집계 ──
    print("\n" + "=" * 70)
    print("AI HUB METRIC EVALUATION (우리 YOLOv8l-seg)")
    print("=" * 70)
    print(f"\n{'Class':<14s} {'target_IoU':>12s} {'background_IoU':>16s} {'mIoU(AIHub)':>14s}")
    print("-" * 60)

    total_miou = []
    total_target = []
    total_bg = []

    for c in range(1, NUM_CLASSES + 1):
        target_ious = per_class_stats[c]["target_ious"]
        bg_ious = per_class_stats[c]["bg_ious"]
        if len(target_ious) == 0:
            continue
        mean_target = np.mean(target_ious)
        mean_bg = np.mean(bg_ious)
        miou_aihub = (mean_target + mean_bg) / 2

        total_miou.append(miou_aihub)
        total_target.append(mean_target)
        total_bg.append(mean_bg)

        print(f"{CLASS_NAMES[c-1]:<14s} {mean_target:>12.4f} {mean_bg:>16.4f} {miou_aihub:>14.4f}")

    print("-" * 60)
    print(f"{'MEAN':<14s} {np.mean(total_target):>12.4f} {np.mean(total_bg):>16.4f} {np.mean(total_miou):>14.4f}")

    print("\n[비교]")
    print(f"  AI Hub 보고 (Crushed label2): target_IoU 0.2545, bg_IoU 0.9431, mIoU 0.5988")
    print(f"  AI Hub 보고 (평균):                                            mIoU 0.6555")
    print(f"  **우리 YOLOv8l-seg (이 측정)**: target_IoU {np.mean(total_target):.4f}, "
          f"bg_IoU {np.mean(total_bg):.4f}, mIoU {np.mean(total_miou):.4f}")


if __name__ == "__main__":
    main()
