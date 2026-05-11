#!/usr/bin/env python3
"""학습 진행 상황 모니터링 + PSNR 실시간 추적"""
import os, sys, glob, json, time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_psnr_from_tb(model_path):
    """Tensorboard에서 PSNR 추출"""
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
                            last = events[-1]
                            return {
                                "best": round(best.value, 2),
                                "best_step": best.step,
                                "last": round(last.value, 2),
                                "last_step": last.step,
                                "total_events": len(events),
                            }
    except Exception:
        pass
    return None

def get_latest_iteration(model_path):
    """최신 iteration 확인"""
    pc_dir = os.path.join(model_path, "point_cloud")
    if not os.path.isdir(pc_dir):
        return None
    iters = []
    for d in os.listdir(pc_dir):
        if d.startswith("iteration_"):
            try:
                iters.append(int(d.split("_")[1]))
            except ValueError:
                pass
    return max(iters) if iters else None

def main():
    output_dir = os.path.join(PROJECT_ROOT, "data", "gaussian_output")
    print(f"\n{'='*70}")
    print(f"  CarNeRF 3D 학습 모니터링")
    print(f"{'='*70}")

    # 모든 학습 결과 디렉토리 스캔
    results = []
    for name in sorted(os.listdir(output_dir)):
        path = os.path.join(output_dir, name)
        if not os.path.isdir(path):
            continue

        cfg_file = os.path.join(path, "cfg_args")
        if not os.path.exists(cfg_file):
            continue

        psnr_info = get_psnr_from_tb(path)
        latest_iter = get_latest_iteration(path)

        ply_sizes = {}
        pc_dir = os.path.join(path, "point_cloud")
        if os.path.isdir(pc_dir):
            for d in os.listdir(pc_dir):
                ply = os.path.join(pc_dir, d, "point_cloud.ply")
                if os.path.exists(ply):
                    ply_sizes[d] = os.path.getsize(ply) / (1024 * 1024)

        results.append({
            "name": name,
            "psnr": psnr_info,
            "latest_iter": latest_iter,
            "ply_sizes": ply_sizes,
        })

    # 결과 출력
    print(f"\n{'Name':<45s} {'Best PSNR':>10s} {'Last PSNR':>10s} {'Iter':>8s} {'PLY MB':>8s}")
    print("-" * 85)

    for r in sorted(results, key=lambda x: (x["psnr"]["best"] if x["psnr"] else 0), reverse=True):
        psnr_best = f"{r['psnr']['best']:.2f}" if r["psnr"] else "N/A"
        psnr_last = f"{r['psnr']['last']:.2f}" if r["psnr"] else "N/A"
        iter_str = str(r["latest_iter"]) if r["latest_iter"] else "N/A"
        ply_str = ""
        if r["ply_sizes"]:
            max_ply = max(r["ply_sizes"].values())
            ply_str = f"{max_ply:.0f}"
        print(f"  {r['name']:<43s} {psnr_best:>10s} {psnr_last:>10s} {iter_str:>8s} {ply_str:>8s}")

    print(f"\n  Total models: {len(results)}")

    # 최고 PSNR
    best = max(results, key=lambda x: (x["psnr"]["best"] if x["psnr"] else 0))
    if best["psnr"]:
        print(f"\n  BEST: {best['name']} → PSNR {best['psnr']['best']:.2f} at step {best['psnr']['best_step']}")
    print()


if __name__ == "__main__":
    main()
