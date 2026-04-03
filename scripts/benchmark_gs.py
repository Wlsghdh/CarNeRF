#!/usr/bin/env python3
"""
CarNeRF GS 벤치마크 - 다양한 하이퍼파라미터로 학습 후 PSNR 비교

사용법:
    python scripts/benchmark_gs.py --source_path data/colmap_output/nf_sonata_hq/dense
    python scripts/benchmark_gs.py --source_path data/colmap_output/car2_test/dense --configs ultra best_combo
    python scripts/benchmark_gs.py --list_configs
"""
import argparse, json, os, sys, time, subprocess, re, logging

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIGS = {
    "hq_baseline": {
        "desc": "HQ baseline (60K, grad 0.00007)",
        "iterations": 60000, "densify_grad_threshold": 0.00007,
        "densify_until_iter": 35000, "opacity_reset_interval": 3000,
        "lambda_dssim": 0.2, "antialiasing": True,
    },
    "aggressive_densify": {
        "desc": "Aggressive densify (0.00005, until 45K)",
        "iterations": 60000, "densify_grad_threshold": 0.00005,
        "densify_until_iter": 45000, "opacity_reset_interval": 2500,
        "lambda_dssim": 0.2, "antialiasing": True,
    },
    "low_dssim": {
        "desc": "Low SSIM weight (0.15) for PSNR",
        "iterations": 60000, "densify_grad_threshold": 0.00007,
        "densify_until_iter": 35000, "opacity_reset_interval": 3000,
        "lambda_dssim": 0.15, "antialiasing": True,
    },
    "ultra": {
        "desc": "Ultra (100K, aggressive, sparse_adam)",
        "iterations": 100000, "densify_grad_threshold": 0.00005,
        "densify_until_iter": 50000, "opacity_reset_interval": 2500,
        "lambda_dssim": 0.18, "antialiasing": True, "optimizer_type": "sparse_adam",
    },
    "masked_depth": {
        "desc": "Masked images + Depth reg",
        "iterations": 60000, "densify_grad_threshold": 0.00007,
        "densify_until_iter": 35000, "opacity_reset_interval": 3000,
        "lambda_dssim": 0.2, "antialiasing": True,
        "images": "images_masked", "depths": "depths",
    },
    "best_combo": {
        "desc": "Best combo (aggressive+low_dssim+masked+depth+80K)",
        "iterations": 80000, "densify_grad_threshold": 0.00004,
        "densify_until_iter": 50000, "opacity_reset_interval": 2000,
        "lambda_dssim": 0.15, "antialiasing": True,
        "images": "images_masked", "depths": "depths",
    },
}


def get_psnr(model_path):
    """Tensorboard에서 최종 PSNR 추출"""
    try:
        from tensorboard.backend.event_processing.event_accumulator import EventAccumulator
        for f in os.listdir(model_path):
            if f.startswith("events.out.tfevents"):
                ea = EventAccumulator(os.path.join(model_path, f))
                ea.Reload()
                for tag in ea.Tags().get("scalars", []):
                    if "psnr" in tag.lower():
                        events = ea.Scalars(tag)
                        if events:
                            return round(events[-1].value, 2)
    except Exception:
        pass
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
    if cfg.get("antialiasing"): cmd.append("--antialiasing")
    if cfg.get("optimizer_type"): cmd.extend(["--optimizer_type", cfg["optimizer_type"]])
    if cfg.get("images"): cmd.extend(["--images", cfg["images"]])
    if cfg.get("depths"): cmd.extend(["--depths", cfg["depths"]])

    env = os.environ.copy()
    env["CUDA_HOME"] = "/usr/local/cuda-12.2"
    env["PATH"] = "/usr/local/cuda-12.2/bin:" + env.get("PATH", "")

    start = time.time()
    logger.info(f">>> {cfg['desc']}")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env, cwd=PROJECT_ROOT)
    last_psnr = None
    for line in proc.stdout:
        m = re.search(r'PSNR\s*[=:]\s*([\d.]+)', line)
        if m: last_psnr = float(m.group(1))
    proc.wait()

    elapsed = round((time.time() - start) / 60, 1)
    psnr = get_psnr(output) or last_psnr
    return {"desc": cfg["desc"], "config": "", "psnr": psnr, "minutes": elapsed, "ok": proc.returncode == 0}


def main():
    parser = argparse.ArgumentParser(description="CarNeRF GS Benchmark")
    parser.add_argument("--source_path", help="COLMAP dense path")
    parser.add_argument("--configs", nargs="+", default=["hq_baseline", "aggressive_densify", "low_dssim"])
    parser.add_argument("--list_configs", action="store_true")
    args = parser.parse_args()

    if args.list_configs:
        for n, c in CONFIGS.items():
            print(f"  {n:22s} {c['desc']}")
        return

    source = os.path.abspath(args.source_path)
    name = os.path.basename(os.path.dirname(source))
    if name == "dense": name = os.path.basename(os.path.dirname(os.path.dirname(source)))

    results = []
    for cn in args.configs:
        cfg = CONFIGS.get(cn)
        if not cfg:
            continue
        c = cfg.copy()
        if c.get("images") == "images_masked" and not os.path.isdir(os.path.join(source, "images_masked")):
            c["images"] = "images"
        if c.get("depths") and not os.path.exists(os.path.join(source, "sparse", "0", "depth_params.json")):
            del c["depths"]

        out = os.path.join(PROJECT_ROOT, "data", "gaussian_output", f"{name}_bench_{cn}")
        r = run_config(source, out, c)
        r["config"] = cn
        results.append(r)
        logger.info(f"  PSNR={r['psnr']}, time={r['minutes']}min")

    logger.info("\n" + "=" * 50)
    for r in sorted(results, key=lambda x: float(x.get("psnr") or 0), reverse=True):
        logger.info(f"  {r['config']:22s} PSNR={str(r.get('psnr','-')):>8s}  {r['minutes']}min")

    out_json = os.path.join(PROJECT_ROOT, "data", "gaussian_output", f"bench_{name}.json")
    with open(out_json, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    logger.info(f"Results saved: {out_json}")


if __name__ == "__main__":
    main()
