"""
차량 결함 탐지 모델 학습 (YOLOv8)
- VeHIDE 데이터셋 (polygon → YOLO bbox 변환)
- 5개 클래스: dent, scratch, paint_damage, glass_crack, missing_part
- 저장 경로: backend/app/ml_models/defect_detector.pt
"""

import os
import sys
import json
import shutil
import random
import numpy as np
from pathlib import Path
from PIL import Image

# 경로 설정
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VEHIDE_DIR = os.path.join(BASE_DIR, "data", "defect_detection", "vehide")
YOLO_DIR = os.path.join(BASE_DIR, "data", "defect_detection", "yolo_dataset")
MODEL_DIR = os.path.join(BASE_DIR, "backend", "app", "ml_models")
os.makedirs(MODEL_DIR, exist_ok=True)

# VeHIDE 클래스 → 우리 클래스 매핑
CLASS_MAP = {
    'be_den': 'dent',           # 찌그러짐
    'rach': 'scratch',          # 스크래치/찢김
    'tray_son': 'paint_damage', # 도색 손상
    'vo_kinh': 'glass_crack',   # 유리 파손
    'mat_bo_phan': 'missing_part',  # 부품 손실
    # 아래 2개는 제외 (차량 결함이 아닌 타이어 관련)
    # 'mop_lom': 'flat_tire',
    # 'thung': 'puncture',
}

# 최종 클래스 리스트 (YOLO class index)
CLASSES = ['dent', 'scratch', 'paint_damage', 'glass_crack', 'missing_part']


def polygon_to_bbox(all_x, all_y):
    """폴리곤 좌표 → bounding box (x_min, y_min, x_max, y_max)"""
    x_min = min(all_x)
    x_max = max(all_x)
    y_min = min(all_y)
    y_max = max(all_y)
    return x_min, y_min, x_max, y_max


def convert_vehide_to_yolo():
    """VeHIDE VIA JSON → YOLO 형식 변환"""
    print("[1/4] VeHIDE → YOLO 형식 변환")

    # YOLO 디렉토리 구조 생성
    for split in ['train', 'val']:
        os.makedirs(os.path.join(YOLO_DIR, "images", split), exist_ok=True)
        os.makedirs(os.path.join(YOLO_DIR, "labels", split), exist_ok=True)

    total_images = 0
    total_labels = 0
    class_counts = {c: 0 for c in CLASSES}

    for split_name, json_file, img_dir in [
        ('train', '0Train_via_annos.json', 'image/image'),
        ('val', '0Val_via_annos.json', 'validation/validation'),
    ]:
        json_path = os.path.join(VEHIDE_DIR, json_file)
        image_dir = os.path.join(VEHIDE_DIR, img_dir)

        if not os.path.exists(json_path):
            print(f"  [스킵] {json_path} 없음")
            continue

        with open(json_path, 'r') as f:
            data = json.load(f)

        print(f"\n  [{split_name}] {len(data)}개 이미지 처리 중...")

        processed = 0
        skipped = 0

        for img_name, img_data in data.items():
            filename = img_data.get('name', img_name)
            img_path = os.path.join(image_dir, filename)

            if not os.path.exists(img_path):
                skipped += 1
                continue

            # 이미지 크기 확인
            try:
                with Image.open(img_path) as im:
                    img_w, img_h = im.size
            except Exception:
                skipped += 1
                continue

            if img_w == 0 or img_h == 0:
                skipped += 1
                continue

            # 레이블 변환
            regions = img_data.get('regions', [])
            yolo_labels = []

            for region in regions:
                cls_name = region.get('class', '')
                if cls_name not in CLASS_MAP:
                    continue

                mapped_cls = CLASS_MAP[cls_name]
                cls_idx = CLASSES.index(mapped_cls)

                all_x = region.get('all_x', [])
                all_y = region.get('all_y', [])

                if len(all_x) < 3 or len(all_y) < 3:
                    continue

                x_min, y_min, x_max, y_max = polygon_to_bbox(all_x, all_y)

                # 좌표 클리핑
                x_min = max(0, x_min)
                y_min = max(0, y_min)
                x_max = min(img_w, x_max)
                y_max = min(img_h, y_max)

                # 유효성 검사
                if x_max <= x_min or y_max <= y_min:
                    continue

                # YOLO 형식: class_idx cx cy w h (정규화)
                cx = ((x_min + x_max) / 2) / img_w
                cy = ((y_min + y_max) / 2) / img_h
                w = (x_max - x_min) / img_w
                h = (y_max - y_min) / img_h

                # 범위 검사
                if not (0 <= cx <= 1 and 0 <= cy <= 1 and 0 < w <= 1 and 0 < h <= 1):
                    continue

                yolo_labels.append(f"{cls_idx} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
                class_counts[mapped_cls] += 1

            # 결함이 있는 이미지만 저장
            if yolo_labels:
                # 이미지 복사 (심볼릭 링크)
                dst_img = os.path.join(YOLO_DIR, "images", split_name, filename)
                if not os.path.exists(dst_img):
                    try:
                        os.symlink(os.path.abspath(img_path), dst_img)
                    except OSError:
                        shutil.copy2(img_path, dst_img)

                # 레이블 저장
                label_name = os.path.splitext(filename)[0] + '.txt'
                label_path = os.path.join(YOLO_DIR, "labels", split_name, label_name)
                with open(label_path, 'w') as f:
                    f.write('\n'.join(yolo_labels))

                total_labels += len(yolo_labels)
                processed += 1

            total_images += 1

        print(f"    처리: {processed}장 | 스킵: {skipped}장")

    print(f"\n  총 이미지: {total_images}장")
    print(f"  총 레이블: {total_labels}개")
    print(f"  클래스별 분포:")
    for cls, cnt in class_counts.items():
        print(f"    {cls:20s}: {cnt:,}개")

    return class_counts


def create_yaml():
    """YOLO 데이터셋 YAML 생성"""
    print("\n[2/4] 데이터셋 YAML 생성")

    yaml_content = f"""# CarNeRF Vehicle Defect Detection Dataset
path: {os.path.abspath(YOLO_DIR)}
train: images/train
val: images/val

nc: {len(CLASSES)}
names: {CLASSES}
"""
    yaml_path = os.path.join(YOLO_DIR, "dataset.yaml")
    with open(yaml_path, 'w') as f:
        f.write(yaml_content)
    print(f"  저장: {yaml_path}")
    return yaml_path


def train_yolo(yaml_path):
    """YOLOv8 학습"""
    print("\n[3/4] YOLOv8 학습 시작")

    from ultralytics import YOLO

    # YOLOv8s (Small) - 속도/정확도 균형
    model = YOLO('yolov8s.pt')

    # 학습
    results = model.train(
        data=yaml_path,
        epochs=50,
        imgsz=640,
        batch=16,
        device=0,           # GPU 0
        project=os.path.join(BASE_DIR, "runs", "defect"),
        name="yolov8s_vehide",
        patience=15,         # early stopping
        # augmentation
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        degrees=10,
        translate=0.1,
        scale=0.5,
        fliplr=0.5,
        mosaic=1.0,
        # 기타
        workers=4,
        exist_ok=True,
        verbose=True,
    )

    return results, model


def save_model():
    """최적 모델을 backend/app/ml_models/로 복사"""
    print("\n[4/4] 모델 저장")

    best_pt = os.path.join(BASE_DIR, "runs", "defect", "yolov8s_vehide", "weights", "best.pt")
    if not os.path.exists(best_pt):
        # 가장 최근 runs 디렉토리 탐색
        runs_dir = os.path.join(BASE_DIR, "runs", "defect")
        if os.path.exists(runs_dir):
            subdirs = sorted(Path(runs_dir).iterdir(), key=os.path.getmtime, reverse=True)
            for d in subdirs:
                candidate = d / "weights" / "best.pt"
                if candidate.exists():
                    best_pt = str(candidate)
                    break

    if not os.path.exists(best_pt):
        print("  [에러] best.pt를 찾을 수 없습니다!")
        return

    dst = os.path.join(MODEL_DIR, "defect_detector.pt")
    shutil.copy2(best_pt, dst)
    print(f"  저장: {dst}")
    print(f"  원본: {best_pt}")

    # 클래스 정보도 저장
    meta = {
        'classes': CLASSES,
        'class_map': CLASS_MAP,
        'model_type': 'yolov8s',
    }
    joblib.dump(meta, os.path.join(MODEL_DIR, "defect_meta.pkl"))
    print(f"  메타: {MODEL_DIR}/defect_meta.pkl")


def main():
    print("=" * 60)
    print("  CarNeRF 차량 결함 탐지 모델 학습 (YOLOv8)")
    print("=" * 60)

    # 1. 데이터 변환
    class_counts = convert_vehide_to_yolo()

    # 학습 이미지 수 확인
    train_imgs = len(os.listdir(os.path.join(YOLO_DIR, "images", "train")))
    val_imgs = len(os.listdir(os.path.join(YOLO_DIR, "images", "val")))
    print(f"\n  학습: {train_imgs}장 | 검증: {val_imgs}장")

    if train_imgs == 0:
        print("[에러] 학습 이미지가 없습니다!")
        sys.exit(1)

    # 2. YAML 생성
    yaml_path = create_yaml()

    # 3. 학습
    results, model = train_yolo(yaml_path)

    # 4. 모델 저장
    save_model()

    # 결과 요약
    print("\n" + "=" * 60)
    print("  학습 완료!")
    print("=" * 60)
    metrics_path = os.path.join(BASE_DIR, "runs", "defect", "yolov8s_vehide", "results.csv")
    if os.path.exists(metrics_path):
        import pandas as pd
        metrics = pd.read_csv(metrics_path)
        last = metrics.iloc[-1]
        print(f"  mAP50:    {last.get('metrics/mAP50(B)', 'N/A')}")
        print(f"  mAP50-95: {last.get('metrics/mAP50-95(B)', 'N/A')}")
        print(f"  Precision: {last.get('metrics/precision(B)', 'N/A')}")
        print(f"  Recall:    {last.get('metrics/recall(B)', 'N/A')}")


if __name__ == "__main__":
    import joblib
    main()
