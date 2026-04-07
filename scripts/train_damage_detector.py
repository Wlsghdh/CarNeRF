"""
CarNeRF 차량 파손 탐지 모델 학습
- 이진 분류: damage (단일 클래스 object detection)
- YOLOv8n (nano) - 빠른 학습 + 웹 서빙에 적합
- VeHiDE 데이터셋 (11,621 train + 2,324 val)
"""
import os
import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description="Train damage detection model")
    parser.add_argument("--gpu", type=int, default=0, help="GPU device (0,1,2,3 only)")
    parser.add_argument("--epochs", type=int, default=50, help="Training epochs")
    parser.add_argument("--batch", type=int, default=32, help="Batch size")
    parser.add_argument("--imgsz", type=int, default=640, help="Image size")
    parser.add_argument("--model", type=str, default="yolov8n.pt", help="Base model")
    args = parser.parse_args()

    # GPU 4,5,6 금지
    if args.gpu in [4, 5, 6]:
        print("ERROR: GPU 4, 5, 6 사용 금지 (공유 서버 정책)")
        sys.exit(1)

    os.environ["CUDA_VISIBLE_DEVICES"] = str(args.gpu)

    from ultralytics import YOLO

    dataset_yaml = "/home/jjh0709/Project_2026_1/data/defect_detection/yolo_binary/dataset.yaml"
    output_dir = "/home/jjh0709/Project_2026_1/backend/app/ml_models"
    os.makedirs(output_dir, exist_ok=True)

    print(f"=== CarNeRF Damage Detector Training ===")
    print(f"GPU: {args.gpu}")
    print(f"Model: {args.model}")
    print(f"Epochs: {args.epochs}")
    print(f"Batch: {args.batch}")
    print(f"Image size: {args.imgsz}")
    print(f"Dataset: {dataset_yaml}")
    print()

    # Load model
    model = YOLO(args.model)

    # Train
    results = model.train(
        data=dataset_yaml,
        epochs=args.epochs,
        batch=args.batch,
        imgsz=args.imgsz,
        device=0,  # Already set CUDA_VISIBLE_DEVICES
        project="/home/jjh0709/Project_2026_1/runs/detect",
        name="damage_binary",
        exist_ok=True,
        # Hyperparameters
        lr0=0.01,
        lrf=0.01,
        momentum=0.937,
        weight_decay=0.0005,
        warmup_epochs=3,
        warmup_momentum=0.8,
        # Augmentation
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        degrees=10.0,
        translate=0.1,
        scale=0.5,
        flipud=0.0,
        fliplr=0.5,
        mosaic=1.0,
        mixup=0.1,
        # Save
        save=True,
        save_period=10,
        patience=15,
        verbose=True,
    )

    # Copy best model to ml_models directory
    best_path = "/home/jjh0709/Project_2026_1/runs/detect/damage_binary/weights/best.pt"
    dest_path = os.path.join(output_dir, "defect_detector.pt")

    if os.path.exists(best_path):
        import shutil
        shutil.copy2(best_path, dest_path)
        print(f"\n=== Training Complete ===")
        print(f"Best model copied to: {dest_path}")

        # Save metadata
        import json
        meta = {
            "classes": ["damage"],
            "nc": 1,
            "model_type": args.model,
            "epochs": args.epochs,
            "imgsz": args.imgsz,
            "dataset": "vehide_binary",
            "train_images": 10356,
            "val_images": 2070,
        }
        meta_path = os.path.join(output_dir, "defect_meta.json")
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)
        print(f"Metadata saved to: {meta_path}")
    else:
        print(f"WARNING: Best model not found at {best_path}")

    # Validation metrics
    print("\n=== Validation Results ===")
    val_results = model.val()
    print(f"mAP50: {val_results.box.map50:.4f}")
    print(f"mAP50-95: {val_results.box.map:.4f}")


if __name__ == "__main__":
    main()
