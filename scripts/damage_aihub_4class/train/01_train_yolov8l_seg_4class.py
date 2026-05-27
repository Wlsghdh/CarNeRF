#!/usr/bin/env python3
"""
YOLOv8l-seg 학습 스크립트

- GPU 1대 (A100 80GB)
- DataLoader workers=2 (CPU 부하 최소화)
- imgsz=1280 (scratch 같은 얇은 손상 탐지에 유리)
"""

import argparse
from ultralytics import YOLO


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data", default="./datasets/yolo_seg/data.yaml")
    p.add_argument("--model", default="yolov8l-seg.pt")
    p.add_argument("--epochs", type=int, default=100)
    p.add_argument("--imgsz", type=int, default=1280)
    p.add_argument("--batch", type=int, default=8)
    p.add_argument("--device", default="2")
    p.add_argument("--workers", type=int, default=2)
    p.add_argument("--project", default="./outputs")
    p.add_argument("--name", default="yolov8l_seg_v1")
    p.add_argument("--resume", action="store_true")
    args = p.parse_args()

    model = YOLO(args.model)

    model.train(
        data=args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        workers=args.workers,
        project=args.project,
        name=args.name,
        # augmentation
        mosaic=1.0,
        mixup=0.1,
        copy_paste=0.1,
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        flipud=0.0,
        fliplr=0.5,
        scale=0.5,
        # optimization
        optimizer="AdamW",
        lr0=0.001,
        lrf=0.01,
        weight_decay=0.0005,
        warmup_epochs=3,
        # saving
        save=True,
        save_period=10,
        patience=20,
        # misc
        exist_ok=True,
        resume=args.resume,
        verbose=True,
    )


if __name__ == "__main__":
    main()
