#!/usr/bin/env python3
"""
Depth Anything V2를 사용한 단안 depth map 생성 + COLMAP sparse point와 스케일 정렬
GS의 depth regularization과 호환되는 형식으로 출력:
  - depths/<image_name>.png  (16-bit inverse depth PNG)
  - sparse/0/depth_params.json  (이미지별 scale/offset)
"""

import argparse
import json
import os
import sys
import time
import logging

import cv2
import numpy as np
import torch

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_colmap_sparse_points(sparse_dir: str):
    """COLMAP sparse/0/points3D.bin에서 3D 포인트를 읽고,
    images.bin에서 각 이미지의 카메라 포즈(R, T)와 2D-3D 매칭을 가져온다.
    반환: {image_name: [(u, v, depth), ...]} — 각 이미지에서 보이는 3D 포인트의 투영 깊이
    """
    try:
        from scene.colmap_loader import (
            read_extrinsics_binary,
            read_intrinsics_binary,
            read_points3D_binary,
        )
    except ImportError:
        # GS 리포가 sys.path에 없으면 추가
        gs_path = os.path.join(PROJECT_ROOT, "third_party", "gaussian-splatting")
        sys.path.insert(0, gs_path)
        from scene.colmap_loader import (
            read_extrinsics_binary,
            read_intrinsics_binary,
            read_points3D_binary,
        )

    images_bin = os.path.join(sparse_dir, "images.bin")
    cameras_bin = os.path.join(sparse_dir, "cameras.bin")
    points3d_bin = os.path.join(sparse_dir, "points3D.bin")

    if not all(os.path.exists(p) for p in [images_bin, cameras_bin, points3d_bin]):
        logger.error(f"COLMAP binary 파일이 없습니다: {sparse_dir}")
        return None, None

    cam_extrinsics = read_extrinsics_binary(images_bin)
    cam_intrinsics = read_intrinsics_binary(cameras_bin)
    points3d = read_points3D_binary(points3d_bin)

    # 각 이미지별 보이는 3D 포인트의 depth 수집
    image_depths = {}
    for key in cam_extrinsics:
        extr = cam_extrinsics[key]
        intr = cam_intrinsics[extr.camera_id]
        name = extr.name

        # R, T (world to camera)
        from scene.colmap_loader import qvec2rotmat
        R = qvec2rotmat(extr.qvec)
        T = np.array(extr.tvec)

        # 이 이미지에 보이는 3D 포인트 ID 수집
        point3d_ids = extr.point3D_ids
        valid_mask = point3d_ids >= 0

        if valid_mask.sum() == 0:
            continue

        valid_ids = point3d_ids[valid_mask]

        depths = []
        for pid in valid_ids:
            if pid in points3d:
                xyz = points3d[pid].xyz
                # world → camera: depth = (R @ xyz + T)[2]
                cam_point = R @ xyz + T
                depth = cam_point[2]
                if depth > 0:
                    depths.append(depth)

        if depths:
            image_depths[name] = np.array(depths)

    return image_depths, cam_extrinsics


def compute_scale_offset(mono_inv_depth: np.ndarray, sparse_depths: np.ndarray,
                          sparse_uvs: np.ndarray, height: int, width: int):
    """단안 inverse depth와 COLMAP sparse depth 사이의 scale/offset을 least squares로 계산.
    mono_inv_depth: (H, W) 모델 출력 (0~1 정규화된 inverse depth)
    sparse_depths: (N,) COLMAP에서 얻은 실제 depth 값들
    반환: scale, offset  (aligned_inv_depth = mono_inv_depth * scale + offset)
    """
    # sparse depth → inverse depth
    sparse_inv_depths = 1.0 / sparse_depths

    # 모노 depth를 sparse point 위치에서 샘플링 — 전체 이미지 median 사용 (간단)
    mono_median = np.median(mono_inv_depth[mono_inv_depth > 0])
    sparse_median = np.median(sparse_inv_depths)

    if mono_median > 0 and sparse_median > 0:
        scale = sparse_median / mono_median
        offset = 0.0
    else:
        scale = 1.0
        offset = 0.0

    return float(scale), float(offset)


def main():
    parser = argparse.ArgumentParser(description="Depth Anything V2로 depth map 생성")
    parser.add_argument("--source_path", required=True, help="COLMAP dense 결과 경로")
    parser.add_argument("--model_name", default="depth-anything/Depth-Anything-V2-Base-hf",
                        help="HuggingFace 모델명")
    parser.add_argument("--device", default="cuda", help="디바이스 (cuda/cpu)")
    args = parser.parse_args()

    source_path = os.path.abspath(args.source_path)
    images_dir = os.path.join(source_path, "images")
    depths_dir = os.path.join(source_path, "depths")
    sparse_dir = os.path.join(source_path, "sparse", "0")
    depth_params_file = os.path.join(sparse_dir, "depth_params.json")

    if not os.path.isdir(images_dir):
        logger.error(f"이미지 폴더가 없습니다: {images_dir}")
        sys.exit(1)

    os.makedirs(depths_dir, exist_ok=True)

    # 이미지 파일 목록
    extensions = {".jpg", ".jpeg", ".png", ".bmp"}
    image_files = sorted([
        f for f in os.listdir(images_dir)
        if os.path.splitext(f)[1].lower() in extensions
    ])
    logger.info(f"이미지 {len(image_files)}개 발견")

    # COLMAP sparse points 로드 (scale alignment용)
    logger.info("COLMAP sparse points 로드 중...")
    image_depths, cam_extrinsics = load_colmap_sparse_points(sparse_dir)
    if image_depths:
        logger.info(f"  {len(image_depths)}개 이미지의 sparse depth 로드됨")
    else:
        logger.warning("COLMAP sparse points를 로드할 수 없습니다. scale=1.0으로 진행합니다.")

    # Depth Anything V2 모델 로드
    logger.info(f"Depth Anything V2 모델 로드 중: {args.model_name}")
    try:
        from transformers import pipeline
        depth_pipe = pipeline(
            "depth-estimation",
            model=args.model_name,
            device=args.device if args.device == "cuda" and torch.cuda.is_available() else "cpu",
        )
    except Exception as e:
        logger.error(f"모델 로드 실패: {e}")
        logger.info("transformers와 torch가 설치되어 있는지 확인하세요.")
        sys.exit(1)

    logger.info("Depth map 생성 시작...")
    start = time.time()
    depth_params = {}

    for idx, fname in enumerate(image_files):
        img_path = os.path.join(images_dir, fname)
        name_no_ext = os.path.splitext(fname)[0]

        # depth 추론
        from PIL import Image
        img = Image.open(img_path).convert("RGB")
        result = depth_pipe(img)
        depth_map = np.array(result["depth"], dtype=np.float32)

        # depth_map을 원본 해상도로 리사이즈 (모델이 다른 해상도로 출력할 수 있음)
        orig_w, orig_h = img.size
        if depth_map.shape[0] != orig_h or depth_map.shape[1] != orig_w:
            depth_map = cv2.resize(depth_map, (orig_w, orig_h), interpolation=cv2.INTER_LINEAR)

        # inverse depth로 변환 (depth → 1/depth)
        # depth_map은 상대적 값이므로 먼저 정규화
        valid_mask = depth_map > 0
        if valid_mask.sum() > 0:
            # 모델 출력을 inverse depth로: 값이 클수록 가까움
            # Depth Anything은 disparity(=inverse depth) 출력
            inv_depth = depth_map.copy()
            inv_depth[~valid_mask] = 0
        else:
            inv_depth = np.zeros_like(depth_map)

        # 16-bit PNG로 저장 (GS가 / 2^16으로 나눔)
        # 정규화: 0~1 → 0~65535
        max_val = inv_depth.max()
        if max_val > 0:
            inv_depth_norm = inv_depth / max_val
        else:
            inv_depth_norm = inv_depth

        inv_depth_16bit = (inv_depth_norm * 65535).astype(np.uint16)
        depth_out_path = os.path.join(depths_dir, f"{name_no_ext}.png")
        cv2.imwrite(depth_out_path, inv_depth_16bit)

        # scale/offset 계산 (COLMAP sparse depth와 정렬)
        scale, offset = 1.0, 0.0
        if image_depths and fname in image_depths:
            sparse_d = image_depths[fname]
            # GS는 16bit로 저장된 것을 / 2^16으로 나눈 후 scale*x + offset을 적용
            # 우리의 정규화: inv_depth_16bit / 65535 = inv_depth / max_val
            # GS 로드: inv_depth_16bit / 65536 ≈ inv_depth / max_val
            # 실제 inverse depth = 1 / depth
            # aligned = (inv_depth_16bit / 65536) * scale + offset ≈ 1/depth (COLMAP 좌표계)
            sparse_inv_d = 1.0 / sparse_d
            median_sparse_inv = np.median(sparse_inv_d)
            median_mono = np.median(inv_depth_norm[inv_depth_norm > 0])

            if median_mono > 0 and median_sparse_inv > 0:
                # GS 로드: val = (pixel / 65536) * scale + offset
                # pixel / 65536 ≈ inv_depth_norm = inv_depth / max_val
                # 목표: inv_depth_norm * scale + offset ≈ sparse_inv_depth
                scale = float(median_sparse_inv / median_mono)
                offset = 0.0

        depth_params[name_no_ext] = {"scale": scale, "offset": offset}

        elapsed = time.time() - start
        avg = elapsed / (idx + 1)
        remaining = avg * (len(image_files) - idx - 1)
        logger.info(
            f"  [{idx+1}/{len(image_files)}] {fname} "
            f"(scale={scale:.4f}, 경과: {elapsed:.0f}s, 남은: {remaining:.0f}s)"
        )

    # depth_params.json 저장
    with open(depth_params_file, "w") as f:
        json.dump(depth_params, f, indent=2)
    logger.info(f"depth_params.json 저장: {depth_params_file}")

    elapsed = time.time() - start
    logger.info(f"Depth map 생성 완료: {len(image_files)}개 ({elapsed:.1f}초)")
    logger.info(f"  depths 폴더: {depths_dir}")


if __name__ == "__main__":
    main()
