#!/usr/bin/env python3
"""
Approach A end-to-end 파이프라인: 1-class YOLO + 5-class Concat

Stage 1: 1-class YOLOv8l-seg → bbox + 손상 영역 mask
Stage 2: 각 bbox crop → Concat 5-class
   ├ "normal"이면 → 제거 (FP)
   └ 나머지 4개 클래스 → 최종 라벨

평가:
  - Box mAP50 (4-class detection)
  - Mask mIoU (AI Hub 방식, target+bg 평균)
  - Per-class precision/recall
"""

import argparse
import json
import os
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image
import timm
from torchvision import transforms
from ultralytics import YOLO


YOLO_CLASSES = ["scratch", "dent", "breakage", "separation"]
# Concat 5-class ImageFolder 알파벳 순
CONCAT_CLASSES = ["breakage", "dent", "normal", "scratch", "separation"]
NORMAL_IDX = CONCAT_CLASSES.index("normal")  # 2

# concat_idx → YOLO_CLASSES idx 매핑 (normal은 -1)
CONCAT_TO_YOLO = {
    0: 2,    # breakage
    1: 1,    # dent
    2: -1,   # normal (제거)
    3: 0,    # scratch
    4: 3,    # separation
}


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--yolo-weights", required=True, help="1-class YOLO best.pt")
    p.add_argument("--concat-weights", required=True, help="5-class Concat best.pt")
    p.add_argument("--val-images", default="./datasets/yolo_seg/images/val")
    p.add_argument("--val-labels", default="./datasets/yolo_seg/labels/val")
    p.add_argument("--output-dir", default="./outputs/eval_approach_a")
    p.add_argument("--device", default="cuda:2")
    p.add_argument("--imgsz", type=int, default=1280)
    p.add_argument("--yolo-conf", type=float, default=0.15,
                   help="1-class라 conf 더 낮춰 recall 극대화")
    p.add_argument("--yolo-iou", type=float, default=0.5)
    p.add_argument("--match-iou", type=float, default=0.5)
    p.add_argument("--bbox-expand", type=float, default=1.3)
    p.add_argument("--crop-size", type=int, default=224)
    p.add_argument("--normal-conf-thresh", type=float, default=0.5,
                   help="normal로 분류된 후보 제거 임계값")
    p.add_argument("--max-images", type=int, default=2000)
    return p.parse_args()


class ConcatModel(nn.Module):
    def __init__(self, num_classes=5, dropout=0.3):
        super().__init__()
        self.resnet = timm.create_model("resnet50", pretrained=False,
                                         num_classes=0, global_pool="avg")
        self.convnext = timm.create_model("convnextv2_base", pretrained=False,
                                           num_classes=0, global_pool="avg")
        self.swin = timm.create_model("swin_base_patch4_window7_224",
                                       pretrained=False, num_classes=0,
                                       global_pool="avg")
        total = self.resnet.num_features + self.convnext.num_features + self.swin.num_features
        self.mlp = nn.Sequential(
            nn.Linear(total, 512), nn.BatchNorm1d(512), nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Linear(512, 128), nn.BatchNorm1d(128), nn.ReLU(inplace=True),
            nn.Dropout(dropout * 0.7),
            nn.Linear(128, num_classes),
        )

    def forward(self, x):
        f = torch.cat([self.resnet(x), self.convnext(x), self.swin(x)], dim=1)
        return self.mlp(f)


def crop_with_expand(img, bbox, expand, target):
    h, w = img.shape[:2]
    x1, y1, x2, y2 = bbox
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    side = max((x2 - x1) * expand, (y2 - y1) * expand, target * 0.5)
    nx1 = max(0, int(cx - side / 2))
    ny1 = max(0, int(cy - side / 2))
    nx2 = min(w, int(cx + side / 2))
    ny2 = min(h, int(cy + side / 2))
    crop = img[ny1:ny2, nx1:nx2]
    if crop.size == 0:
        return None
    return cv2.resize(crop, (target, target))


def load_gt(label_path, w, h):
    """GT polygon → list of (class_id, bbox, semantic_mask)"""
    items = []
    semantic_mask = np.zeros((h, w), dtype=np.uint8)
    if not os.path.exists(label_path):
        return items, semantic_mask
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
            cv2.fillPoly(semantic_mask, [pts], cls_id + 1)  # 1-4
            items.append({"class_id": cls_id, "bbox": [x1, y1, x2, y2]})
    return items, semantic_mask


def bbox_iou(b1, b2):
    x1 = max(b1[0], b2[0]); y1 = max(b1[1], b2[1])
    x2 = min(b1[2], b2[2]); y2 = min(b1[3], b2[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    a1 = (b1[2] - b1[0]) * (b1[3] - b1[1])
    a2 = (b2[2] - b2[0]) * (b2[3] - b2[1])
    u = a1 + a2 - inter
    return inter / u if u > 0 else 0


def compute_ap(preds, gt_count):
    """11-point interp AP"""
    preds = sorted(preds, key=lambda x: -x[0])
    tp_cum, fp_cum = 0, 0
    p_list, r_list = [], []
    for conf, is_tp in preds:
        if is_tp:
            tp_cum += 1
        else:
            fp_cum += 1
        p_list.append(tp_cum / (tp_cum + fp_cum))
        r_list.append(tp_cum / max(gt_count, 1))
    if not p_list:
        return 0.0
    ap = 0
    for t in np.arange(0, 1.1, 0.1):
        p_int = max([p for p, r in zip(p_list, r_list) if r >= t] or [0])
        ap += p_int / 11
    return ap


def main():
    args = parse_args()
    os.makedirs(args.output_dir, exist_ok=True)
    device = torch.device(args.device)

    print(f"Loading 1-class YOLO from {args.yolo_weights}")
    yolo = YOLO(args.yolo_weights)

    print(f"Loading 5-class Concat from {args.concat_weights}")
    concat = ConcatModel(num_classes=5).to(device)
    concat.load_state_dict(torch.load(args.concat_weights, map_location=device))
    concat.eval()

    concat_tf = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])

    img_dir = Path(args.val_images)
    label_dir = Path(args.val_labels)
    img_files = sorted([p for p in img_dir.iterdir()
                        if p.suffix.lower() in (".jpg", ".jpeg", ".png")])
    if args.max_images > 0:
        img_files = img_files[:args.max_images]
    print(f"Evaluating {len(img_files):,} images")

    # ── Detection mAP 누적 ──
    box_preds = defaultdict(list)  # cls -> [(conf, is_tp)]
    gt_counts = defaultdict(int)

    # ── AI Hub mIoU 누적 ──
    per_class_ious = {c: {"target": [], "bg": []} for c in range(4)}

    # ── Normal 필터 통계 ──
    n_yolo_detect = 0
    n_normal_filtered = 0
    n_kept = 0

    for idx, img_file in enumerate(img_files):
        if (idx + 1) % 200 == 0:
            print(f"  ...{idx+1:,}/{len(img_files):,}")
        img = cv2.imread(str(img_file))
        if img is None:
            continue
        h, w = img.shape[:2]

        gt_items, gt_semantic = load_gt(label_dir / (img_file.stem + ".txt"), w, h)
        for g in gt_items:
            gt_counts[g["class_id"]] += 1

        # Stage 1: 1-class YOLO
        res = yolo.predict(img, imgsz=args.imgsz, conf=args.yolo_conf,
                           iou=args.yolo_iou, device=args.device, verbose=False)[0]
        if res.boxes is None or len(res.boxes) == 0:
            continue
        boxes = res.boxes.xyxy.cpu().numpy()
        confs_yolo = res.boxes.conf.cpu().numpy()
        n_yolo_detect += len(boxes)

        # YOLO instance masks (1-class)
        yolo_masks = None
        if res.masks is not None:
            mdata = res.masks.data.cpu().numpy()
            yolo_masks = [cv2.resize(m, (w, h), interpolation=cv2.INTER_NEAREST) > 0.5
                          for m in mdata]

        # Stage 2: Concat 5-class
        crops, valid_idx = [], []
        for bi, box in enumerate(boxes):
            crop = crop_with_expand(img, box, args.bbox_expand, args.crop_size)
            if crop is None:
                continue
            crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
            crops.append(concat_tf(Image.fromarray(crop_rgb)))
            valid_idx.append(bi)

        if not crops:
            continue

        batch = torch.stack(crops).to(device)
        with torch.no_grad():
            with torch.amp.autocast("cuda"):
                logits = concat(batch)
                probs = F.softmax(logits, dim=1).cpu().numpy()

        # 최종 예측 (per detection)
        final_preds = []  # (bbox, yolo_class, conf, mask)
        pred_semantic = np.zeros((h, w), dtype=np.uint8)
        for j, bi in enumerate(valid_idx):
            top_idx = int(np.argmax(probs[j]))
            top_conf = float(probs[j][top_idx])

            # Normal로 분류 + 신뢰도 충분히 높으면 제거
            if top_idx == NORMAL_IDX and top_conf >= args.normal_conf_thresh:
                n_normal_filtered += 1
                continue

            # Normal 제외 best class
            non_normal_probs = probs[j].copy()
            non_normal_probs[NORMAL_IDX] = -1
            final_concat_idx = int(np.argmax(non_normal_probs))
            yolo_cls = CONCAT_TO_YOLO[final_concat_idx]
            if yolo_cls < 0:
                continue

            # YOLO conf와 Concat conf 가중 평균
            final_conf = 0.5 * float(confs_yolo[bi]) + 0.5 * float(non_normal_probs[final_concat_idx])
            final_preds.append({
                "bbox": boxes[bi],
                "class": yolo_cls,
                "conf": final_conf,
                "mask": yolo_masks[bi] if yolo_masks else None,
            })
            n_kept += 1
            # semantic mask 갱신 (높은 conf가 덮어쓰도록 나중에 정렬)
            if yolo_masks is not None and yolo_masks[bi] is not None:
                pred_semantic[yolo_masks[bi]] = yolo_cls + 1

        # ── Box mAP 매칭 ──
        used_gt = set()
        for pred in sorted(final_preds, key=lambda x: -x["conf"]):
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

        # ── AI Hub mIoU (per class) ──
        for c in range(4):
            gt_t = (gt_semantic == c + 1)
            pred_t = (pred_semantic == c + 1)
            gt_bg = ~gt_t; pred_bg = ~pred_t

            i_t = np.logical_and(gt_t, pred_t).sum()
            u_t = np.logical_or(gt_t, pred_t).sum()
            i_b = np.logical_and(gt_bg, pred_bg).sum()
            u_b = np.logical_or(gt_bg, pred_bg).sum()

            if u_t > 0:
                per_class_ious[c]["target"].append(i_t / u_t)
            if u_b > 0:
                per_class_ious[c]["bg"].append(i_b / u_b)

    # ── 보고 ──
    print("\n" + "=" * 70)
    print("APPROACH A: 1-class YOLO + 5-class Concat (Normal filter)")
    print("=" * 70)

    print(f"\n[Detection]")
    print(f"  YOLO total detections: {n_yolo_detect:,}")
    print(f"  Normal filtered:       {n_normal_filtered:,} ({n_normal_filtered/max(n_yolo_detect,1)*100:.1f}%)")
    print(f"  Final kept:            {n_kept:,}")

    print(f"\n[Box mAP50 — Approach A]")
    aps_box = {}
    for c in range(4):
        ap = compute_ap(box_preds[c], gt_counts[c])
        aps_box[c] = ap
        print(f"  {YOLO_CLASSES[c]:12s}: {ap:.4f}  (GT: {gt_counts[c]})")
    map50 = np.mean(list(aps_box.values()))
    print(f"  MEAN mAP50:    {map50:.4f}")

    print(f"\n[AI Hub mIoU — Approach A]")
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
    print(f"  Approach A (this):                  mAP {map50:.4f},  mIoU(AIHub) {np.mean(miou_list):.4f}")

    # save
    report = {
        "n_yolo_detections": n_yolo_detect,
        "n_normal_filtered": n_normal_filtered,
        "n_kept": n_kept,
        "box_aps": {YOLO_CLASSES[c]: aps_box[c] for c in range(4)},
        "map50": float(map50),
        "aihub_mIoU_per_class": {
            YOLO_CLASSES[c]: float(miou_list[c]) for c in range(4)
        },
        "aihub_mIoU_mean": float(np.mean(miou_list)),
    }
    with open(os.path.join(args.output_dir, "report.json"), "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\nReport saved to {args.output_dir}/report.json")


if __name__ == "__main__":
    main()
