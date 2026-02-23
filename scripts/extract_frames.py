#!/usr/bin/env python3
"""
영상에서 프레임 추출 스크립트
- 흔들림 필터링 (Laplacian variance)
- 균등 샘플링
- 이미지 폴더도 지원
"""

import argparse
import os
import sys
import glob
import shutil
import logging

import cv2
import numpy as np
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def compute_blur_score(image: np.ndarray) -> float:
    """Laplacian variance로 흔들림 점수를 계산한다. 값이 높을수록 선명."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return cv2.Laplacian(gray, cv2.CV_64F).var()


def resize_if_needed(image: np.ndarray, max_long_side: int = 1600) -> np.ndarray:
    """긴 변이 max_long_side를 초과하면 리사이즈한다."""
    h, w = image.shape[:2]
    long_side = max(h, w)
    if long_side <= max_long_side:
        return image
    scale = max_long_side / long_side
    new_w = int(w * scale)
    new_h = int(h * scale)
    return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)


def extract_from_video(
    video_path: str,
    output_dir: str,
    max_frames: int,
    min_blur_score: float,
) -> int:
    """영상 파일에서 프레임을 추출한다."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.error(f"영상 파일을 열 수 없습니다: {video_path}")
        sys.exit(1)

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    logger.info(f"영상 정보: 총 {total_frames}프레임, {fps:.1f} FPS")

    # 1단계: 3프레임마다 샘플링하면서 블러 필터링
    candidates = []
    frame_idx = 0

    logger.info("프레임 추출 및 흔들림 필터링 중...")
    pbar = tqdm(total=total_frames, desc="프레임 스캔")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % 3 == 0:
            blur_score = compute_blur_score(frame)
            if blur_score >= min_blur_score:
                candidates.append((frame_idx, blur_score, frame))

        frame_idx += 1
        pbar.update(1)

    pbar.close()
    cap.release()

    logger.info(f"흔들림 필터링 결과: {total_frames // 3}개 중 {len(candidates)}개 통과 (blur >= {min_blur_score})")

    if len(candidates) == 0:
        logger.error("선명한 프레임이 하나도 없습니다. --min_blur_score 값을 낮춰 보세요.")
        sys.exit(1)

    # 2단계: 균등 간격으로 max_frames개 선택
    if len(candidates) > max_frames:
        indices = np.linspace(0, len(candidates) - 1, max_frames, dtype=int)
        selected = [candidates[i] for i in indices]
    else:
        selected = candidates

    logger.info(f"최종 선택: {len(selected)}개 프레임")

    # 3단계: 저장
    os.makedirs(output_dir, exist_ok=True)
    for i, (fidx, score, frame) in enumerate(selected):
        frame = resize_if_needed(frame)
        filename = f"frame_{i:04d}.jpg"
        cv2.imwrite(os.path.join(output_dir, filename), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])

    return len(selected)


def extract_from_images(
    image_dir: str,
    output_dir: str,
    max_frames: int,
    min_blur_score: float,
) -> int:
    """이미지 폴더에서 프레임을 추출한다."""
    extensions = ["*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG", "*.PNG"]
    image_paths = []
    for ext in extensions:
        image_paths.extend(glob.glob(os.path.join(image_dir, ext)))
    image_paths.sort()

    if not image_paths:
        logger.error(f"이미지를 찾을 수 없습니다: {image_dir}")
        sys.exit(1)

    logger.info(f"발견된 이미지: {len(image_paths)}개")

    # 블러 필터링
    candidates = []
    filtered_count = 0
    for path in tqdm(image_paths, desc="흔들림 필터링"):
        img = cv2.imread(path)
        if img is None:
            logger.warning(f"이미지를 읽을 수 없습니다: {path}")
            continue
        blur_score = compute_blur_score(img)
        if blur_score >= min_blur_score:
            candidates.append((path, blur_score, img))
        else:
            filtered_count += 1

    logger.info(f"흔들림 필터링 결과: {filtered_count}개 제외, {len(candidates)}개 통과")

    if len(candidates) == 0:
        logger.error("선명한 이미지가 하나도 없습니다. --min_blur_score 값을 낮춰 보세요.")
        sys.exit(1)

    # 균등 간격 선택
    if len(candidates) > max_frames:
        indices = np.linspace(0, len(candidates) - 1, max_frames, dtype=int)
        selected = [candidates[i] for i in indices]
    else:
        selected = candidates

    logger.info(f"최종 선택: {len(selected)}개 이미지")

    # 저장
    os.makedirs(output_dir, exist_ok=True)
    for i, (path, score, img) in enumerate(selected):
        img = resize_if_needed(img)
        filename = f"frame_{i:04d}.jpg"
        cv2.imwrite(os.path.join(output_dir, filename), img, [cv2.IMWRITE_JPEG_QUALITY, 95])

    return len(selected)


def main():
    parser = argparse.ArgumentParser(description="영상/이미지에서 프레임 추출")
    parser.add_argument("--input", required=True, help="영상 파일 경로 또는 이미지 폴더 경로")
    parser.add_argument("--output", required=True, help="프레임 저장 경로")
    parser.add_argument("--max_frames", type=int, default=80, help="최대 프레임 수 (기본값: 80)")
    parser.add_argument("--min_blur_score", type=float, default=100.0, help="최소 블러 점수 (기본값: 100)")
    args = parser.parse_args()

    input_path = os.path.abspath(args.input)
    output_path = os.path.abspath(args.output)

    if not os.path.exists(input_path):
        logger.error(f"입력 경로가 존재하지 않습니다: {input_path}")
        sys.exit(1)

    if os.path.isfile(input_path):
        # 영상 파일
        ext = os.path.splitext(input_path)[1].lower()
        video_exts = [".mp4", ".mov", ".avi", ".mkv", ".webm"]
        if ext in video_exts:
            logger.info(f"영상 파일 모드: {input_path}")
            count = extract_from_video(input_path, output_path, args.max_frames, args.min_blur_score)
        else:
            logger.error(f"지원하지 않는 파일 형식입니다: {ext}")
            sys.exit(1)
    elif os.path.isdir(input_path):
        # 이미지 폴더
        logger.info(f"이미지 폴더 모드: {input_path}")
        count = extract_from_images(input_path, output_path, args.max_frames, args.min_blur_score)
    else:
        logger.error(f"올바르지 않은 입력 경로입니다: {input_path}")
        sys.exit(1)

    logger.info(f"완료! {count}개 프레임이 {output_path}에 저장되었습니다.")


if __name__ == "__main__":
    main()
