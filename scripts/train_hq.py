#!/usr/bin/env python3
"""
CarNeRF HQ 학습 오케스트레이터
배경 제거 → Depth map 생성 → Gaussian Splatting 학습 → Export를 한 번에 실행

사용 예:
    python scripts/train_hq.py \
        --source_path data/colmap_output/nf_sonata_hq/dense \
        --output_path data/gaussian_output/nf_sonata_v2 \
        --iterations 60000
"""

import argparse
import os
import sys
import time
import subprocess
import logging

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))


def run_step(step_name: str, cmd: list) -> bool:
    """파이프라인의 한 단계를 실행하고 성공 여부를 반환한다."""
    logger.info("")
    logger.info("=" * 70)
    logger.info(f"  단계: {step_name}")
    logger.info(f"  명령: {' '.join(cmd)}")
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
        description="CarNeRF HQ 학습 오케스트레이터",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
최적 하이퍼파라미터 (기본값):
  --images images_masked        배경 제거된 RGBA 이미지
  --depths depths               depth regularization
  --antialiasing                앨리어싱 제거
  --iterations 60000            학습 반복 횟수
  --densify_grad_threshold 0.00007  공격적 densification
  --densify_until_iter 35000    densification 기간 연장
  --opacity_reset_interval 3000 안정적 리셋 간격
  --lambda_dssim 0.2            PSNR 최적 가중치
""",
    )
    parser.add_argument("--source_path", required=True, help="COLMAP dense 결과 경로")
    parser.add_argument("--output_path", required=True, help="학습 결과 저장 경로")
    parser.add_argument("--export_path", default="", help="Export 경로 (비어있으면 output_path/export)")
    parser.add_argument("--iterations", type=int, default=60000, help="학습 반복 횟수 (기본값: 60000)")
    parser.add_argument("--max_gaussians", type=int, default=2_000_000, help="최대 가우시안 수 (기본값: 2,000,000)")

    # 개별 단계 스킵
    parser.add_argument("--skip_bg_removal", action="store_true", help="배경 제거 스킵")
    parser.add_argument("--skip_depth", action="store_true", help="depth map 생성 스킵")
    parser.add_argument("--skip_export", action="store_true", help="export 스킵")

    # GS 하이퍼파라미터 오버라이드
    parser.add_argument("--images", type=str, default="images_masked", help="이미지 폴더명")
    parser.add_argument("--depths", type=str, default="depths", help="depth 폴더명 (빈 문자열=미사용)")
    parser.add_argument("--antialiasing", action="store_true", default=True, help="anti-aliasing (기본값: ON)")
    parser.add_argument("--no_antialiasing", action="store_true", help="anti-aliasing 비활성화")
    parser.add_argument("--densify_grad_threshold", type=float, default=0.00007)
    parser.add_argument("--densify_until_iter", type=int, default=35000)
    parser.add_argument("--opacity_reset_interval", type=int, default=3000)
    parser.add_argument("--lambda_dssim", type=float, default=0.2)
    parser.add_argument("--position_lr_max_steps", type=int, default=60000)

    # Export 파라미터
    parser.add_argument("--max_scale_factor", type=float, default=10.0, help="볼륨 pruning 스케일 팩터")
    parser.add_argument("--max_aspect_ratio", type=float, default=50.0, help="볼륨 pruning 종횡비")

    # rembg 모델
    parser.add_argument("--rembg_model", default="u2net", help="rembg 모델명")

    args = parser.parse_args()

    source_path = os.path.abspath(args.source_path)
    output_path = os.path.abspath(args.output_path)
    export_path = os.path.abspath(args.export_path) if args.export_path else os.path.join(output_path, "export")

    if not os.path.isdir(source_path):
        logger.error(f"소스 경로가 존재하지 않습니다: {source_path}")
        sys.exit(1)

    if args.no_antialiasing:
        args.antialiasing = False

    pipeline_start = time.time()

    logger.info("")
    logger.info("*" * 70)
    logger.info("  CarNeRF HQ 학습 파이프라인 시작")
    logger.info(f"  소스: {source_path}")
    logger.info(f"  출력: {output_path}")
    logger.info(f"  반복: {args.iterations}")
    logger.info(f"  이미지: {args.images}")
    logger.info(f"  Depth: {args.depths if args.depths else '(미사용)'}")
    logger.info(f"  Anti-aliasing: {args.antialiasing}")
    logger.info("*" * 70)

    # ─────────────────────────────────────────────────────────────────
    # 1단계: 배경 제거
    # ─────────────────────────────────────────────────────────────────
    images_masked_dir = os.path.join(source_path, "images_masked")

    if not args.skip_bg_removal:
        images_dir = os.path.join(source_path, "images")
        if not os.path.isdir(images_dir):
            logger.error(f"이미지 폴더가 없습니다: {images_dir}")
            sys.exit(1)

        success = run_step("배경 제거 (rembg)", [
            sys.executable, os.path.join(SCRIPTS_DIR, "remove_background.py"),
            "--input_dir", images_dir,
            "--output_dir", images_masked_dir,
            "--model", args.rembg_model,
        ])
        if not success:
            logger.error("배경 제거 실패!")
            sys.exit(1)
    else:
        logger.info("배경 제거 스킵됨")
        if not os.path.isdir(images_masked_dir) and args.images == "images_masked":
            logger.warning(f"images_masked 폴더가 없습니다. --images images 로 대체합니다.")
            args.images = "images"

    # ─────────────────────────────────────────────────────────────────
    # 2단계: Depth map 생성
    # ─────────────────────────────────────────────────────────────────
    depths_dir = os.path.join(source_path, "depths")
    depth_params_file = os.path.join(source_path, "sparse", "0", "depth_params.json")

    if not args.skip_depth:
        success = run_step("Depth map 생성 (Depth Anything V2)", [
            sys.executable, os.path.join(SCRIPTS_DIR, "generate_depths.py"),
            "--source_path", source_path,
        ])
        if not success:
            logger.warning("Depth map 생성 실패! depth regularization 없이 학습합니다.")
            args.depths = ""
    else:
        logger.info("Depth map 생성 스킵됨")
        if not os.path.isdir(depths_dir) and args.depths:
            logger.warning("depths 폴더가 없습니다. depth regularization을 비활성화합니다.")
            args.depths = ""

    # depth_params.json이 없으면 depth 비활성화
    if args.depths and not os.path.exists(depth_params_file):
        logger.warning(f"depth_params.json이 없습니다: {depth_params_file}")
        logger.warning("depth regularization을 비활성화합니다.")
        args.depths = ""

    # ─────────────────────────────────────────────────────────────────
    # 3단계: Gaussian Splatting 학습
    # ─────────────────────────────────────────────────────────────────
    train_cmd = [
        sys.executable, os.path.join(SCRIPTS_DIR, "train_gaussian.py"),
        "--source_path", source_path,
        "--output_path", output_path,
        "--iterations", str(args.iterations),
        "--images", args.images,
        "--densify_grad_threshold", str(args.densify_grad_threshold),
        "--densify_until_iter", str(args.densify_until_iter),
        "--opacity_reset_interval", str(args.opacity_reset_interval),
        "--lambda_dssim", str(args.lambda_dssim),
        "--position_lr_max_steps", str(args.position_lr_max_steps),
        "--test_iterations", "7000", "30000", str(args.iterations),
        "--save_iterations", "7000", "30000", str(args.iterations),
        "--disable_viewer",
    ]

    if args.depths:
        train_cmd.extend(["--depths", args.depths])
    if args.antialiasing:
        train_cmd.append("--antialiasing")

    success = run_step("Gaussian Splatting 학습", train_cmd)
    if not success:
        logger.error("Gaussian Splatting 학습 실패!")
        sys.exit(1)

    # ─────────────────────────────────────────────────────────────────
    # 4단계: 모델 Export
    # ─────────────────────────────────────────────────────────────────
    if not args.skip_export:
        ply_path = os.path.join(
            output_path, "point_cloud", f"iteration_{args.iterations}", "point_cloud.ply"
        )
        if not os.path.exists(ply_path):
            logger.error(f"PLY 파일을 찾을 수 없습니다: {ply_path}")
            sys.exit(1)

        export_cmd = [
            sys.executable, os.path.join(SCRIPTS_DIR, "export_model.py"),
            "--input", ply_path,
            "--output", export_path,
            "--format", "both",
            "--max_gaussians", str(args.max_gaussians),
            "--max_scale_factor", str(args.max_scale_factor),
            "--max_aspect_ratio", str(args.max_aspect_ratio),
        ]

        success = run_step("모델 Export", export_cmd)
        if not success:
            logger.error("모델 Export 실패!")
            sys.exit(1)
    else:
        logger.info("Export 스킵됨")

    # ─────────────────────────────────────────────────────────────────
    # 완료
    # ─────────────────────────────────────────────────────────────────
    total_time = time.time() - pipeline_start
    minutes = int(total_time // 60)
    seconds = int(total_time % 60)

    logger.info("")
    logger.info("*" * 70)
    logger.info("  CarNeRF HQ 학습 파이프라인 완료!")
    logger.info(f"  총 소요 시간: {minutes}분 {seconds}초")
    logger.info("")
    logger.info("  결과:")
    logger.info(f"    배경 제거:    {images_masked_dir}")
    logger.info(f"    Depth maps:   {depths_dir}")
    logger.info(f"    학습 결과:    {output_path}")
    logger.info(f"    Export:       {export_path}")
    logger.info("")
    logger.info("  웹 배포:")
    logger.info(f"    cp {export_path}/model.splat backend/app/static/models/<name>/model.splat")
    logger.info("*" * 70)


if __name__ == "__main__":
    main()
