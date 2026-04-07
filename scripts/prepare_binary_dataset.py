"""
이진 분류 YOLO 데이터셋 준비
- 기존 5클래스 라벨 → 단일 클래스 'damage' (class 0)으로 통합
- vehide 이미지를 YOLO 디렉토리에 심링크
"""
import os
import shutil
from pathlib import Path

# Paths
BASE = Path("/home/jjh0709/Project_2026_1/data/defect_detection")
VEHIDE_TRAIN = BASE / "vehide" / "image" / "image"
VEHIDE_VAL = BASE / "vehide" / "validation" / "validation"

# Old multi-class dataset
OLD_LABELS_TRAIN = BASE / "yolo_dataset" / "labels" / "train"
OLD_LABELS_VAL = BASE / "yolo_dataset" / "labels" / "val"

# New binary dataset
OUT = BASE / "yolo_binary"
OUT_IMG_TRAIN = OUT / "images" / "train"
OUT_IMG_VAL = OUT / "images" / "val"
OUT_LBL_TRAIN = OUT / "labels" / "train"
OUT_LBL_VAL = OUT / "labels" / "val"

for d in [OUT_IMG_TRAIN, OUT_IMG_VAL, OUT_LBL_TRAIN, OUT_LBL_VAL]:
    d.mkdir(parents=True, exist_ok=True)


def convert_labels(src_label_dir, dst_label_dir, src_img_dir, dst_img_dir):
    """5클래스 라벨 → 단일 클래스 (0=damage) 변환 + 이미지 심링크"""
    count = 0
    skipped = 0
    for label_file in sorted(src_label_dir.glob("*.txt")):
        stem = label_file.stem
        # Find matching image
        img_path = None
        for ext in [".jpg", ".jpeg", ".png"]:
            candidate = src_img_dir / (stem + ext)
            if candidate.exists():
                img_path = candidate
                break

        if img_path is None:
            skipped += 1
            continue

        # Convert labels: all classes → 0 (damage)
        new_lines = []
        with open(label_file) as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 5:
                    # Replace class ID with 0
                    parts[0] = "0"
                    new_lines.append(" ".join(parts))

        if not new_lines:
            skipped += 1
            continue

        # Write new label
        dst_label = dst_label_dir / label_file.name
        with open(dst_label, "w") as f:
            f.write("\n".join(new_lines) + "\n")

        # Symlink image
        dst_img = dst_img_dir / img_path.name
        if not dst_img.exists():
            os.symlink(img_path.resolve(), dst_img)

        count += 1

    return count, skipped


print("Converting train labels...")
train_count, train_skip = convert_labels(
    OLD_LABELS_TRAIN, OUT_LBL_TRAIN, VEHIDE_TRAIN, OUT_IMG_TRAIN
)
print(f"  Train: {train_count} converted, {train_skip} skipped")

print("Converting val labels...")
val_count, val_skip = convert_labels(
    OLD_LABELS_VAL, OUT_LBL_VAL, VEHIDE_VAL, OUT_IMG_VAL
)
print(f"  Val: {val_count} converted, {val_skip} skipped")

# Write dataset YAML
yaml_content = f"""# CarNeRF Binary Damage Detection Dataset
path: {OUT}
train: images/train
val: images/val

nc: 1
names: ['damage']
"""

yaml_path = OUT / "dataset.yaml"
with open(yaml_path, "w") as f:
    f.write(yaml_content)

print(f"\nDataset ready at: {OUT}")
print(f"  Train: {train_count} images")
print(f"  Val: {val_count} images")
print(f"  Config: {yaml_path}")
