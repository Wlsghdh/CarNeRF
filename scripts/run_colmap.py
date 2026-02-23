#!/usr/bin/env python3
"""
COLMAP SfM 자동 실행 스크립트 (pycolmap 3.13 API 사용)
- Feature Extraction → Matching → Sparse Reconstruction → Undistortion
- colmap CLI 없이 Python API로 직접 실행
"""

import argparse
import os
import sys
import logging

# pycolmap + OpenBLAS segfault 방지 (반드시 pycolmap import 전에 설정)
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

import pycolmap

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def run_colmap_pipeline(image_path: str, output_path: str):
    """pycolmap API로 COLMAP SfM 파이프라인을 실행한다."""
    database_path = os.path.join(output_path, "database.db")
    sparse_path = os.path.join(output_path, "sparse")

    os.makedirs(sparse_path, exist_ok=True)

    # 이전 실행 잔여 DB 제거
    if os.path.exists(database_path):
        os.remove(database_path)

    # 이미지 수 확인
    image_count = len([
        f for f in os.listdir(image_path)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ])
    logger.info(f"입력 이미지 수: {image_count}개")

    if image_count < 3:
        logger.error("최소 3개 이상의 이미지가 필요합니다.")
        sys.exit(1)

    # 1단계: Feature Extraction
    logger.info("[Feature Extraction] 실행 중...")
    pycolmap.extract_features(
        database_path=database_path,
        image_path=image_path,
        camera_mode=pycolmap.CameraMode.SINGLE,
        camera_model="OPENCV",
        device=pycolmap.Device.auto,
    )
    logger.info("[Feature Extraction] 완료")

    # 2단계: Feature Matching (sequential - 영상 프레임에 적합, 메모리 효율적)
    logger.info("[Feature Matching] 실행 중 (sequential)...")
    pycolmap.match_sequential(
        database_path=database_path,
        device=pycolmap.Device.auto,
    )
    logger.info("[Feature Matching] 완료")

    # 3단계: Incremental Mapper (Sparse Reconstruction)
    logger.info("[Sparse Reconstruction] 실행 중...")
    reconstructions = pycolmap.incremental_mapping(
        database_path=database_path,
        image_path=image_path,
        output_path=sparse_path,
    )
    logger.info(f"[Sparse Reconstruction] 완료 - {len(reconstructions)}개 모델 생성")

    # sparse/0 이 존재하는지 확인
    sparse_model_path = os.path.join(sparse_path, "0")
    if not os.path.exists(sparse_model_path):
        logger.error(
            "Sparse reconstruction 결과가 없습니다.\n"
            "가능한 원인:\n"
            "  - 이미지 간 겹치는 영역이 부족\n"
            "  - 이미지 품질이 낮음\n"
            "  - 텍스처가 부족한 장면"
        )
        sys.exit(1)

    # 등록된 이미지 수 확인
    reconstruction = reconstructions[0]
    num_registered = reconstruction.num_reg_images()
    num_points = reconstruction.num_points3D()
    logger.info(f"  등록된 이미지: {num_registered}/{image_count}")
    logger.info(f"  3D 포인트: {num_points:,}개")

    # 4단계: Image Undistortion
    logger.info("[Image Undistortion] 실행 중...")
    dense_path = os.path.join(output_path, "dense")
    os.makedirs(dense_path, exist_ok=True)
    pycolmap.undistort_images(
        output_path=dense_path,
        input_path=sparse_model_path,
        image_path=image_path,
    )
    logger.info("[Image Undistortion] 완료")

    # pycolmap은 dense/sparse/ 에 파일을 놓지만
    # Gaussian Splatting은 dense/sparse/0/ 구조를 기대함 → 호환 심링크 생성
    dense_sparse = os.path.join(dense_path, "sparse")
    dense_sparse_0 = os.path.join(dense_sparse, "0")
    if os.path.isdir(dense_sparse) and not os.path.exists(dense_sparse_0):
        # sparse/ 안에 바로 .bin 파일이 있으면 0/ 서브디렉토리로 감싸기
        has_bin = any(f.endswith(".bin") for f in os.listdir(dense_sparse))
        if has_bin:
            import shutil
            tmp = dense_sparse + "_tmp"
            os.rename(dense_sparse, tmp)
            os.makedirs(dense_sparse_0, exist_ok=True)
            for f in os.listdir(tmp):
                shutil.move(os.path.join(tmp, f), os.path.join(dense_sparse_0, f))
            os.rmdir(tmp)
            logger.info("  dense/sparse/ → dense/sparse/0/ 구조 변환 완료")

    logger.info("=" * 60)
    logger.info("COLMAP 파이프라인 완료!")
    logger.info(f"  Sparse 모델: {sparse_model_path}")
    logger.info(f"  Dense 준비:  {dense_path}")
    logger.info("=" * 60)

    return sparse_model_path


def main():
    parser = argparse.ArgumentParser(description="COLMAP SfM 자동 실행 (pycolmap)")
    parser.add_argument("--image_path", required=True, help="입력 이미지 폴더 경로")
    parser.add_argument("--output_path", required=True, help="COLMAP 결과 저장 경로")
    args = parser.parse_args()

    image_path = os.path.abspath(args.image_path)
    output_path = os.path.abspath(args.output_path)

    if not os.path.isdir(image_path):
        logger.error(f"이미지 경로가 존재하지 않습니다: {image_path}")
        sys.exit(1)

    os.makedirs(output_path, exist_ok=True)
    run_colmap_pipeline(image_path, output_path)


if __name__ == "__main__":
    main()
