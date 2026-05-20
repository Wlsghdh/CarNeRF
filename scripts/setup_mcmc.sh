#!/bin/bash
# 3DGS-MCMC 환경 설정 스크립트
# MCMC는 자체 diff-gaussian-rasterization fork를 사용하므로
# 기존 vanilla 3DGS와 충돌함 → 별도 설치 또는 교체 필요
#
# 옵션 1: 기존 rasterizer를 MCMC 버전으로 교체 (간단, 단 vanilla 3DGS가 깨짐)
# 옵션 2: 별도 conda env (안전하지만 환경 관리 복잡)
#
# 이 스크립트는 옵션 1 (교체) 방식을 사용
# 원복: pip install third_party/gaussian-splatting/submodules/diff-gaussian-rasterization

set -e
export CUDA_HOME=/usr/local/cuda-12.2
export PATH=/usr/local/cuda-12.2/bin:$PATH

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
MCMC_DIR="$PROJECT_ROOT/third_party/3dgs-mcmc"

echo "=== Installing MCMC diff-gaussian-rasterization ==="
echo "WARNING: This will replace the vanilla rasterizer!"
echo "To restore: pip install $PROJECT_ROOT/third_party/gaussian-splatting/submodules/diff-gaussian-rasterization"
echo ""

cd "$MCMC_DIR"

# Install MCMC rasterizer (replaces vanilla)
pip install submodules/diff-gaussian-rasterization
pip install submodules/simple-knn

# Verify
python -c "
from diff_gaussian_rasterization import compute_relocation
print('MCMC rasterizer installed successfully!')
print('compute_relocation available: True')
"

echo ""
echo "=== Setup complete ==="
echo "Run MCMC training:"
echo "  CUDA_VISIBLE_DEVICES=0 python scripts/train_mcmc.py \\"
echo "    --source_path data/colmap_output/nf_sonata_hq/dense \\"
echo "    --output_path data/gaussian_output/nf_sonata_mcmc"
echo ""
echo "To restore vanilla 3DGS rasterizer:"
echo "  pip install $PROJECT_ROOT/third_party/gaussian-splatting/submodules/diff-gaussian-rasterization"
