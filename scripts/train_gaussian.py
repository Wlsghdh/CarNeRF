#!/usr/bin/env python3
"""
3D Gaussian Splatting 학습 실행 래퍼 스크립트
- 공식 리포의 train.py를 호출
- 학습 진행률 출력
"""

import argparse
import os
import sys
import subprocess
import logging

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# 프로젝트 루트 경로
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GS_REPO_PATH = os.path.join(PROJECT_ROOT, "third_party", "gaussian-splatting")


def check_gaussian_splatting():
    """Gaussian Splatting 리포가 클론되어 있는지 확인한다."""
    train_script = os.path.join(GS_REPO_PATH, "train.py")
    if not os.path.exists(train_script):
        logger.error(
            f"3D Gaussian Splatting 리포가 없습니다.\n"
            f"  예상 경로: {GS_REPO_PATH}\n"
            f"  setup_env.sh를 실행하거나, 다음 명령으로 클론하세요:\n"
            f"  git clone https://github.com/graphdeco-inria/gaussian-splatting.git {GS_REPO_PATH}\n"
            f"  cd {GS_REPO_PATH} && pip install -e ."
        )
        sys.exit(1)
    logger.info(f"Gaussian Splatting 리포 확인: {GS_REPO_PATH}")


def check_source_path(source_path: str):
    """COLMAP 결과 경로가 올바른 구조인지 확인한다."""
    # Gaussian Splatting은 다음 구조를 기대:
    # source_path/
    #   sparse/0/  (또는 sparse/)
    #   images/
    sparse_dir = os.path.join(source_path, "sparse")
    images_dir = os.path.join(source_path, "images")

    if not os.path.exists(source_path):
        logger.error(f"소스 경로가 존재하지 않습니다: {source_path}")
        sys.exit(1)

    # dense 폴더 구조인 경우 (COLMAP image_undistorter 결과)
    dense_sparse = os.path.join(source_path, "sparse")
    dense_images = os.path.join(source_path, "images")

    if os.path.exists(dense_sparse) and os.path.exists(dense_images):
        logger.info("COLMAP dense 구조 감지")
        return source_path

    # colmap_output 전체 경로인 경우 - dense 하위 폴더 확인
    dense_path = os.path.join(source_path, "dense")
    if os.path.exists(dense_path):
        dense_sparse = os.path.join(dense_path, "sparse")
        dense_images = os.path.join(dense_path, "images")
        if os.path.exists(dense_sparse) and os.path.exists(dense_images):
            logger.info(f"dense 하위 폴더 사용: {dense_path}")
            return dense_path

    logger.warning(
        f"소스 경로에 sparse/ 또는 images/ 폴더가 없을 수 있습니다.\n"
        f"  경로: {source_path}\n"
        f"  Gaussian Splatting이 올바르게 작동하지 않을 수 있습니다."
    )
    return source_path


def train(source_path: str, output_path: str, iterations: int, extra_args: list = None):
    """Gaussian Splatting 학습을 실행한다."""
    train_script = os.path.join(GS_REPO_PATH, "train.py")

    cmd = [
        sys.executable, train_script,
        "--source_path", source_path,
        "--model_path", output_path,
        "--iterations", str(iterations),
    ]

    if extra_args:
        cmd.extend(extra_args)

    logger.info("=" * 60)
    logger.info("3D Gaussian Splatting 학습 시작")
    logger.info(f"  소스 경로: {source_path}")
    logger.info(f"  출력 경로: {output_path}")
    logger.info(f"  반복 횟수: {iterations}")
    if extra_args:
        logger.info(f"  추가 인자: {' '.join(extra_args)}")
    logger.info("=" * 60)

    # 실시간 출력을 위해 Popen 사용
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=GS_REPO_PATH,
    )

    for line in process.stdout:
        print(line, end="")

    process.wait()

    if process.returncode != 0:
        logger.error(f"학습 실패! (return code: {process.returncode})")
        sys.exit(1)

    # 결과 확인
    ply_path = os.path.join(output_path, "point_cloud", f"iteration_{iterations}", "point_cloud.ply")
    if os.path.exists(ply_path):
        file_size_mb = os.path.getsize(ply_path) / (1024 * 1024)
        logger.info("=" * 60)
        logger.info("학습 완료!")
        logger.info(f"  결과 PLY 파일: {ply_path}")
        logger.info(f"  파일 크기: {file_size_mb:.1f} MB")
        logger.info("=" * 60)
    else:
        logger.warning(f"PLY 파일을 찾을 수 없습니다: {ply_path}")
        logger.warning("학습은 완료되었지만 결과 파일 위치를 확인해 주세요.")

    return ply_path


def main():
    parser = argparse.ArgumentParser(description="3D Gaussian Splatting 학습")
    parser.add_argument("--source_path", required=True, help="COLMAP 결과 경로 (dense 폴더)")
    parser.add_argument("--output_path", required=True, help="학습 결과 저장 경로")
    parser.add_argument("--iterations", type=int, default=7000, help="학습 반복 횟수 (기본값: 7000)")

    # GS train.py pass-through 인자
    parser.add_argument("--images", type=str, default="", help="이미지 폴더명 (기본값: images)")
    parser.add_argument("--depths", type=str, default="", help="depth 폴더명 (비어있으면 미사용)")
    parser.add_argument("--antialiasing", action="store_true", help="anti-aliasing 활성화")
    parser.add_argument("--white_background", action="store_true", help="흰색 배경 사용")
    parser.add_argument("--densify_grad_threshold", type=float, default=0, help="densification gradient threshold")
    parser.add_argument("--densify_until_iter", type=int, default=0, help="densification 종료 iteration")
    parser.add_argument("--opacity_reset_interval", type=int, default=0, help="opacity 리셋 간격")
    parser.add_argument("--lambda_dssim", type=float, default=0, help="DSSIM loss 가중치")
    parser.add_argument("--position_lr_max_steps", type=int, default=0, help="position LR max steps")
    parser.add_argument("--test_iterations", type=int, nargs="+", default=[], help="테스트 iteration 목록")
    parser.add_argument("--save_iterations", type=int, nargs="+", default=[], help="저장 iteration 목록")
    parser.add_argument("--disable_viewer", action="store_true", help="뷰어 비활성화")
    parser.add_argument("--optimizer_type", type=str, default="", help="옵티마이저 타입 (default/sparse_adam)")
    args = parser.parse_args()

    source_path = os.path.abspath(args.source_path)
    output_path = os.path.abspath(args.output_path)

    check_gaussian_splatting()
    actual_source = check_source_path(source_path)
    os.makedirs(output_path, exist_ok=True)

    # extra_args 빌드
    extra_args = []
    if args.images:
        extra_args.extend(["--images", args.images])
    if args.depths:
        extra_args.extend(["--depths", args.depths])
    if args.antialiasing:
        extra_args.append("--antialiasing")
    if args.white_background:
        extra_args.append("--white_background")
    if args.densify_grad_threshold > 0:
        extra_args.extend(["--densify_grad_threshold", str(args.densify_grad_threshold)])
    if args.densify_until_iter > 0:
        extra_args.extend(["--densify_until_iter", str(args.densify_until_iter)])
    if args.opacity_reset_interval > 0:
        extra_args.extend(["--opacity_reset_interval", str(args.opacity_reset_interval)])
    if args.lambda_dssim > 0:
        extra_args.extend(["--lambda_dssim", str(args.lambda_dssim)])
    if args.position_lr_max_steps > 0:
        extra_args.extend(["--position_lr_max_steps", str(args.position_lr_max_steps)])
    if args.test_iterations:
        extra_args.extend(["--test_iterations"] + [str(i) for i in args.test_iterations])
    if args.save_iterations:
        extra_args.extend(["--save_iterations"] + [str(i) for i in args.save_iterations])
    if args.disable_viewer:
        extra_args.append("--disable_viewer")
    if args.optimizer_type:
        extra_args.extend(["--optimizer_type", args.optimizer_type])

    train(actual_source, output_path, args.iterations, extra_args=extra_args or None)


if __name__ == "__main__":
    main()
