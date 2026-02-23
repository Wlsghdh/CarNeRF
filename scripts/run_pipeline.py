#!/usr/bin/env python3
"""
CarNeRF 전체 파이프라인 통합 실행 스크립트
영상/이미지 → 프레임 추출 → COLMAP → Gaussian Splatting 학습 → 웹 뷰어용 Export
"""

import argparse
import os
import sys
import time
import subprocess
import logging

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))


def run_step(step_name: str, cmd: list) -> bool:
    """파이프라인의 한 단계를 실행하고 성공 여부를 반환한다."""
    logger.info("")
    logger.info("=" * 70)
    logger.info(f"  단계: {step_name}")
    logger.info("=" * 70)

    start = time.time()

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    for line in process.stdout:
        print(line, end="")

    process.wait()
    elapsed = time.time() - start

    if process.returncode != 0:
        logger.error(f"[실패] {step_name} (소요: {elapsed:.1f}초)")
        return False

    logger.info(f"[성공] {step_name} (소요: {elapsed:.1f}초)")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="CarNeRF 전체 파이프라인 실행",
        epilog="사용 예: python run_pipeline.py --input /path/to/video.mp4 --name my_car",
    )
    parser.add_argument("--input", required=True, help="영상 파일 또는 이미지 폴더 경로")
    parser.add_argument("--name", required=True, help="프로젝트 이름 (결과 폴더명으로 사용)")
    parser.add_argument("--max_frames", type=int, default=80, help="최대 프레임 수 (기본값: 80)")
    parser.add_argument("--min_blur_score", type=float, default=100.0, help="최소 블러 점수 (기본값: 100)")
    parser.add_argument("--iterations", type=int, default=7000, help="Gaussian Splatting 학습 반복 횟수 (기본값: 7000)")
    parser.add_argument("--max_gaussians", type=int, default=1_000_000, help="최대 가우시안 수 (기본값: 1,000,000)")
    parser.add_argument("--hq", action="store_true", help="HQ 모드: 배경 제거 + depth + 최적 파라미터")
    args = parser.parse_args()

    # HQ 모드 기본값 오버라이드
    if args.hq:
        if args.max_frames == 80:
            args.max_frames = 200
        if args.iterations == 7000:
            args.iterations = 60000
        if args.max_gaussians == 1_000_000:
            args.max_gaussians = 2_000_000

    input_path = os.path.abspath(args.input)
    if not os.path.exists(input_path):
        logger.error(f"입력 경로가 존재하지 않습니다: {input_path}")
        sys.exit(1)

    # 경로 설정
    data_dir = os.path.join(PROJECT_ROOT, "data")
    frames_dir = os.path.join(data_dir, "frames", args.name)
    colmap_dir = os.path.join(data_dir, "colmap_output", args.name)
    gaussian_dir = os.path.join(data_dir, "gaussian_output", args.name)
    export_dir = os.path.join(PROJECT_ROOT, "backend", "app", "static", "models", args.name)

    pipeline_start = time.time()

    logger.info("")
    logger.info("*" * 70)
    logger.info("  CarNeRF 파이프라인 시작")
    logger.info(f"  입력: {input_path}")
    logger.info(f"  프로젝트: {args.name}")
    logger.info("*" * 70)

    # 1단계: 프레임 추출
    success = run_step("프레임 추출", [
        sys.executable, os.path.join(SCRIPTS_DIR, "extract_frames.py"),
        "--input", input_path,
        "--output", frames_dir,
        "--max_frames", str(args.max_frames),
        "--min_blur_score", str(args.min_blur_score),
    ])
    if not success:
        logger.error("프레임 추출에 실패했습니다. 파이프라인을 중단합니다.")
        sys.exit(1)

    # 2단계: COLMAP
    success = run_step("COLMAP SfM", [
        sys.executable, os.path.join(SCRIPTS_DIR, "run_colmap.py"),
        "--image_path", frames_dir,
        "--output_path", colmap_dir,
    ])
    if not success:
        logger.error("COLMAP에 실패했습니다. 파이프라인을 중단합니다.")
        sys.exit(1)

    # 3단계: Gaussian Splatting 학습
    # COLMAP dense 결과 경로를 소스로 사용
    colmap_dense_dir = os.path.join(colmap_dir, "dense")
    if not os.path.exists(colmap_dense_dir):
        colmap_dense_dir = colmap_dir

    # HQ 모드: 배경 제거 + depth map 생성
    gs_extra_args = []
    if args.hq:
        # 2a: 배경 제거
        images_masked_dir = os.path.join(colmap_dense_dir, "images_masked")
        success = run_step("배경 제거 (rembg)", [
            sys.executable, os.path.join(SCRIPTS_DIR, "remove_background.py"),
            "--input_dir", os.path.join(colmap_dense_dir, "images"),
            "--output_dir", images_masked_dir,
        ])
        if success:
            gs_extra_args.extend(["--images", "images_masked"])
        else:
            logger.warning("배경 제거 실패. 원본 이미지로 진행합니다.")

        # 2b: Depth map 생성
        success = run_step("Depth map 생성", [
            sys.executable, os.path.join(SCRIPTS_DIR, "generate_depths.py"),
            "--source_path", colmap_dense_dir,
        ])
        if success:
            gs_extra_args.extend(["--depths", "depths"])
        else:
            logger.warning("Depth map 생성 실패. depth 없이 진행합니다.")

        # HQ 최적 파라미터
        gs_extra_args.extend([
            "--antialiasing",
            "--densify_grad_threshold", "0.00007",
            "--densify_until_iter", "35000",
            "--opacity_reset_interval", "3000",
            "--lambda_dssim", "0.2",
            "--position_lr_max_steps", str(args.iterations),
            "--disable_viewer",
        ])

    train_cmd = [
        sys.executable, os.path.join(SCRIPTS_DIR, "train_gaussian.py"),
        "--source_path", colmap_dense_dir,
        "--output_path", gaussian_dir,
        "--iterations", str(args.iterations),
    ] + gs_extra_args

    success = run_step("Gaussian Splatting 학습", train_cmd)
    if not success:
        logger.error("Gaussian Splatting 학습에 실패했습니다. 파이프라인을 중단합니다.")
        sys.exit(1)

    # 4단계: 모델 Export
    ply_path = os.path.join(
        gaussian_dir, "point_cloud", f"iteration_{args.iterations}", "point_cloud.ply"
    )
    if not os.path.exists(ply_path):
        logger.error(f"학습 결과 PLY 파일을 찾을 수 없습니다: {ply_path}")
        sys.exit(1)

    export_cmd = [
        sys.executable, os.path.join(SCRIPTS_DIR, "export_model.py"),
        "--input", ply_path,
        "--output", export_dir,
        "--format", "both",
        "--max_gaussians", str(args.max_gaussians),
    ]
    if args.hq:
        export_cmd.extend(["--max_scale_factor", "10.0", "--max_aspect_ratio", "50"])
    success = run_step("모델 Export", export_cmd)
    if not success:
        logger.error("모델 Export에 실패했습니다. 파이프라인을 중단합니다.")
        sys.exit(1)

    # 완료
    total_time = time.time() - pipeline_start
    minutes = int(total_time // 60)
    seconds = int(total_time % 60)

    logger.info("")
    logger.info("*" * 70)
    logger.info("  CarNeRF 파이프라인 완료!")
    logger.info(f"  총 소요 시간: {minutes}분 {seconds}초")
    logger.info("")
    logger.info("  결과 파일:")
    logger.info(f"    프레임:     {frames_dir}")
    logger.info(f"    COLMAP:     {colmap_dir}")
    logger.info(f"    학습 결과:  {gaussian_dir}")
    logger.info(f"    웹 뷰어용:  {export_dir}")
    logger.info("")
    logger.info("  웹 서버 실행:")
    logger.info(f"    cd {os.path.join(PROJECT_ROOT, 'backend')} && python run.py")
    logger.info(f"    브라우저에서 http://localhost:8000 접속")
    logger.info("*" * 70)


if __name__ == "__main__":
    main()
