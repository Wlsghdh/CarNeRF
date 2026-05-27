#!/usr/bin/env python3
"""
ZIP에서 직접 읽어 품질 필터링 → 클래스 균형 샘플링 → 데이터셋 생성

생성물:
  datasets/
    yolo_seg/           ← YOLOv8 segmentation 학습용
      images/train/
      images/val/
      labels/train/     ← YOLO polygon seg format
      labels/val/
      data.yaml
    cls_crop/           ← 분류 모델 학습용 (bbox crop 224x224)
      train/{scratch,dent,breakage,separation}/
      val/{scratch,dent,breakage,separation}/

사용법:
  python 02_build_dataset.py \
    --label-zip /path/TL_damage.zip \
    --image-zip /path/TS_damage.zip \
    --output-root ./datasets \
    --max-images 30000 \
    --val-ratio 0.15 \
    --min-bbox-area 1000 \
    --min-poly-pts 5
"""

import argparse
import json
import os
import random
import zipfile
from collections import Counter, defaultdict
from io import BytesIO
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

# ── 클래스 매핑 ──
DAMAGE_MAP = {
    "Scratched": 0,   # scratch
    "Crushed": 1,     # dent
    "Breakage": 2,    # breakage
    "Separated": 3,   # separation
}
CLASS_NAMES = ["scratch", "dent", "breakage", "separation"]


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--label-zip", required=True)
    p.add_argument("--image-zip", required=True)
    p.add_argument("--output-root", default="./datasets")
    p.add_argument("--max-images", type=int, default=30000,
                   help="최대 추출 이��지 수")
    p.add_argument("--val-ratio", type=float, default=0.15)
    p.add_argument("--min-bbox-area", type=int, default=1000)
    p.add_argument("--min-poly-pts", type=int, default=5)
    p.add_argument("--crop-size", type=int, default=224,
                   help="분류용 crop 리사이즈 크기")
    p.add_argument("--expand-ratio", type=float, default=1.5,
                   help="crop 시 bbox 확장 비율")
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


def parse_all_labels(label_zip_path, min_bbox_area, min_poly_pts):
    """라벨 ZIP에서 품질 필터링된 레코드 추출 (메모리 only)"""
    print("[1/5] Parsing & filtering labels from ZIP...")
    zf = zipfile.ZipFile(label_zip_path, "r")
    json_names = [n for n in zf.namelist() if n.endswith(".json")]
    print(f"  Total JSON files: {len(json_names):,}")

    # image_file -> list of annotations
    img_records = defaultdict(lambda: {"annotations": [], "width": 0, "height": 0})
    total_annos = 0
    filtered_annos = 0

    for i, name in enumerate(json_names):
        if (i + 1) % 100000 == 0:
            print(f"  ...{i+1:,}/{len(json_names):,}")
        try:
            data = json.loads(zf.read(name))
        except Exception:
            continue

        img_info = data.get("images", {})
        img_file = img_info.get("file_name", "")
        w = img_info.get("width", 0)
        h = img_info.get("height", 0)
        if not img_file or w == 0 or h == 0:
            continue

        for anno in data.get("annotations", []):
            damage = anno.get("damage", "")
            if damage not in DAMAGE_MAP:
                continue
            total_annos += 1

            # bbox 필터
            bbox = anno.get("bbox", [])
            if len(bbox) != 4:
                continue
            area = bbox[2] * bbox[3]
            if area < min_bbox_area:
                filtered_annos += 1
                continue

            # polygon 필터
            seg = anno.get("segmentation", [])
            try:
                points = seg[0][0]
                if len(points) < min_poly_pts:
                    filtered_annos += 1
                    continue
            except (IndexError, TypeError):
                filtered_annos += 1
                continue

            img_records[img_file]["width"] = w
            img_records[img_file]["height"] = h
            img_records[img_file]["annotations"].append({
                "class_id": DAMAGE_MAP[damage],
                "class_name": CLASS_NAMES[DAMAGE_MAP[damage]],
                "bbox": bbox,
                "points": points,
            })

    zf.close()
    print(f"  Total annotations: {total_annos:,}")
    print(f"  Filtered out: {filtered_annos:,} ({filtered_annos/total_annos*100:.1f}%)")
    print(f"  Remaining images: {len(img_records):,}")

    # 클래스 분포 출력
    class_counter = Counter()
    for rec in img_records.values():
        for a in rec["annotations"]:
            class_counter[a["class_name"]] += 1
    print(f"  Class distribution:")
    for name, cnt in class_counter.most_common():
        print(f"    {name:12s}: {cnt:>8,}")

    return dict(img_records)


def balanced_sample(img_records, max_images, seed):
    """클래스 균형을 고려한 이미지 샘플링"""
    print(f"\n[2/5] Balanced sampling (max {max_images:,} images)...")
    random.seed(seed)

    # 이미지별 주요 클래스 결정 (가장 많은 annotation의 클래스)
    img_primary_class = {}
    for img_file, rec in img_records.items():
        cls_counts = Counter(a["class_id"] for a in rec["annotations"])
        img_primary_class[img_file] = cls_counts.most_common(1)[0][0]

    # 클래스별 이미지 그룹
    class_images = defaultdict(list)
    for img_file, cls_id in img_primary_class.items():
        class_images[cls_id].append(img_file)

    # 각 클래스 셔플
    for cls_id in class_images:
        random.shuffle(class_images[cls_id])

    # 소수 클래스 기준 균형 샘플링
    per_class = max_images // len(CLASS_NAMES)
    selected = []
    for cls_id in range(len(CLASS_NAMES)):
        available = class_images[cls_id]
        n_take = min(per_class, len(available))
        selected.extend(available[:n_take])
        print(f"  {CLASS_NAMES[cls_id]:12s}: {n_take:,} / {len(available):,} available")

    # 남은 할당량이 있으면 scratch(가장 많은 클래스)에서 추가
    remaining = max_images - len(selected)
    if remaining > 0:
        already = set(selected)
        extras = [f for f in class_images[0] if f not in already][:remaining]
        selected.extend(extras)
        print(f"  Extra from scratch: {len(extras):,}")

    random.shuffle(selected)
    print(f"  Total selected: {len(selected):,}")
    return selected


def build_datasets(args, img_records, selected_images):
    """선택된 이미지만 ZIP에서 추출 → YOLO seg + classification crop 생성"""

    # train/val 분할
    random.seed(args.seed)
    random.shuffle(selected_images)
    n_val = int(len(selected_images) * args.val_ratio)
    val_set = set(selected_images[:n_val])
    train_set = set(selected_images[n_val:])
    print(f"\n[3/5] Split: train={len(train_set):,}, val={len(val_set):,}")

    # 출력 디렉토리 생성
    yolo_root = os.path.join(args.output_root, "yolo_seg")
    cls_root = os.path.join(args.output_root, "cls_crop")
    for split in ["train", "val"]:
        os.makedirs(os.path.join(yolo_root, "images", split), exist_ok=True)
        os.makedirs(os.path.join(yolo_root, "labels", split), exist_ok=True)
        for cls_name in CLASS_NAMES:
            os.makedirs(os.path.join(cls_root, split, cls_name), exist_ok=True)

    # 이미지 ZIP 파일명 인덱스
    print("[4/5] Building image index from ZIP...")
    img_zf = zipfile.ZipFile(args.image_zip, "r")
    img_index = {}
    for zname in img_zf.namelist():
        if zname.lower().endswith((".jpg", ".jpeg", ".png")):
            basename = os.path.basename(zname)
            img_index[basename] = zname

    # 이미지 추출 및 라벨 생성
    selected_set = set(selected_images)
    print(f"[5/5] Extracting {len(selected_set):,} images & generating labels...")

    stats = {"train": Counter(), "val": Counter(), "missing": 0, "error": 0}
    crop_id = 0

    for idx, img_file in enumerate(selected_images):
        if (idx + 1) % 5000 == 0:
            print(f"  ...{idx+1:,}/{len(selected_images):,}")

        rec = img_records[img_file]
        split = "val" if img_file in val_set else "train"

        # ZIP에서 이미지 읽기
        if img_file not in img_index:
            stats["missing"] += 1
            continue

        try:
            img_data = img_zf.read(img_index[img_file])
            img_arr = np.frombuffer(img_data, np.uint8)
            img = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
            if img is None:
                stats["error"] += 1
                continue
        except Exception:
            stats["error"] += 1
            continue

        h_img, w_img = img.shape[:2]
        stem = os.path.splitext(img_file)[0]

        # ── (A) YOLO seg: 이미지 저장 + 라벨 생성 ──
        img_out = os.path.join(yolo_root, "images", split, img_file)
        cv2.imwrite(img_out, img)

        label_lines = []
        for anno in rec["annotations"]:
            cls_id = anno["class_id"]
            points = anno["points"]
            stats[split][CLASS_NAMES[cls_id]] += 1

            # YOLO seg format: class_id x1 y1 x2 y2 ... (normalized)
            normalized = []
            for pt in points:
                nx = pt[0] / w_img
                ny = pt[1] / h_img
                nx = max(0.0, min(1.0, nx))
                ny = max(0.0, min(1.0, ny))
                normalized.extend([nx, ny])
            coords_str = " ".join(f"{v:.6f}" for v in normalized)
            label_lines.append(f"{cls_id} {coords_str}")

        label_out = os.path.join(yolo_root, "labels", split, stem + ".txt")
        with open(label_out, "w") as f:
            f.write("\n".join(label_lines) + "\n")

        # ── (B) Classification crop: bbox 기반 크롭 ──
        for anno in rec["annotations"]:
            cls_id = anno["class_id"]
            cls_name = anno["class_name"]
            bx, by, bw, bh = anno["bbox"]

            # bbox 확장
            cx, cy = bx + bw / 2, by + bh / 2
            ew = bw * args.expand_ratio
            eh = bh * args.expand_ratio
            side = max(ew, eh, args.crop_size)  # 최소 crop_size 보장

            x1 = max(0, int(cx - side / 2))
            y1 = max(0, int(cy - side / 2))
            x2 = min(w_img, int(cx + side / 2))
            y2 = min(h_img, int(cy + side / 2))

            crop = img[y1:y2, x1:x2]
            if crop.size == 0:
                continue
            crop_resized = cv2.resize(crop, (args.crop_size, args.crop_size))

            crop_name = f"{stem}_c{crop_id}.jpg"
            crop_out = os.path.join(cls_root, split, cls_name, crop_name)
            cv2.imwrite(crop_out, crop_resized)
            crop_id += 1

    img_zf.close()

    # ── YOLO data.yaml 생성 ──
    yaml_content = f"""path: {os.path.abspath(yolo_root)}
train: images/train
val: images/val

names:
  0: scratch
  1: dent
  2: breakage
  3: separation

nc: 4
"""
    with open(os.path.join(yolo_root, "data.yaml"), "w") as f:
        f.write(yaml_content)

    # ── 결과 리포트 ──
    print("\n" + "=" * 60)
    print("DATASET BUILD COMPLETE")
    print("=" * 60)
    print(f"Missing images: {stats['missing']:,}")
    print(f"Read errors: {stats['error']:,}")
    print(f"\n[YOLO Seg - Train] annotations per class:")
    for name in CLASS_NAMES:
        print(f"  {name:12s}: {stats['train'][name]:>6,}")
    print(f"\n[YOLO Seg - Val] annotations per class:")
    for name in CLASS_NAMES:
        print(f"  {name:12s}: {stats['val'][name]:>6,}")
    print(f"\nTotal crops generated: {crop_id:,}")

    # 디스크 사용량
    for d in [yolo_root, cls_root]:
        size = sum(
            os.path.getsize(os.path.join(dp, f))
            for dp, _, fns in os.walk(d) for f in fns
        )
        print(f"  {d}: {size / 1024**3:.2f} GB")


def main():
    args = parse_args()

    # Step 1: 라벨 파싱 + 필터링
    img_records = parse_all_labels(
        args.label_zip, args.min_bbox_area, args.min_poly_pts
    )

    # Step 2: 균형 샘플링
    selected = balanced_sample(img_records, args.max_images, args.seed)

    # Step 3: 데이터셋 생성
    build_datasets(args, img_records, selected)

    print("\nDone!")


if __name__ == "__main__":
    main()
