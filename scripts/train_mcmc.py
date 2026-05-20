#!/usr/bin/env python3
"""
3DGS-MCMC 학습 래퍼 스크립트
- 기존 train_gaussian.py와 동일한 인터페이스
- third_party/3dgs-mcmc의 train.py를 호출

사용법:
    CUDA_VISIBLE_DEVICES=0 python scripts/train_mcmc.py \
        --source_path data/colmap_output/nf_sonata_hq/dense \
        --output_path data/gaussian_output/nf_sonata_mcmc \
        --config third_party/3dgs-mcmc/configs/car_hq.json

빌드 (최초 1회):
    cd third_party/3dgs-mcmc
    pip install submodules/diff-gaussian-rasterization
    pip install submodules/simple-knn
"""
import argparse, os, sys, subprocess, logging

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MCMC_PATH = os.path.join(PROJECT_ROOT, "third_party", "3dgs-mcmc")


def check_mcmc():
    train_script = os.path.join(MCMC_PATH, "train.py")
    if not os.path.exists(train_script):
        logger.error(f"3DGS-MCMC not found: {MCMC_PATH}")
        sys.exit(1)
    # Check if diff-gaussian-rasterization (MCMC fork) is installed
    try:
        import diff_gaussian_rasterization
        if not hasattr(diff_gaussian_rasterization, 'compute_relocation'):
            logger.warning("diff-gaussian-rasterization installed but missing compute_relocation.")
            logger.warning("Need to rebuild MCMC version:")
            logger.warning(f"  cd {MCMC_PATH} && pip install submodules/diff-gaussian-rasterization")
            return False
    except ImportError:
        logger.warning("diff-gaussian-rasterization not installed.")
        logger.warning(f"Build: cd {MCMC_PATH} && pip install submodules/diff-gaussian-rasterization submodules/simple-knn")
        return False
    return True


def main():
    parser = argparse.ArgumentParser(description="3DGS-MCMC Training")
    parser.add_argument("--source_path", required=True)
    parser.add_argument("--output_path", required=True)
    parser.add_argument("--config", default=os.path.join(MCMC_PATH, "configs", "car_hq.json"))
    parser.add_argument("--cap_max", type=int, default=3000000)
    parser.add_argument("--iterations", type=int, default=100000)
    parser.add_argument("--images", type=str, default="images_masked")
    parser.add_argument("--lambda_dssim", type=float, default=0.15)
    parser.add_argument("--test_iterations", nargs="+", type=int, default=[7000, 30000])
    parser.add_argument("--save_iterations", nargs="+", type=int, default=[])
    parser.add_argument("--build", action="store_true", help="Build MCMC CUDA extensions first")
    args = parser.parse_args()

    source = os.path.abspath(args.source_path)
    output = os.path.abspath(args.output_path)

    # Auto-detect dense subfolder
    if os.path.isdir(os.path.join(source, "dense")):
        source = os.path.join(source, "dense")

    if args.build:
        logger.info("Building MCMC CUDA extensions...")
        env = os.environ.copy()
        env["CUDA_HOME"] = "/usr/local/cuda-12.2"
        for sub in ["diff-gaussian-rasterization", "simple-knn"]:
            sub_path = os.path.join(MCMC_PATH, "submodules", sub)
            subprocess.run([sys.executable, "-m", "pip", "install", sub_path], env=env, check=True)
        logger.info("Build complete.")
        return

    if not check_mcmc():
        logger.error("Run with --build first to install CUDA extensions")
        sys.exit(1)

    cmd = [
        sys.executable, os.path.join(MCMC_PATH, "train.py"),
        "-s", source,
        "-m", output,
        "--cap_max", str(args.cap_max),
        "--iterations", str(args.iterations),
        "--position_lr_max_steps", str(args.iterations),
        "--lambda_dssim", str(args.lambda_dssim),
        "--test_iterations", *[str(i) for i in args.test_iterations], str(args.iterations),
        "--save_iterations", *[str(i) for i in args.save_iterations], str(args.iterations),
    ]
    if args.images:
        cmd.extend(["--images", args.images])
    if args.config and os.path.exists(args.config):
        cmd.extend(["--config", args.config])

    env = os.environ.copy()
    env["CUDA_HOME"] = "/usr/local/cuda-12.2"

    logger.info("=" * 60)
    logger.info("3DGS-MCMC Training")
    logger.info(f"  Source:     {source}")
    logger.info(f"  Output:     {output}")
    logger.info(f"  Cap Max:    {args.cap_max}")
    logger.info(f"  Iterations: {args.iterations}")
    logger.info(f"  Images:     {args.images}")
    logger.info("=" * 60)

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env, cwd=MCMC_PATH)
    for line in proc.stdout:
        print(line, end="")
    proc.wait()

    if proc.returncode != 0:
        logger.error(f"Training failed (rc={proc.returncode})")
        sys.exit(1)

    ply = os.path.join(output, "point_cloud", f"iteration_{args.iterations}", "point_cloud.ply")
    if os.path.exists(ply):
        sz = os.path.getsize(ply) / (1024*1024)
        logger.info(f"Done! PLY: {ply} ({sz:.1f}MB)")


if __name__ == "__main__":
    main()
