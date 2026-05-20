#!/usr/bin/env python3
"""
CarNeRF GS 벤치마크 - 다양한 하이퍼파라미터로 학습 후 PSNR 비교

사용법:
    python scripts/benchmark_gs.py --source_path data/colmap_output/nf_sonata_hq/dense
    python scripts/benchmark_gs.py --source_path data/colmap_output/nf_sonata_hq/dense --configs ultra_v2 best_combo_v2
    python scripts/benchmark_gs.py --list_configs
"""
import argparse, json, os, sys, time, subprocess, re, logging

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))

# ──────────────────────────────────────────────────────────────────────
# 벤치마크 설정 목록
# 현재 최고: PSNR 32.68 (100K, images+depths, default optimizer)
# ──────────────────────────────────────────────────────────────────────
CONFIGS = {
    # ── Baseline 재현 ──
    "baseline_100k": {
        "desc": "Baseline (100K, images+depths, PSNR 32.68 재현)",
        "iterations": 100000,
        "densify_grad_threshold": 0.0002,
        "densify_until_iter": 15000,
        "opacity_reset_interval": 3000,
        "lambda_dssim": 0.2,
        "antialiasing": False,
        "depths": "depths",
    },

    # ── HQ 파라미터 60K ──
    "hq_baseline": {
        "desc": "HQ baseline (60K, grad 0.00007, AA)",
        "iterations": 60000,
        "densify_grad_threshold": 0.00007,
        "densify_until_iter": 35000,
        "opacity_reset_interval": 3000,
        "lambda_dssim": 0.2,
        "antialiasing": True,
        "depths": "depths",
    },

    # ── Aggressive Densification ──
    "aggressive_v2": {
        "desc": "Aggressive densify (0.00004, until 50K, 80K iter)",
        "iterations": 80000,
        "densify_grad_threshold": 0.00004,
        "densify_until_iter": 50000,
        "opacity_reset_interval": 2000,
        "lambda_dssim": 0.2,
        "antialiasing": True,
        "depths": "depths",
    },

    # ── Low DSSIM (PSNR에 유리) ──
    "low_dssim": {
        "desc": "Low SSIM (0.12) for max PSNR",
        "iterations": 80000,
        "densify_grad_threshold": 0.00005,
        "densify_until_iter": 45000,
        "opacity_reset_interval": 2500,
        "lambda_dssim": 0.12,
        "antialiasing": True,
        "depths": "depths",
    },

    # ── Masked Images + Depth (배경 제거) ──
    "masked_depth": {
        "desc": "Masked RGBA + Depth reg (80K)",
        "iterations": 80000,
        "densify_grad_threshold": 0.00005,
        "densify_until_iter": 45000,
        "opacity_reset_interval": 2500,
        "lambda_dssim": 0.2,
        "antialiasing": True,
        "images": "images_masked",
        "depths": "depths",
    },

    # ── Ultra: 모든 최적화 결합 ──
    "ultra_v2": {
        "desc": "Ultra V2 (120K, aggressive, masked+depth, low_dssim)",
        "iterations": 120000,
        "densify_grad_threshold": 0.00003,
        "densify_until_iter": 60000,
        "opacity_reset_interval": 2000,
        "lambda_dssim": 0.15,
        "antialiasing": True,
        "images": "images_masked",
        "depths": "depths",
    },

    # ── Sparse Adam Optimizer ──
    "sparse_adam": {
        "desc": "Sparse Adam optimizer (80K, aggressive)",
        "iterations": 80000,
        "densify_grad_threshold": 0.00005,
        "densify_until_iter": 45000,
        "opacity_reset_interval": 2500,
        "lambda_dssim": 0.2,
        "antialiasing": True,
        "depths": "depths",
        "optimizer_type": "sparse_adam",
    },

    # ── Best Combo V2 (가장 유망) ──
    "best_combo_v2": {
        "desc": "Best V2 (100K, grad=0.00004, dssim=0.15, masked+depth, AA)",
        "iterations": 100000,
        "densify_grad_threshold": 0.00004,
        "densify_until_iter": 55000,
        "opacity_reset_interval": 2000,
        "lambda_dssim": 0.15,
        "antialiasing": True,
        "images": "images_masked",
        "depths": "depths",
    },

    # ── PSNR 34+ Target: 고품질 영상용 ──
    "target_34_v1": {
        "desc": "PSNR 34+ target (150K, ultra-aggressive densify, sparse_adam)",
        "iterations": 150000,
        "densify_grad_threshold": 0.00002,
        "densify_until_iter": 70000,
        "opacity_reset_interval": 2000,
        "lambda_dssim": 0.15,
        "antialiasing": True,
        "images": "images_masked",
        "depths": "depths",
        "optimizer_type": "sparse_adam",
    },

    # ── PSNR 34+ Target V2: 밸런스 ──
    "target_34_v2": {
        "desc": "PSNR 34+ balanced (120K, grad=0.00003, dssim=0.12)",
        "iterations": 120000,
        "densify_grad_threshold": 0.00003,
        "densify_until_iter": 60000,
        "opacity_reset_interval": 2500,
        "lambda_dssim": 0.12,
        "antialiasing": True,
        "images": "images_masked",
        "depths": "depths",
        "optimizer_type": "sparse_adam",
    },

    # ── HQ Video Input: 고해상도 영상 전용 ──
    "hq_video": {
        "desc": "HQ video input (100K, conservative densify, depth+mask)",
        "iterations": 100000,
        "densify_grad_threshold": 0.00005,
        "densify_until_iter": 50000,
        "opacity_reset_interval": 2000,
        "lambda_dssim": 0.15,
        "antialiasing": True,
        "images": "images_masked",
        "depths": "depths",
    },
}


def get_psnr(model_path):
    """Tensorboard에서 최종 PSNR 추출"""
    try:
        from tensorboard.backend.event_processing.event_accumulator import EventAccumulator
        for f in sorted(os.listdir(model_path)):
            if f.startswith("events.out.tfevents"):
                ea = EventAccumulator(os.path.join(model_path, f))
                ea.Reload()
                for tag in ea.Tags().get("scalars", []):
                    if "psnr" in tag.lower():
                        events = ea.Scalars(tag)
                        if events:
                            best = max(events, key=lambda e: e.value)
                            return round(best.value, 2)
    except Exception as e:
        logger.warning(f"PSNR 추출 실패: {e}")
    return None


def run_config(source, output, cfg):
    """한 설정으로 학습"""
    cmd = [
        sys.executable, os.path.join(SCRIPTS_DIR, "train_gaussian.py"),
        "--source_path", source, "--output_path", output,
        "--iterations", str(cfg["iterations"]),
        "--position_lr_max_steps", str(cfg["iterations"]),
        "--test_iterations", "7000", "30000", str(cfg["iterations"]),
        "--save_iterations", str(cfg["iterations"]),
        "--disable_viewer",
    ]
    for k in ["densify_grad_threshold", "densify_until_iter", "opacity_reset_interval", "lambda_dssim"]:
        if k in cfg:
            cmd.extend([f"--{k}", str(cfg[k])])
    if cfg.get("antialiasing"):
        cmd.append("--antialiasing")
    if cfg.get("optimizer_type"):
        cmd.extend(["--optimizer_type", cfg["optimizer_type"]])
    if cfg.get("images"):
        cmd.extend(["--images", cfg["images"]])
    if cfg.get("depths"):
        cmd.extend(["--depths", cfg["depths"]])

    gpu = os.environ.get("CUDA_VISIBLE_DEVICES", "1")
    env = os.environ.copy()
    env["CUDA_HOME"] = "/usr/local/cuda-12.2"
    env["PATH"] = "/usr/local/cuda-12.2/bin:" + env.get("PATH", "")
    env["CUDA_VISIBLE_DEVICES"] = gpu

    start = time.time()
    logger.info(f"\n{'='*60}")
    logger.info(f"  Config: {cfg['desc']}")
    logger.info(f"  Output: {output}")
    logger.info(f"  GPU: {gpu}")
    logger.info(f"{'='*60}")

    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        env=env, cwd=PROJECT_ROOT,
    )
    last_psnr = None
    for line in proc.stdout:
        # 진행률 출력
        m = re.search(r'PSNR\s*[=:]\s*([\d.]+)', line)
        if m:
            last_psnr = float(m.group(1))
        # iteration 진행 상황
        m2 = re.search(r'(\d+)/(\d+)', line)
        if m2 and int(m2.group(1)) % 10000 == 0:
            pct = int(int(m2.group(1)) / int(m2.group(2)) * 100)
            logger.info(f"  Progress: {m2.group(1)}/{m2.group(2)} ({pct}%)")
    proc.wait()

    elapsed = round((time.time() - start) / 60, 1)
    psnr = get_psnr(output) or last_psnr
    ok = proc.returncode == 0

    logger.info(f"  Result: PSNR={psnr}, time={elapsed}min, ok={ok}")
    return {
        "desc": cfg["desc"],
        "config": "",
        "psnr": psnr,
        "minutes": elapsed,
        "ok": ok,
        "iterations": cfg["iterations"],
    }


def main():
    parser = argparse.ArgumentParser(description="CarNeRF GS Benchmark")
    parser.add_argument("--source_path", help="COLMAP dense path")
    parser.add_argument("--configs", nargs="+",
                        default=["hq_baseline", "aggressive_v2", "low_dssim", "masked_depth", "best_combo_v2"])
    parser.add_argument("--gpu", default="1", help="GPU ID (default: 1)")
    parser.add_argument("--list_configs", action="store_true")
    args = parser.parse_args()

    if args.list_configs:
        print("\n사용 가능한 벤치마크 설정:")
        for n, c in CONFIGS.items():
            print(f"  {n:22s}  {c['desc']}")
        return

    if not args.source_path:
        parser.error("--source_path 필요")

    os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu

    source = os.path.abspath(args.source_path)
    name = os.path.basename(os.path.dirname(source))
    if name == "dense":
        name = os.path.basename(os.path.dirname(os.path.dirname(source)))

    logger.info(f"\n{'*'*60}")
    logger.info(f"  CarNeRF GS Benchmark")
    logger.info(f"  Source: {source}")
    logger.info(f"  Configs: {args.configs}")
    logger.info(f"  GPU: {args.gpu}")
    logger.info(f"{'*'*60}")

    results = []
    for cn in args.configs:
        cfg = CONFIGS.get(cn)
        if not cfg:
            logger.warning(f"  Unknown config: {cn}")
            continue

        c = cfg.copy()
        # 이미지/depth 가용성 체크
        if c.get("images") == "images_masked" and not os.path.isdir(os.path.join(source, "images_masked")):
            logger.warning(f"  images_masked 없음 → images 사용")
            c["images"] = "images"
        if c.get("depths") and not os.path.exists(os.path.join(source, "sparse", "0", "depth_params.json")):
            logger.warning(f"  depth_params.json 없음 → depth 비활성화")
            del c["depths"]

        out = os.path.join(PROJECT_ROOT, "data", "gaussian_output", f"{name}_bench_{cn}")

        # 이미 학습 결과가 있으면 PSNR만 추출
        ply = os.path.join(out, "point_cloud", f"iteration_{c['iterations']}", "point_cloud.ply")
        if os.path.exists(ply):
            psnr = get_psnr(out)
            logger.info(f"\n  [SKIP] {cn}: 이미 학습됨 (PSNR={psnr})")
            results.append({"desc": c["desc"], "config": cn, "psnr": psnr, "minutes": 0, "ok": True, "iterations": c["iterations"]})
            continue

        r = run_config(source, out, c)
        r["config"] = cn
        results.append(r)

    # 결과 요약
    logger.info(f"\n{'='*60}")
    logger.info("  BENCHMARK RESULTS")
    logger.info(f"{'='*60}")
    for r in sorted(results, key=lambda x: float(x.get("psnr") or 0), reverse=True):
        psnr_str = f"{r['psnr']:.2f}" if r.get("psnr") else "N/A"
        logger.info(f"  {r['config']:22s}  PSNR={psnr_str:>8s}  {r['minutes']:>6.1f}min  {'OK' if r['ok'] else 'FAIL'}")

    # JSON 저장
    out_json = os.path.join(PROJECT_ROOT, "data", "gaussian_output", f"bench_{name}.json")
    with open(out_json, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    logger.info(f"\n  Results saved: {out_json}")

    # 최고 PSNR
    best = max(results, key=lambda x: float(x.get("psnr") or 0))
    if best.get("psnr"):
        logger.info(f"\n  BEST: {best['config']} → PSNR {best['psnr']:.2f}")


if __name__ == "__main__":
    main()
