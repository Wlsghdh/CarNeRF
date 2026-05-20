#!/usr/bin/env python3
"""
고품질 COLMAP SfM 파이프라인 (pycolmap)
- SIFT max_num_features: 8192 → 16384
- Exhaustive matching (200장 이하 적합)
- Domain Size Pooling (DSP) 활성화 → 더 정확한 feature matching
- 기존 run_colmap.py 대비 더 많은 3D 포인트 생성

사용법:
    OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python scripts/run_colmap_hq.py \
        --image_path data/colmap_output/nf_sonata_hq/dense/images \
        --output_path data/colmap_output/nf_sonata_hq_v2
"""
import argparse, os, sys, logging, shutil

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

import pycolmap

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def run_hq_colmap(image_path: str, output_path: str, use_exhaustive=True, max_features=16384):
    database_path = os.path.join(output_path, "database.db")
    sparse_path = os.path.join(output_path, "sparse")
    os.makedirs(sparse_path, exist_ok=True)

    if os.path.exists(database_path):
        os.remove(database_path)

    image_count = len([f for f in os.listdir(image_path) if f.lower().endswith((".jpg", ".jpeg", ".png"))])
    logger.info(f"Images: {image_count}")

    # HQ Feature Extraction
    extraction_opts = pycolmap.FeatureExtractionOptions()
    extraction_opts.sift.max_num_features = max_features
    extraction_opts.sift.domain_size_pooling = True  # DSP for better descriptors
    extraction_opts.sift.estimate_affine_shape = True  # affine-invariant features

    logger.info(f"[Feature Extraction] max_features={max_features}, DSP=True, affine=True")
    pycolmap.extract_features(
        database_path=database_path,
        image_path=image_path,
        camera_mode=pycolmap.CameraMode.SINGLE,
        camera_model="OPENCV",
        extraction_options=extraction_opts,
        device=pycolmap.Device.auto,
    )
    logger.info("[Feature Extraction] Done")

    # Exhaustive Matching (feasible for <=300 images)
    if use_exhaustive and image_count <= 300:
        logger.info("[Feature Matching] Exhaustive matching...")
        pycolmap.match_exhaustive(database_path=database_path, device=pycolmap.Device.auto)
    else:
        logger.info("[Feature Matching] Sequential matching...")
        pycolmap.match_sequential(database_path=database_path, device=pycolmap.Device.auto)
    logger.info("[Feature Matching] Done")

    # Sparse Reconstruction
    logger.info("[Sparse Reconstruction]...")
    reconstructions = pycolmap.incremental_mapping(
        database_path=database_path,
        image_path=image_path,
        output_path=sparse_path,
    )
    logger.info(f"[Sparse Reconstruction] {len(reconstructions)} model(s)")

    sparse_model_path = os.path.join(sparse_path, "0")
    if not os.path.exists(sparse_model_path):
        logger.error("No reconstruction result!")
        sys.exit(1)

    reconstruction = reconstructions[0]
    logger.info(f"  Registered: {reconstruction.num_reg_images()}/{image_count}")
    logger.info(f"  3D points:  {reconstruction.num_points3D():,}")

    # Undistortion
    logger.info("[Undistortion]...")
    dense_path = os.path.join(output_path, "dense")
    os.makedirs(dense_path, exist_ok=True)
    pycolmap.undistort_images(
        output_path=dense_path,
        input_path=sparse_model_path,
        image_path=image_path,
    )

    # sparse/ → sparse/0/ structure fix
    dense_sparse = os.path.join(dense_path, "sparse")
    dense_sparse_0 = os.path.join(dense_sparse, "0")
    if os.path.isdir(dense_sparse) and not os.path.exists(dense_sparse_0):
        has_bin = any(f.endswith(".bin") for f in os.listdir(dense_sparse))
        if has_bin:
            tmp = dense_sparse + "_tmp"
            os.rename(dense_sparse, tmp)
            os.makedirs(dense_sparse_0, exist_ok=True)
            for f in os.listdir(tmp):
                shutil.move(os.path.join(tmp, f), os.path.join(dense_sparse_0, f))
            os.rmdir(tmp)

    logger.info("=" * 50)
    logger.info("HQ COLMAP Done!")
    logger.info(f"  Dense: {dense_path}")
    logger.info("=" * 50)


def main():
    parser = argparse.ArgumentParser(description="HQ COLMAP SfM")
    parser.add_argument("--image_path", required=True)
    parser.add_argument("--output_path", required=True)
    parser.add_argument("--max_features", type=int, default=16384)
    parser.add_argument("--sequential", action="store_true", help="Use sequential matching instead of exhaustive")
    args = parser.parse_args()

    run_hq_colmap(
        os.path.abspath(args.image_path),
        os.path.abspath(args.output_path),
        use_exhaustive=not args.sequential,
        max_features=args.max_features,
    )


if __name__ == "__main__":
    main()
