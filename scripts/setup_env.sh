#!/bin/bash
# =============================================================================
# CarNeRF 환경 세팅 자동화 스크립트
# - conda 환경 생성 (python 3.10)
# - PyTorch (CUDA) 설치
# - COLMAP 설치
# - 3D Gaussian Splatting 클론 및 빌드
# - requirements.txt 설치
# - 설치 검증
# =============================================================================

set -e  # 에러 발생 시 즉시 중단

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_NAME="carnerf"
GS_DIR="${PROJECT_ROOT}/third_party/gaussian-splatting"

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}  CarNeRF 환경 세팅 시작${NC}"
echo -e "${BLUE}  프로젝트 경로: ${PROJECT_ROOT}${NC}"
echo -e "${BLUE}============================================${NC}"

# -----------------------------------------
# 1. Conda 환경 확인 및 생성
# -----------------------------------------
echo -e "\n${YELLOW}[1/6] Conda 환경 확인 및 생성${NC}"

if ! command -v conda &> /dev/null; then
    echo -e "${RED}conda가 설치되어 있지 않습니다.${NC}"
    echo "Miniconda 설치: https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

# conda 초기화 (스크립트에서 conda activate 사용하기 위해)
eval "$(conda shell.bash hook)"

if conda env list | grep -q "^${ENV_NAME} "; then
    echo -e "${GREEN}conda 환경 '${ENV_NAME}'이 이미 존재합니다.${NC}"
else
    echo "conda 환경 '${ENV_NAME}' 생성 중 (Python 3.10)..."
    conda create -n "${ENV_NAME}" python=3.10 -y
fi

conda activate "${ENV_NAME}"
echo -e "${GREEN}활성화된 환경: ${CONDA_DEFAULT_ENV}${NC}"
echo "Python 경로: $(which python)"
echo "Python 버전: $(python --version)"

# -----------------------------------------
# 2. PyTorch 설치 (CUDA 지원)
# -----------------------------------------
echo -e "\n${YELLOW}[2/6] PyTorch 설치 (CUDA 지원)${NC}"

# CUDA 버전 감지
if command -v nvcc &> /dev/null; then
    CUDA_VERSION=$(nvcc --version | grep "release" | sed 's/.*release //' | sed 's/,.*//')
    echo "CUDA 버전 감지: ${CUDA_VERSION}"
else
    echo -e "${YELLOW}nvcc를 찾을 수 없습니다. nvidia-smi로 확인합니다...${NC}"
    if command -v nvidia-smi &> /dev/null; then
        CUDA_VERSION=$(nvidia-smi | grep "CUDA Version" | awk '{print $9}')
        echo "CUDA 버전 (nvidia-smi): ${CUDA_VERSION}"
    else
        echo -e "${RED}CUDA를 찾을 수 없습니다. GPU가 있는지 확인해 주세요.${NC}"
        exit 1
    fi
fi

# PyTorch 설치 (CUDA 11.8 또는 12.1 기준)
CUDA_MAJOR=$(echo "${CUDA_VERSION}" | cut -d'.' -f1)
if [ "${CUDA_MAJOR}" -ge "12" ]; then
    echo "CUDA 12.x 감지 → PyTorch CUDA 12.1 버전 설치"
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
else
    echo "CUDA 11.x 감지 → PyTorch CUDA 11.8 버전 설치"
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
fi

# -----------------------------------------
# 3. COLMAP 설치
# -----------------------------------------
echo -e "\n${YELLOW}[3/6] COLMAP 설치 확인${NC}"

if command -v colmap &> /dev/null; then
    echo -e "${GREEN}COLMAP이 이미 설치되어 있습니다.${NC}"
    colmap -h 2>&1 | head -3
else
    echo "COLMAP 설치를 시도합니다..."

    # 방법 1: apt (Ubuntu)
    if command -v apt &> /dev/null; then
        echo "apt로 COLMAP 설치 중..."
        sudo apt update
        sudo apt install -y colmap
    else
        echo -e "${YELLOW}apt를 사용할 수 없습니다.${NC}"
        echo "수동으로 COLMAP을 설치해 주세요:"
        echo "  - conda: conda install -c conda-forge colmap"
        echo "  - 소스 빌드: https://colmap.github.io/install.html"
        echo ""
        echo -e "${YELLOW}COLMAP 없이 계속 진행합니다. 나중에 설치해 주세요.${NC}"
    fi
fi

# -----------------------------------------
# 4. 3D Gaussian Splatting 클론
# -----------------------------------------
echo -e "\n${YELLOW}[4/6] 3D Gaussian Splatting 클론${NC}"

mkdir -p "${PROJECT_ROOT}/third_party"

if [ -d "${GS_DIR}" ]; then
    echo -e "${GREEN}Gaussian Splatting 리포가 이미 존재합니다: ${GS_DIR}${NC}"
else
    echo "Gaussian Splatting 클론 중..."
    git clone https://github.com/graphdeco-inria/gaussian-splatting.git "${GS_DIR}"
fi

cd "${GS_DIR}"
echo "submodule 초기화..."
git submodule update --init --recursive

# -----------------------------------------
# 5. Gaussian Splatting 의존성 설치
# -----------------------------------------
echo -e "\n${YELLOW}[5/6] Gaussian Splatting 의존성 설치${NC}"

cd "${GS_DIR}"

# submodule들 설치 (diff-gaussian-rasterization, simple-knn)
if [ -d "submodules/diff-gaussian-rasterization" ]; then
    echo "diff-gaussian-rasterization 설치 중..."
    pip install "submodules/diff-gaussian-rasterization"
fi

if [ -d "submodules/simple-knn" ]; then
    echo "simple-knn 설치 중..."
    pip install "submodules/simple-knn"
fi

# requirements.txt 설치 (프로젝트 루트)
echo "프로젝트 의존성 설치 중..."
pip install -r "${PROJECT_ROOT}/requirements.txt"

# Gaussian Splatting 자체 의존성 (있는 경우)
if [ -f "${GS_DIR}/requirements.txt" ]; then
    pip install -r "${GS_DIR}/requirements.txt"
fi

# -----------------------------------------
# 6. 설치 검증
# -----------------------------------------
echo -e "\n${YELLOW}[6/6] 설치 검증${NC}"

echo ""
echo "--- Python 패키지 ---"
python -c "
import torch
print(f'PyTorch 버전: {torch.__version__}')
print(f'CUDA 사용 가능: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'CUDA 버전: {torch.version.cuda}')
    print(f'GPU: {torch.cuda.get_device_name(0)}')
    print(f'GPU 메모리: {torch.cuda.get_device_properties(0).total_mem / 1024**3:.1f} GB')
else:
    print('⚠ CUDA가 사용 불가합니다. GPU 드라이버를 확인해 주세요.')
"

echo ""
python -c "
import cv2; print(f'OpenCV 버전: {cv2.__version__}')
import numpy; print(f'NumPy 버전: {numpy.__version__}')
from plyfile import PlyData; print('plyfile: OK')
from tqdm import tqdm; print('tqdm: OK')
"

echo ""
echo "--- COLMAP ---"
if command -v colmap &> /dev/null; then
    echo -e "${GREEN}COLMAP: 설치됨${NC}"
else
    echo -e "${RED}COLMAP: 미설치 (별도 설치 필요)${NC}"
fi

echo ""
echo "--- Gaussian Splatting ---"
if [ -f "${GS_DIR}/train.py" ]; then
    echo -e "${GREEN}Gaussian Splatting: ${GS_DIR}${NC}"
else
    echo -e "${RED}Gaussian Splatting: 설치 실패${NC}"
fi

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  CarNeRF 환경 세팅 완료!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "사용법:"
echo "  conda activate ${ENV_NAME}"
echo "  cd ${PROJECT_ROOT}"
echo "  python scripts/run_pipeline.py --input data/raw/video.mp4 --name my_car"
