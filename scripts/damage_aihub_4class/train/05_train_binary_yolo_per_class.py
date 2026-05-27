#!/usr/bin/env python3
"""
Approach B: 클래스별 binary YOLO 학습 (4번 실행)

각 클래스에 대해 binary 데이터셋 생성 + YOLOv8l-seg 학습

사용법:
  # scratch (class 0) binary 학습
  python 34_train_binary_yolo_per_class.py --target-class 0 --epochs 20

  # 4 클래스 모두 순차 실행 (한 번에)
  python 34_train_binary_yolo_per_class.py --all --epochs 20

설정:
  - epochs 짧게 (binary는 빠르게 수렴, AI Hub도 1-9 epoch 사용)
  - imgsz 1024 (1280보다 작아서 빠름, AI Hub 256보다는 큼)
  - 4 모델 총 ~32~40h 목표
"""

import argparse
import os
from pathlib import Path
from ultralytics import YOLO


CLASS_NAMES = ["scratch", "dent", "breakage", "separation"]


def build_binary_dataset(src_root, dst_root, target_cls):
    """target_cls만 0번으로, 나머지는 라벨에서 제거"""
    src = Path(src_root).resolve()
    dst = Path(dst_root).resolve()
    assert src.exists(), f"Source not found: {src}"

    print(f"Building binary dataset for class {target_cls} ({CLASS_NAMES[target_cls]}): {dst}")
    dst.mkdir(parents=True, exist_ok=True)

    # data.yaml
    (dst / "data.yaml").write_text(f"""path: {dst}
train: images/train
val: images/val

names:
  0: {CLASS_NAMES[target_cls]}

nc: 1
""")

    for split in ["train", "val"]:
        # ⚠️ 폴더 symlink 대신 파일 단위 symlink (28 스크립트 fix 패턴)
        src_imgs = src / "images" / split
        dst_imgs = dst / "images" / split
        dst_imgs.mkdir(parents=True, exist_ok=True)
        n_imgs = 0
        for img in src_imgs.iterdir():
            if img.suffix.lower() not in (".jpg", ".jpeg", ".png"):
                continue
            link = dst_imgs / img.name
            if not link.exists():
                os.symlink(img.resolve(), link)
            n_imgs += 1

        # labels: target_cls만 남기고 모두 0으로
        src_labels = src / "labels" / split
        dst_labels = dst / "labels" / split
        dst_labels.mkdir(parents=True, exist_ok=True)

        n_lines, n_files = 0, 0
        for lf in src_labels.iterdir():
            if lf.suffix != ".txt":
                continue
            new_lines = []
            with open(lf) as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) < 7:
                        continue
                    if int(parts[0]) != target_cls:
                        continue  # 다른 클래스는 제외
                    parts[0] = "0"
                    new_lines.append(" ".join(parts))
                    n_lines += 1
            # 모두 비어도 파일은 생성 (background only)
            (dst_labels / lf.name).write_text("\n".join(new_lines) + ("\n" if new_lines else ""))
            n_files += 1
        print(f"  {split}: {n_files:,} files, {n_lines:,} {CLASS_NAMES[target_cls]} instances")


def train_binary(data_yaml, target_cls, args):
    """단일 binary YOLO 학습 (resume + skip-if-done 안전장치 포함)"""
    run_name = f"yolov8l_seg_binary_{CLASS_NAMES[target_cls]}"
    run_dir = Path(args.project) / run_name
    last_pt = run_dir / "weights" / "last.pt"
    best_pt = run_dir / "weights" / "best.pt"
    results_csv = run_dir / "results.csv"

    # 1. 이미 완료된 경우 skip
    if best_pt.exists() and results_csv.exists():
        try:
            with open(results_csv) as f:
                n_epochs_done = sum(1 for _ in f) - 1  # header 제외
        except Exception:
            n_epochs_done = 0
        if n_epochs_done >= args.epochs:
            print(f"\n[SKIP] {CLASS_NAMES[target_cls]}: already done ({n_epochs_done}/{args.epochs} epochs)")
            return

    # 2. last.pt 있으면 resume
    if last_pt.exists():
        print(f"\n[RESUME] {CLASS_NAMES[target_cls]} binary YOLOv8l-seg from {last_pt}")
        model = YOLO(str(last_pt))
        model.train(resume=True)
        return

    # 3. 처음부터 학습
    print(f"\n[Training] {CLASS_NAMES[target_cls]} binary YOLOv8l-seg")
    model = YOLO(args.model)
    model.train(
        data=data_yaml,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        workers=args.workers,
        project=args.project,
        name=run_name,
        amp=True,
        mosaic=1.0,
        close_mosaic=5,
        mixup=0.05,
        copy_paste=0.1,
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        fliplr=0.5,
        scale=0.5,
        optimizer="AdamW",
        lr0=0.001,
        lrf=0.01,
        weight_decay=0.0005,
        warmup_epochs=3,
        save=True,
        save_period=-1,
        patience=8,
        exist_ok=True,
        verbose=True,
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--src-root", default="./datasets/yolo_seg")
    p.add_argument("--dst-root-base", default="./datasets/yolo_seg_binary")
    p.add_argument("--target-class", type=int, default=0,
                   help="0=scratch, 1=dent, 2=breakage, 3=separation")
    p.add_argument("--all", action="store_true",
                   help="4 클래스 순차 학습")
    p.add_argument("--model", default="yolov8l-seg.pt")
    p.add_argument("--epochs", type=int, default=20)
    p.add_argument("--imgsz", type=int, default=1024,
                   help="binary는 좀 작아도 OK (1280에서 1024로)")
    p.add_argument("--batch", type=int, default=16)
    p.add_argument("--device", default="2")
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--project", default="./outputs")
    args = p.parse_args()

    targets = [0, 1, 2, 3] if args.all else [args.target_class]

    for c in targets:
        dst_root = f"{args.dst_root_base}_{CLASS_NAMES[c]}"
        # 1. 데이터셋 구성
        build_binary_dataset(args.src_root, dst_root, c)
        # 2. 학습
        data_yaml = str(Path(dst_root) / "data.yaml")
        train_binary(data_yaml, c, args)


if __name__ == "__main__":
    main()
