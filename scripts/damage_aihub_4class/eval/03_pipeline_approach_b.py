#!/usr/bin/env python3
"""
Approach B: 4-binary YOLO ensemble (AI Hub 방식)

각 클래스의 binary YOLO 4개를 동시에 추론 → 각 detection의 conf 비교 → argmax로 최종 결정

각 모델은 자기 클래스 binary detection만 수행:
  - Model_scratch: scratch detection만
  - Model_dent: dent detection만
  - Model_breakage: breakage detection만
  - Model_separation: separation detection만

Ensemble:
  - 각 이미지에 4 모델 forward (4× inference time)
  - bbox 합쳐서 NMS (또는 그대로 두기)
  - 같은 영역에 여러 모델이 예측하면 conf 가장 높은 것 채택

평가: Box mAP + AI Hub mIoU
"""

import argparse
import json
import os
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
import torch
from ultralytics import YOLO


YOLO_CLASSES = ["scratch", "dent", "breakage", "separation"]


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--weights-scratch", required=True)
    p.add_argument("--weights-dent", required=True)
    p.add_argument("--weights-breakage", required=True)
    p.add_argument("--weights-separation", required=True)
    p.add_argument("--val-images", default="./datasets/yolo_seg/images/val")
    p.add_argument("--val-labels", default="./datasets/yolo_seg/labels/val")
    p.add_argument("--output-dir", default="./outputs/eval_approach_b")
    p.add_argument("--device", default="cuda:2")
    p.add_argument("--imgsz", type=int, default=1280)
    p.add_argument("--conf", type=float, default=0.20)
    p.add_argument("--iou-nms", type=float, default=0.5)
    p.add_argument("--match-iou", type=float, default=0.5)
    p.add_argument("--ensemble-iou", type=float, default=0.5,
                   help="다른 모델 간 detection IoU 이상이면 같은 객체로 판정")
    p.add_argument("--max-images", type=int, default=2000)
    return p.parse_args()


def load_gt(label_path, w, h):
    items = []
    semantic = np.zeros((h, w), dtype=np.uint8)
    if not os.path.exists(label_path):
        return items, semantic
    with open(label_path) as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) < 7:
                continue
            cls_id = int(parts[0])
            coords = list(map(float, parts[1:]))
            xs = np.array(coords[0::2]) * w
            ys = np.array(coords[1::2]) * h
            x1, y1, x2, y2 = xs.min(), ys.min(), xs.max(), ys.max()
            pts = np.stack([xs, ys], axis=1).astype(np.int32)
            cv2.fillPoly(semantic, [pts], cls_id + 1)
            items.append({"class_id": cls_id, "bbox": [x1, y1, x2, y2]})
    return items, semantic


def bbox_iou(b1, b2):
    x1 = max(b1[0], b2[0]); y1 = max(b1[1], b2[1])
    x2 = min(b1[2], b2[2]); y2 = min(b1[3], b2[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    a1 = (b1[2] - b1[0]) * (b1[3] - b1[1])
    a2 = (b2[2] - b2[0]) * (b2[3] - b2[1])
    u = a1 + a2 - inter
    return inter / u if u > 0 else 0


def compute_ap(preds, gt_count):
    preds = sorted(preds, key=lambda x: -x[0])
    tp_cum, fp_cum = 0, 0
    p_list, r_list = [], []
    for conf, is_tp in preds:
        if is_tp: tp_cum += 1
        else: fp_cum += 1
        p_list.append(tp_cum / (tp_cum + fp_cum))
        r_list.append(tp_cum / max(gt_count, 1))
    if not p_list: return 0.0
    ap = 0
    for t in np.arange(0, 1.1, 0.1):
        p_int = max([p for p, r in zip(p_list, r_list) if r >= t] or [0])
        ap += p_int / 11
    return ap


def cross_model_nms(detections, iou_thresh):
    """다른 모델 간 같은 영역 detection은 conf 높은 것만 남김"""
    if not detections:
        return []
    # confidence 내림차순
    detections = sorted(detections, key=lambda d: -d["conf"])
    kept = []
    for d in detections:
        skip = False
        for k in kept:
            if bbox_iou(d["bbox"], k["bbox"]) >= iou_thresh:
                skip = True
                break
        if not skip:
            kept.append(d)
    return kept


def main():
    args = parse_args()
    os.makedirs(args.output_dir, exist_ok=True)

    weights_map = {
        0: args.weights_scratch,
        1: args.weights_dent,
        2: args.weights_breakage,
        3: args.weights_separation,
    }

    print("Loading 4 binary YOLO models...")
    models = {}
    for c, w in weights_map.items():
        print(f"  {YOLO_CLASSES[c]}: {w}")
        models[c] = YOLO(w)

    img_dir = Path(args.val_images)
    label_dir = Path(args.val_labels)
    img_files = sorted([p for p in img_dir.iterdir()
                        if p.suffix.lower() in (".jpg", ".jpeg", ".png")])
    if args.max_images > 0:
        img_files = img_files[:args.max_images]
    print(f"\nEvaluating {len(img_files):,} images")

    box_preds = defaultdict(list)
    gt_counts = defaultdict(int)
    per_class_ious = {c: {"target": [], "bg": []} for c in range(4)}

    for idx, img_file in enumerate(img_files):
        if (idx + 1) % 100 == 0:
            print(f"  ...{idx+1:,}/{len(img_files):,}")
        img = cv2.imread(str(img_file))
        if img is None:
            continue
        h, w = img.shape[:2]

        gt_items, gt_semantic = load_gt(label_dir / (img_file.stem + ".txt"), w, h)
        for g in gt_items:
            gt_counts[g["class_id"]] += 1

        # 4 모델 ensemble inference
        all_detections = []
        pred_semantic = np.zeros((h, w), dtype=np.uint8)

        for c in range(4):
            res = models[c].predict(img, imgsz=args.imgsz, conf=args.conf,
                                     iou=args.iou_nms, device=args.device, verbose=False)[0]
            if res.boxes is None or len(res.boxes) == 0:
                continue
            boxes = res.boxes.xyxy.cpu().numpy()
            confs = res.boxes.conf.cpu().numpy()

            yolo_masks = None
            if res.masks is not None:
                mdata = res.masks.data.cpu().numpy()
                yolo_masks = [cv2.resize(m, (w, h), interpolation=cv2.INTER_NEAREST) > 0.5
                              for m in mdata]

            for bi in range(len(boxes)):
                all_detections.append({
                    "bbox": boxes[bi],
                    "conf": float(confs[bi]),
                    "class": c,
                    "mask": yolo_masks[bi] if yolo_masks else None,
                })

        # Cross-model NMS (다른 클래스 모델의 중첩 제거)
        final_dets = cross_model_nms(all_detections, args.ensemble_iou)

        # semantic mask 구성 (낮은 conf부터, 높은 conf가 덮어쓰게)
        for d in sorted(final_dets, key=lambda x: x["conf"]):
            if d["mask"] is not None:
                pred_semantic[d["mask"]] = d["class"] + 1

        # ── Box mAP 매칭 ──
        used_gt = set()
        for pred in sorted(final_dets, key=lambda d: -d["conf"]):
            best_iou, best_gi = 0, -1
            for gi, gt in enumerate(gt_items):
                if gi in used_gt or gt["class_id"] != pred["class"]:
                    continue
                iou = bbox_iou(pred["bbox"], gt["bbox"])
                if iou > best_iou:
                    best_iou, best_gi = iou, gi
            is_tp = 1 if (best_iou >= args.match_iou and best_gi >= 0) else 0
            if is_tp:
                used_gt.add(best_gi)
            box_preds[pred["class"]].append((pred["conf"], is_tp))

        # ── AI Hub mIoU ──
        for c in range(4):
            gt_t = (gt_semantic == c + 1)
            pred_t = (pred_semantic == c + 1)
            gt_bg = ~gt_t; pred_bg = ~pred_t

            i_t = np.logical_and(gt_t, pred_t).sum()
            u_t = np.logical_or(gt_t, pred_t).sum()
            i_b = np.logical_and(gt_bg, pred_bg).sum()
            u_b = np.logical_or(gt_bg, pred_bg).sum()

            if u_t > 0: per_class_ious[c]["target"].append(i_t / u_t)
            if u_b > 0: per_class_ious[c]["bg"].append(i_b / u_b)

    # ── 보고 ──
    print("\n" + "=" * 70)
    print("APPROACH B: 4-binary YOLO ensemble (AI Hub style)")
    print("=" * 70)

    print(f"\n[Box mAP50 — Approach B]")
    aps = {}
    for c in range(4):
        ap = compute_ap(box_preds[c], gt_counts[c])
        aps[c] = ap
        print(f"  {YOLO_CLASSES[c]:12s}: {ap:.4f}  (GT: {gt_counts[c]})")
    map50 = np.mean(list(aps.values()))
    print(f"  MEAN mAP50:    {map50:.4f}")

    print(f"\n[AI Hub mIoU — Approach B]")
    print(f"  {'Class':<14s} {'target_IoU':>12s} {'bg_IoU':>10s} {'mIoU(AIHub)':>14s}")
    print("-" * 56)
    miou_list, t_list, b_list = [], [], []
    for c in range(4):
        t = np.mean(per_class_ious[c]["target"]) if per_class_ious[c]["target"] else 0
        b = np.mean(per_class_ious[c]["bg"]) if per_class_ious[c]["bg"] else 0
        mi = (t + b) / 2
        miou_list.append(mi); t_list.append(t); b_list.append(b)
        print(f"  {YOLO_CLASSES[c]:<14s} {t:>12.4f} {b:>10.4f} {mi:>14.4f}")
    print("-" * 56)
    print(f"  {'MEAN':<14s} {np.mean(t_list):>12.4f} {np.mean(b_list):>10.4f} {np.mean(miou_list):>14.4f}")

    print(f"\n[Comparison]")
    print(f"  Current YOLOv8l-seg (multi-class): mAP 0.4499, mIoU(AIHub) 0.6347")
    print(f"  AI Hub baseline (4 binary UNets):              mIoU(AIHub) 0.6555")
    print(f"  Approach B (4 binary YOLOs ensemble): mAP {map50:.4f}, mIoU(AIHub) {np.mean(miou_list):.4f}")

    report = {
        "box_aps": {YOLO_CLASSES[c]: aps[c] for c in range(4)},
        "map50": float(map50),
        "aihub_mIoU_per_class": {YOLO_CLASSES[c]: float(miou_list[c]) for c in range(4)},
        "aihub_mIoU_mean": float(np.mean(miou_list)),
    }
    with open(os.path.join(args.output_dir, "report.json"), "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\nReport saved to {args.output_dir}/report.json")


if __name__ == "__main__":
    main()
