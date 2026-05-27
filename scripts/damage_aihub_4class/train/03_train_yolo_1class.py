#!/usr/bin/env python3
"""
1-class YOLOv8l-seg 학습 (Approach A - Stage 1)

검증된 yolov8l-seg 사용 (NaN 없음, 0.4499 mAP 달성한 동일 모델 구조)
1-class라 빠른 수렴 기대 → 60 epoch

Stage 1 목적: 손상 영역 폭넓게 탐지 (recall 극대화)
Stage 2 (Concat 5-class)가 정상/유형 판단 담당
"""

import argparse
from ultralytics import YOLO


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data", default="./datasets/yolo_seg_1cls/data.yaml")
    p.add_argument("--model", default="yolov8l-seg.pt")
    p.add_argument("--epochs", type=int, default=60)
    p.add_argument("--imgsz", type=int, default=1280)
    p.add_argument("--batch", type=int, default=16)
    p.add_argument("--device", default="2")
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--project", default="./outputs")
    p.add_argument("--name", default="yolov8l_seg_1cls")
    p.add_argument("--patience", type=int, default=15)
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
        # 검증된 설정 (v8l-seg 0.4499 동일)
        amp=True,
        mosaic=1.0,
        close_mosaic=10,
        mixup=0.1,
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
        patience=args.patience,
        exist_ok=True,
        verbose=True,
    )


if __name__ == "__main__":
    main()
