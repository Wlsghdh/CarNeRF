#!/usr/bin/env python3
"""
FastGS (CVPR 2026) 학습 실행 래퍼 스크립트
- third_party/FastGS/train.py 호출
- 별도 conda env(fastgs, py3.7/torch1.12/cu11.6)에서 실행
"""

import argparse
import os
import shutil
import subprocess
import sys
import logging

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FASTGS_REPO_PATH = os.path.join(PROJECT_ROOT, "third_party", "FastGS")
FASTGS_ENV_NAME = "fastgs"
FASTGS_PYTHON_CANDIDATES = [
    f"/home/{os.environ.get('USER', 'jjh0709')}/.conda/envs/{FASTGS_ENV_NAME}/bin/python",
    f"/opt/miniconda3/envs/{FASTGS_ENV_NAME}/bin/python",
]


def find_fastgs_python() -> str:
    """fastgs conda env 의 python 실행 파일을 찾는다."""
    for p in FASTGS_PYTHON_CANDIDATES:
        if os.path.exists(p):
            return p
    bin_path = shutil.which("conda")
    if bin_path:
        return f"conda run -n {FASTGS_ENV_NAME} python"
    logger.error(
        f"fastgs conda env 를 찾을 수 없습니다.\n"
        f"  다음 명령으로 빌드하세요:\n"
        f"  cd {FASTGS_REPO_PATH} && conda env create -f environment.yml"
    )
    sys.exit(1)


def check_fastgs_repo():
    train_script = os.path.join(FASTGS_REPO_PATH, "train.py")
    if not os.path.exists(train_script):
        logger.error(
            f"FastGS 리포가 없습니다: {FASTGS_REPO_PATH}\n"
            f"  git clone --recursive https://github.com/fastgs/FastGS.git {FASTGS_REPO_PATH}"
        )
        sys.exit(1)


def check_source_path(source_path: str) -> str:
    """COLMAP 결과 경로 정규화 (train_gaussian.py 와 동일 규칙)."""
    if not os.path.exists(source_path):
        logger.error(f"소스 경로가 존재하지 않습니다: {source_path}")
        sys.exit(1)

    if os.path.exists(os.path.join(source_path, "sparse")) and os.path.exists(os.path.join(source_path, "images")):
        return source_path

    dense_path = os.path.join(source_path, "dense")
    if (
        os.path.exists(dense_path)
        and os.path.exists(os.path.join(dense_path, "sparse"))
        and os.path.exists(os.path.join(dense_path, "images"))
    ):
        return dense_path

    logger.warning(f"소스 경로에 sparse/ 또는 images/ 가 없을 수 있습니다: {source_path}")
    return source_path


def train(source_path: str, output_path: str, iterations: int, extra_args: list = None):
    python_exec = find_fastgs_python()
    train_script = os.path.join(FASTGS_REPO_PATH, "train.py")

    cmd_prefix = python_exec.split() if " " in python_exec else [python_exec]
    cmd = cmd_prefix + [
        train_script,
        "--source_path", source_path,
        "--model_path", output_path,
        "--iterations", str(iterations),
        "--save_iterations", str(iterations),
    ]
    if extra_args:
        cmd.extend(extra_args)

    logger.info("=" * 60)
    logger.info("FastGS 학습 시작")
    logger.info(f"  소스: {source_path}")
    logger.info(f"  출력: {output_path}")
    logger.info(f"  반복: {iterations}")
    logger.info(f"  cmd : {' '.join(cmd)}")
    logger.info("=" * 60)

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=FASTGS_REPO_PATH)
    for line in process.stdout:
        print(line, end="")
    process.wait()

    if process.returncode != 0:
        logger.error(f"FastGS 학습 실패 (return code: {process.returncode})")
        sys.exit(1)

    ply_path = os.path.join(output_path, "point_cloud", f"iteration_{iterations}", "point_cloud.ply")
    if os.path.exists(ply_path):
        size_mb = os.path.getsize(ply_path) / (1024 * 1024)
        logger.info(f"FastGS 학습 완료: {ply_path} ({size_mb:.1f} MB)")
    else:
        logger.warning(f"PLY 파일을 찾을 수 없습니다: {ply_path}")
    return ply_path


def main():
    parser = argparse.ArgumentParser(description="FastGS 학습 (CVPR 2026)")
    parser.add_argument("--source_path", required=True, help="COLMAP 결과 경로 (dense)")
    parser.add_argument("--output_path", required=True, help="학습 결과 저장 경로")
    parser.add_argument("--iterations", type=int, default=30000, help="학습 iteration (FastGS 기본 30000)")

    # FastGS 핵심 가속 인자
    parser.add_argument("--grad_abs_thresh", type=float, default=0.0009, help="FastGS gaussian score threshold (작을수록 densify 적극)")
    parser.add_argument("--densification_interval", type=int, default=500, help="densification 간격 (base=500, big=100)")
    parser.add_argument("--mult", type=float, default=0.7, help="FastGS rendering multiplier (외부 장면 0.7 권장)")
    parser.add_argument("--highfeature_lr", type=float, default=0.0, help="high-frequency feature LR (0이면 미사용)")
    parser.add_argument("--lowfeature_lr", type=float, default=0.0, help="low-frequency feature LR (0이면 미사용)")
    parser.add_argument("--dense", type=float, default=0.0, help="dense 비율 (0이면 미사용)")
    parser.add_argument("--loss_thresh", type=float, default=0.0, help="loss threshold (0이면 미사용)")

    # vanilla 호환 pass-through
    parser.add_argument("--images", type=str, default="")
    parser.add_argument("--white_background", action="store_true")
    parser.add_argument("--antialiasing", action="store_true")
    parser.add_argument("--optimizer_type", type=str, default="default")
    parser.add_argument("--test_iterations", type=int, nargs="+", default=[])
    parser.add_argument("--save_iterations", type=int, nargs="+", default=[])
    parser.add_argument("--eval", action="store_true")
    args = parser.parse_args()

    source_path = os.path.abspath(args.source_path)
    output_path = os.path.abspath(args.output_path)
    os.makedirs(output_path, exist_ok=True)

    check_fastgs_repo()
    actual_source = check_source_path(source_path)

    extra = []
    if args.images:
        extra.extend(["--images", args.images])
    if args.white_background:
        extra.append("--white_background")
    if args.antialiasing:
        extra.append("--antialiasing")
    if args.eval:
        extra.append("--eval")
    extra.extend(["--optimizer_type", args.optimizer_type])
    extra.extend(["--densification_interval", str(args.densification_interval)])
    extra.extend(["--grad_abs_thresh", str(args.grad_abs_thresh)])
    extra.extend(["--mult", str(args.mult)])
    if args.highfeature_lr > 0:
        extra.extend(["--highfeature_lr", str(args.highfeature_lr)])
    if args.lowfeature_lr > 0:
        extra.extend(["--lowfeature_lr", str(args.lowfeature_lr)])
    if args.dense > 0:
        extra.extend(["--dense", str(args.dense)])
    if args.loss_thresh > 0:
        extra.extend(["--loss_thresh", str(args.loss_thresh)])
    if args.test_iterations:
        extra.extend(["--test_iterations"] + [str(i) for i in args.test_iterations])
    if args.save_iterations:
        extra.extend(["--save_iterations"] + [str(i) for i in args.save_iterations])

    train(actual_source, output_path, args.iterations, extra_args=extra)


if __name__ == "__main__":
    main()
