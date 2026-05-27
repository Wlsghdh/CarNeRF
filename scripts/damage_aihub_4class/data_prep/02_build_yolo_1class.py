#!/usr/bin/env python3
"""
1-class YOLO 데이터셋 구성 (Approach A: 논문 1 방식)

기존 yolo_seg (4-class) → yolo_seg_1cls (1-class "damage")
- 이미지는 symlink 재사용
- 라벨만 새로: 모든 class id → 0

목적: Stage 1 detection이 클래스 구분 부담 없이 손상 영역만 학습
      → 재현율(recall) 극대화
"""

import argparse
import os
from pathlib import Path


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--src-root", default="./datasets/yolo_seg")
    p.add_argument("--dst-root", default="./datasets/yolo_seg_1cls")
    return p.parse_args()


def convert_label(src_path, dst_path):
    with open(src_path) as f:
        lines = f.readlines()
    new_lines = []
    for line in lines:
        parts = line.strip().split()
        if len(parts) < 7:
            continue
        parts[0] = "0"  # class id 강제 0
        new_lines.append(" ".join(parts))
    with open(dst_path, "w") as f:
        f.write("\n".join(new_lines) + "\n")


def main():
    args = parse_args()
    src = Path(args.src_root).resolve()
    dst = Path(args.dst_root).resolve()
    assert src.exists(), f"Source not found: {src}"

    print(f"[1-class] {src} → {dst}")
    dst.mkdir(parents=True, exist_ok=True)

    # data.yaml
    (dst / "data.yaml").write_text(f"""path: {dst}
train: images/train
val: images/val

names:
  0: damage

nc: 1
""")

    # ⚠️ 이미지는 폴더 symlink 대신 파일 단위 symlink (ultralytics가 라벨 경로 잘못 찾는 문제 방지)
    total = 0
    for split in ["train", "val"]:
        src_imgs = src / "images" / split
        dst_imgs = dst / "images" / split
        dst_imgs.mkdir(parents=True, exist_ok=True)

        # 각 이미지 파일을 개별 symlink
        n_imgs = 0
        for img in src_imgs.iterdir():
            if img.suffix.lower() not in (".jpg", ".jpeg", ".png"):
                continue
            link = dst_imgs / img.name
            if not link.exists():
                os.symlink(img.resolve(), link)
            n_imgs += 1

        # 라벨 변환
        src_labels = src / "labels" / split
        dst_labels = dst / "labels" / split
        dst_labels.mkdir(parents=True, exist_ok=True)

        n = 0
        for lf in src_labels.iterdir():
            if lf.suffix != ".txt":
                continue
            convert_label(lf, dst_labels / lf.name)
            n += 1
            total += 1
        print(f"  {split}: {n_imgs:,} image symlinks, {n:,} labels")

    print(f"\n[DONE] Total: {total:,} labels → 1-class")


if __name__ == "__main__":
    main()
