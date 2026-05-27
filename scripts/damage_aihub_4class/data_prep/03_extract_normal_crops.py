#!/usr/bin/env python3
"""
Hard negative mining: 정상 crop 추출

목적: Concat 분류기를 5-class (4 damage + 1 normal) 로 학습 위한 데이터
방법: GT bbox와 겹치지 않는 random 영역 crop = 정상 차량 부위

각 이미지에서 N개의 정상 crop 추출, IoU < 0.05 보장.
"""

import argparse
import os
import random
from collections import Counter
from pathlib import Path

import cv2
import numpy as np


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--src-root", default="./datasets/yolo_seg")
    p.add_argument("--output-dir", default="./datasets/normal_crops")
    p.add_argument("--per-image-normal", type=int, default=2,
                   help="이미지당 정상 crop 개수")
    p.add_argument("--target-total", type=int, default=20000)
    p.add_argument("--crop-size", type=int, default=224)
    p.add_argument("--min-bbox-size", type=int, default=120,
                   help="추출할 crop의 원본 bbox 최소 크기 (랜덤)")
    p.add_argument("--max-bbox-size", type=int, default=300)
    p.add_argument("--max-iou", type=float, default=0.05,
                   help="GT bbox와의 최대 허용 IoU")
    p.add_argument("--blur-min", type=float, default=80.0)
    p.add_argument("--val-ratio", type=float, default=0.15)
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


def load_gt_bboxes(label_path, w, h):
    """polygon 라벨 → bbox 리스트"""
    if not os.path.exists(label_path):
        return []
    bboxes = []
    with open(label_path) as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) < 7:
                continue
            coords = list(map(float, parts[1:]))
            xs = np.array(coords[0::2]) * w
            ys = np.array(coords[1::2]) * h
            bboxes.append([xs.min(), ys.min(), xs.max(), ys.max()])
    return bboxes


def bbox_iou(b1, b2):
    x1 = max(b1[0], b2[0]); y1 = max(b1[1], b2[1])
    x2 = min(b1[2], b2[2]); y2 = min(b1[3], b2[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    a1 = (b1[2] - b1[0]) * (b1[3] - b1[1])
    a2 = (b2[2] - b2[0]) * (b2[3] - b2[1])
    u = a1 + a2 - inter
    return inter / u if u > 0 else 0


def sample_normal_bbox(w, h, gt_bboxes, min_size, max_size, max_iou, max_tries=20):
    """GT와 겹치지 않는 random bbox 샘플링"""
    for _ in range(max_tries):
        side = random.randint(min_size, max_size)
        # 이미지 내부에 들어가도록
        if side >= w or side >= h:
            continue
        x = random.randint(0, w - side)
        y = random.randint(0, h - side)
        cand = [x, y, x + side, y + side]

        # 모든 GT와 IoU 체크
        max_overlap = max([bbox_iou(cand, g) for g in gt_bboxes], default=0)
        if max_overlap < max_iou:
            return cand
    return None


def main():
    args = parse_args()
    random.seed(args.seed)

    src = Path(args.src_root)
    out = Path(args.output_dir)
    for split in ["train", "val"]:
        (out / split / "normal").mkdir(parents=True, exist_ok=True)

    # train val 모두에서 추출 (yolo_seg의 분할 따라감)
    stats = {"train": 0, "val": 0, "no_crop_possible": 0, "blur_filtered": 0}

    # train과 val 합쳐서 처리, 분할은 args.val_ratio로 다시
    all_pairs = []
    for split in ["train", "val"]:
        img_dir = src / "images" / split
        label_dir = src / "labels" / split
        for img_path in sorted(img_dir.iterdir()):
            if img_path.suffix.lower() not in (".jpg", ".jpeg", ".png"):
                continue
            label_path = label_dir / (img_path.stem + ".txt")
            all_pairs.append((img_path, label_path))

    random.shuffle(all_pairs)
    target = args.target_total
    saved = 0

    print(f"Extracting normal crops (target: {target:,})...")
    for idx, (img_path, label_path) in enumerate(all_pairs):
        if saved >= target:
            break
        if (idx + 1) % 2000 == 0:
            print(f"  ...processed {idx+1:,}, saved {saved:,}")

        img = cv2.imread(str(img_path))
        if img is None:
            continue
        h, w = img.shape[:2]

        gt_bboxes = load_gt_bboxes(label_path, w, h)
        if not gt_bboxes:
            continue

        for k in range(args.per_image_normal):
            if saved >= target:
                break
            cand_bbox = sample_normal_bbox(
                w, h, gt_bboxes,
                args.min_bbox_size, args.max_bbox_size, args.max_iou
            )
            if cand_bbox is None:
                stats["no_crop_possible"] += 1
                continue

            x1, y1, x2, y2 = cand_bbox
            crop = img[y1:y2, x1:x2]
            if crop.size == 0:
                continue

            # blur 체크
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            blur = cv2.Laplacian(gray, cv2.CV_64F).var()
            if blur < args.blur_min:
                stats["blur_filtered"] += 1
                continue

            crop_resized = cv2.resize(crop, (args.crop_size, args.crop_size))

            split = "val" if random.random() < args.val_ratio else "train"
            out_name = f"{img_path.stem}_n{k}.jpg"
            cv2.imwrite(
                str(out / split / "normal" / out_name),
                crop_resized,
                [cv2.IMWRITE_JPEG_QUALITY, 90]
            )
            stats[split] += 1
            saved += 1

    print(f"\n[DONE]")
    print(f"  Saved Train normal: {stats['train']:,}")
    print(f"  Saved Val normal:   {stats['val']:,}")
    print(f"  Total:              {stats['train'] + stats['val']:,}")
    print(f"  Blur filtered:      {stats['blur_filtered']:,}")
    print(f"  No crop possible:   {stats['no_crop_possible']:,}")

    size_mb = sum(
        os.path.getsize(os.path.join(dp, f))
        for dp, _, fns in os.walk(out) for f in fns
    ) / 1024**2
    print(f"  Disk: {size_mb:.1f} MB")


if __name__ == "__main__":
    main()
