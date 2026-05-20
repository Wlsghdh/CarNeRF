#!/usr/bin/env python3
"""
2D Gaussian Splatting 학습 래퍼 스크립트
- 차량 표면 재구성에 특화된 surfel 기반 2DGS
- normal/distance regularization으로 깨끗한 표면 생성
"""

import argparse
import os
import sys
import subprocess
import logging

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GS2D_REPO = os.path.join(PROJECT_ROOT, "third_party", "2d-gaussian-splatting")


def main():
    parser = argparse.ArgumentParser(description="2D Gaussian Splatting 학습")
    parser.add_argument("--source_path", required=True, help="COLMAP dense 경로")
    parser.add_argument("--output_path", required=True, help="출력 경로")
    parser.add_argument("--iterations", type=int, default=60000)
    parser.add_argument("--images", type=str, default="", help="이미지 폴더명")
    parser.add_argument("--lambda_dssim", type=float, default=0.2)
    parser.add_argument("--lambda_normal", type=float, default=0.05, help="Normal regularization (>7K iter)")
    parser.add_argument("--lambda_dist", type=float, default=0.1, help="Distance regularization (>3K iter)")
    parser.add_argument("--densify_grad_threshold", type=float, default=0.00007)
    parser.add_argument("--densify_until_iter", type=int, default=35000)
    parser.add_argument("--opacity_reset_interval", type=int, default=3000)
    parser.add_argument("--antialiasing", action="store_true")
    parser.add_argument("--disable_viewer", action="store_true", default=True)
    args = parser.parse_args()

    train_script = os.path.join(GS2D_REPO, "train.py")
    if not os.path.exists(train_script):
        logger.error(f"2DGS 리포가 없습니다: {GS2D_REPO}")
        sys.exit(1)

    source = os.path.abspath(args.source_path)
    output = os.path.abspath(args.output_path)

    # dense 구조 확인
    if os.path.isdir(os.path.join(source, "dense")):
        source = os.path.join(source, "dense")

    os.makedirs(output, exist_ok=True)

    cmd = [
        sys.executable, train_script,
        "--source_path", source,
        "--model_path", output,
        "--iterations", str(args.iterations),
        "--lambda_dssim", str(args.lambda_dssim),
        "--lambda_normal", str(args.lambda_normal),
        "--lambda_dist", str(args.lambda_dist),
        "--densify_grad_threshold", str(args.densify_grad_threshold),
        "--densify_until_iter", str(args.densify_until_iter),
        "--opacity_reset_interval", str(args.opacity_reset_interval),
        "--test_iterations", "7000", "30000", str(args.iterations),
        "--save_iterations", str(args.iterations),
    ]

    if args.images:
        cmd.extend(["--images", args.images])
    # 2DGS는 --disable_viewer 대신 --quiet 사용
    if args.disable_viewer:
        cmd.append("--quiet")

    logger.info("=" * 60)
    logger.info("2D Gaussian Splatting 학습 시작")
    logger.info(f"  소스: {source}")
    logger.info(f"  출력: {output}")
    logger.info(f"  반복: {args.iterations}")
    logger.info(f"  lambda_normal: {args.lambda_normal}")
    logger.info(f"  lambda_dist: {args.lambda_dist}")
    logger.info("=" * 60)

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=GS2D_REPO,
    )

    for line in process.stdout:
        print(line, end="")

    process.wait()

    if process.returncode != 0:
        logger.error(f"2DGS 학습 실패! (return code: {process.returncode})")
        sys.exit(1)

    ply_path = os.path.join(output, "point_cloud", f"iteration_{args.iterations}", "point_cloud.ply")
    if os.path.exists(ply_path):
        file_mb = os.path.getsize(ply_path) / (1024 * 1024)
        logger.info(f"학습 완료! PLY: {ply_path} ({file_mb:.1f}MB)")
    else:
        logger.warning(f"PLY를 찾을 수 없음: {ply_path}")


if __name__ == "__main__":
    main()
