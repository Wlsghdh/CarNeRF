#!/bin/bash
set -e
cd /home/jjh0709/Project_2026_1

export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export CUDA_HOME=/usr/local/cuda-12.2

echo "============================================================"
echo "NF소나타 HQ 재구축 (200프레임 + 60K + 튜닝된 하이퍼파라미터)"
echo "============================================================"

START_TOTAL=$(python3 -c "import time; print(time.time())")

# Step 1: COLMAP
echo ""
echo "[Step 1/3] COLMAP SfM (200 frames, sequential matching)..."
START=$(python3 -c "import time; print(time.time())")

conda run -n jjh python scripts/run_colmap.py \
  --image_path data/frames/nf_sonata_hq \
  --output_path data/colmap_output/nf_sonata_hq

END=$(python3 -c "import time; print(time.time())")
echo ">> Step 1 완료: $(python3 -c "print(f'{$END - $START:.1f}초 ({($END - $START)/60:.1f}분)')")"

# Step 2: Gaussian Splatting 60K with tuned parameters
echo ""
echo "[Step 2/3] Gaussian Splatting 60K iterations (튜닝된 파라미터)..."
START=$(python3 -c "import time; print(time.time())")

conda run -n jjh python third_party/gaussian-splatting/train.py \
  -s data/colmap_output/nf_sonata_hq/dense \
  -m data/gaussian_output/nf_sonata_hq \
  --iterations 60000 \
  --densify_grad_threshold 0.0001 \
  --densify_until_iter 25000 \
  --lambda_dssim 0.4 \
  --opacity_reset_interval 2000 \
  --position_lr_max_steps 60000 \
  --test_iterations 7000 30000 60000

END=$(python3 -c "import time; print(time.time())")
echo ">> Step 2 완료: $(python3 -c "print(f'{$END - $START:.1f}초 ({($END - $START)/60:.1f}분)')")"

# Step 3: Export
echo ""
echo "[Step 3/3] Export..."
START=$(python3 -c "import time; print(time.time())")

conda run -n jjh python scripts/export_model.py \
  --input data/gaussian_output/nf_sonata_hq/point_cloud/iteration_60000/point_cloud.ply \
  --output backend/app/static/models/nf_sonata/model \
  --format both \
  --max_gaussians 3000000

END=$(python3 -c "import time; print(time.time())")
echo ">> Step 3 완료: $(python3 -c "print(f'{$END - $START:.1f}초')")"

END_TOTAL=$(python3 -c "import time; print(time.time())")
echo ""
echo "============================================================"
echo "HQ 재구축 완료!"
echo "  총 시간: $(python3 -c "print(f'{$END_TOTAL - $START_TOTAL:.1f}초 ({($END_TOTAL - $START_TOTAL)/60:.1f}분)')")"
echo "============================================================"
