#!/bin/bash
# CarNeRF 전체 벤치마크 순차 실행 스크립트
# 사용법: bash scripts/run_full_benchmark.sh
#
# GPU 1,2,3만 사용 (4,5,6 금지)

PYTHON=/home/jjh0709/.conda/envs/jjh/bin/python
PROJECT=/home/jjh0709/Project_2026_1
SOURCE=$PROJECT/data/colmap_output/nf_sonata_hq/dense

export CUDA_HOME=/usr/local/cuda-12.2
export PATH=/usr/local/cuda-12.2/bin:$PATH

cd $PROJECT

echo "=============================================="
echo "  CarNeRF Full Benchmark Suite"
echo "  $(date)"
echo "=============================================="

# Phase 1: 3개 병렬 (이미 실행 중일 수 있음)
echo ""
echo "[Phase 1] Parallel training (GPU 1,2,3)"
echo "  GPU 1: aggressive_v2 (80K)"
echo "  GPU 2: low_dssim (80K)"
echo "  GPU 3: 2DGS (60K)"
echo "  → 이미 실행 중이면 완료 대기"

# aggressive_v2 완료 대기
while ! ls data/gaussian_output/nf_sonata_hq_bench_aggressive_v2/point_cloud/iteration_80000/point_cloud.ply 2>/dev/null; do
    sleep 60
done
echo "  aggressive_v2 완료!"

# Phase 2: GPU 1이 비었으니 masked_depth 실행
echo ""
echo "[Phase 2] masked_depth on GPU 1"
CUDA_VISIBLE_DEVICES=1 $PYTHON scripts/benchmark_gs.py \
    --source_path $SOURCE \
    --configs masked_depth \
    --gpu 1

echo "  masked_depth 완료!"

# low_dssim 완료 대기
while ! ls data/gaussian_output/nf_sonata_hq_bench_low_dssim/point_cloud/iteration_80000/point_cloud.ply 2>/dev/null; do
    sleep 60
done
echo "  low_dssim 완료!"

# Phase 3: GPU 2가 비었으니 best_combo_v2 실행
echo ""
echo "[Phase 3] best_combo_v2 on GPU 2"
CUDA_VISIBLE_DEVICES=2 $PYTHON scripts/benchmark_gs.py \
    --source_path $SOURCE \
    --configs best_combo_v2 \
    --gpu 2

echo "  best_combo_v2 완료!"

# Phase 4: 결과 집계
echo ""
echo "[Phase 4] Final Results"
$PYTHON scripts/monitor_training.py

echo ""
echo "=============================================="
echo "  Benchmark Complete! $(date)"
echo "=============================================="
