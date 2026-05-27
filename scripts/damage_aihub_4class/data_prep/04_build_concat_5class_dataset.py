#!/usr/bin/env python3
"""
5-class Concat 데이터셋 구성 (Approach A - Stage 2 학습용)

5 classes: scratch / dent / breakage / separation / normal
- 4 damage classes: yolo_seg polygon에서 bbox crop
- normal class: scripts/29의 결과 활용

Output: datasets/cls_crops_5class/{train,val}/{class}/*.jpg
"""

import argparse
import os
import shutil
from collections import Counter
from pathlib import Path

import cv2
import numpy as np


CLASS_NAMES = ["scratch", "dent", "breakage", "separation", "normal"]


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--src-yolo-seg", default="./datasets/yolo_seg")
    p.add_argument("--src-normal", default="./datasets/normal_crops")
    p.add_argument("--output-root", default="./datasets/cls_crops_5class")
    p.add_argument("--per-class-damage", type=int, default=5000,
                   help="4개 damage 클래스 각각 추출 개수")
    p.add_argument("--bbox-expand", type=float, default=1.3)
    p.add_argument("--crop-size", type=int, default=224)
    p.add_argument("--bbox-area-min", type=int, default=1500)
    p.add_argument("--bbox-area-max", type=int, default=80000)
    p.add_argument("--poly-pts-min", type=int, default=6)
    p.add_argument("--blur-min", type=float, default=120.0)
    p.add_argument("--val-ratio", type=float, default=0.15)
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


def expand_crop(img, bbox, expand, target):
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


def load_seg_labels(label_path):
    items = []
    with open(label_path) as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) < 7:
                continue
            cls_id = int(parts[0])
            coords = list(map(float, parts[1:]))
            items.append({
                "class_id": cls_id,
                "coords": coords,
                "n_pts": len(coords) // 2,
            })
    return items


def main():
    args = parse_args()
    import random
    random.seed(args.seed)

    src = Path(args.src_yolo_seg)
    src_normal = Path(args.src_normal)
    out = Path(args.output_root)

    for split in ["train", "val"]:
        for cls in CLASS_NAMES:
            (out / split / cls).mkdir(parents=True, exist_ok=True)

    # ─── 1. Damage crops 추출 ───
    print("[1/2] Extracting damage crops from yolo_seg...")
    candidates_by_cls = {0: [], 1: [], 2: [], 3: []}

    for split_src in ["train", "val"]:
        img_dir = src / "images" / split_src
        label_dir = src / "labels" / split_src
        for img_path in sorted(img_dir.iterdir()):
            if img_path.suffix.lower() not in (".jpg", ".jpeg", ".png"):
                continue
            label_path = label_dir / (img_path.stem + ".txt")
            if not label_path.exists():
                continue

            items = load_seg_labels(label_path)
            if not items:
                continue

            try:
                from PIL import Image
                with Image.open(img_path) as im:
                    w, h = im.size
            except Exception:
                continue

            # 이미지 내 클래스별 면적 (모호성 체크)
            cls_area = Counter()
            for it in items:
                if it["n_pts"] < args.poly_pts_min:
                    continue
                xs = np.array(it["coords"][0::2]) * w
                ys = np.array(it["coords"][1::2]) * h
                bw, bh = xs.max() - xs.min(), ys.max() - ys.min()
                cls_area[it["class_id"]] += bw * bh
            if sum(cls_area.values()) == 0:
                continue
            total = sum(cls_area.values())

            for it in items:
                if it["n_pts"] < args.poly_pts_min:
                    continue
                xs = np.array(it["coords"][0::2]) * w
                ys = np.array(it["coords"][1::2]) * h
                x1, y1, x2, y2 = xs.min(), ys.min(), xs.max(), ys.max()
                area = (x2 - x1) * (y2 - y1)
                if not (args.bbox_area_min <= area <= args.bbox_area_max):
                    continue
                # 다른 클래스가 30% 이상이면 모호 → skip
                other = [v for k, v in cls_area.items() if k != it["class_id"]]
                if other and max(other) > 0.3 * total:
                    continue
                candidates_by_cls[it["class_id"]].append({
                    "img_path": img_path,
                    "bbox": [x1, y1, x2, y2],
                    "area": area,
                })

    print(f"  Candidates per class:")
    for c in range(4):
        print(f"    {CLASS_NAMES[c]:12s}: {len(candidates_by_cls[c]):>6,}")

    # ─── 2. 균형 샘플링 + crop 저장 ───
    print(f"\n[2/2] Saving crops (per-class target: {args.per_class_damage:,})...")
    for c in range(4):
        recs = candidates_by_cls[c]
        random.shuffle(recs)
        take = recs[:args.per_class_damage]

        # 이미지 path별로 정렬 (캐시 효율)
        take.sort(key=lambda r: str(r["img_path"]))
        cached_path, cached_img = None, None

        for idx, rec in enumerate(take):
            if rec["img_path"] != cached_path:
                cached_img = cv2.imread(str(rec["img_path"]))
                cached_path = rec["img_path"]
            if cached_img is None:
                continue
            crop = expand_crop(cached_img, rec["bbox"], args.bbox_expand, args.crop_size)
            if crop is None:
                continue
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            blur = cv2.Laplacian(gray, cv2.CV_64F).var()
            if blur < args.blur_min:
                continue

            split = "val" if (idx / len(take)) < args.val_ratio else "train"
            out_name = f"{rec['img_path'].stem}_b{idx:05d}.jpg"
            cv2.imwrite(
                str(out / split / CLASS_NAMES[c] / out_name),
                crop,
                [cv2.IMWRITE_JPEG_QUALITY, 90]
            )
        print(f"  {CLASS_NAMES[c]:12s}: saved")

    # ─── 3. Normal crops 복사 (29번 스크립트 결과) ───
    if src_normal.exists():
        print("\n[3/3] Copying normal crops from script 29...")
        for split in ["train", "val"]:
            normal_src = src_normal / split / "normal"
            normal_dst = out / split / "normal"
            if not normal_src.exists():
                continue
            n = 0
            for f in normal_src.iterdir():
                shutil.copy(f, normal_dst / f.name)
                n += 1
            print(f"  {split}: copied {n:,} normal crops")
    else:
        print(f"\n⚠️ Normal crops not found at {src_normal}. Run script 29 first.")

    # ─── Summary ───
    print("\n[SUMMARY]")
    for split in ["train", "val"]:
        print(f"  [{split}]")
        for cls in CLASS_NAMES:
            n = len(list((out / split / cls).iterdir())) if (out / split / cls).exists() else 0
            print(f"    {cls:12s}: {n:>5,}")


if __name__ == "__main__":
    main()
