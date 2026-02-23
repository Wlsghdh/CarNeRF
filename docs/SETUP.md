# CarNeRF 환경 설정 가이드

본 문서는 A100 GPU 서버에서 CarNeRF 프로젝트를 실행하기 위한
환경 설정 절차를 단계별로 안내합니다.

---

## 목차

1. [시스템 요구사항](#1-시스템-요구사항)
2. [CUDA / cuDNN 확인](#2-cuda--cudnn-확인)
3. [conda 환경 설정](#3-conda-환경-설정)
4. [COLMAP 설치](#4-colmap-설치)
5. [Gaussian Splatting 설정](#5-gaussian-splatting-설정)
6. [전체 설치 검증](#6-전체-설치-검증)
7. [트러블슈팅](#7-트러블슈팅)

---

## 1. 시스템 요구사항

| 항목 | 최소 요구사항 | 권장 사양 |
|------|-------------|----------|
| GPU | NVIDIA GPU (CUDA Compute Capability 7.0+) | NVIDIA A100 (40GB/80GB) |
| GPU 메모리 | 8 GB | 40 GB 이상 |
| RAM | 16 GB | 64 GB 이상 |
| 저장 공간 | 50 GB | 200 GB 이상 (SSD 권장) |
| OS | Ubuntu 20.04+ | Ubuntu 22.04 LTS |
| CUDA | 11.7+ | 12.1+ |
| Python | 3.9+ | 3.10 |
| conda | Miniconda 또는 Anaconda | Miniconda (최신) |

---

## 2. CUDA / cuDNN 확인

### 2.1 NVIDIA 드라이버 확인

```bash
# NVIDIA 드라이버 버전 및 GPU 정보 확인
nvidia-smi
```

**예상 출력:**
```
+-----------------------------------------------------------------------------+
| NVIDIA-SMI 535.129.03   Driver Version: 535.129.03   CUDA Version: 12.2     |
|-------------------------------+----------------------+----------------------+
| GPU  Name        Persistence-M| Bus-Id        Disp.A | Volatile Uncorr. ECC |
| Fan  Temp  Perf  Pwr:Usage/Cap|         Memory-Usage | GPU-Util  Compute M. |
|===============================+======================+======================|
|   0  NVIDIA A100-SXM...  On   | 00000000:00:04.0 Off |                    0 |
| N/A   32C    P0    52W / 400W |      0MiB / 81920MiB |      0%      Default |
+-------------------------------+----------------------+----------------------+
```

**확인 사항:**
- `CUDA Version`이 11.7 이상인지 확인
- GPU 모델이 올바르게 표시되는지 확인
- GPU 메모리가 충분한지 확인

### 2.2 CUDA Toolkit 확인

```bash
# CUDA 컴파일러 버전 확인
nvcc --version
```

**예상 출력:**
```
nvcc: NVIDIA (R) Cuda compiler driver
Copyright (c) 2005-2023 NVIDIA Corporation
Built on Tue_Aug_15_22:02:13_PDT_2023
Cuda compilation tools, release 12.2, V12.2.140
```

CUDA Toolkit이 설치되어 있지 않다면 아래 절차를 따릅니다.

```bash
# CUDA Toolkit 12.1 설치 (Ubuntu 22.04)
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt-get update
sudo apt-get install -y cuda-toolkit-12-1

# 환경 변수 설정
echo 'export PATH=/usr/local/cuda-12.1/bin:$PATH' >> ~/.bashrc
echo 'export LD_LIBRARY_PATH=/usr/local/cuda-12.1/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc
source ~/.bashrc
```

### 2.3 cuDNN 확인

```bash
# cuDNN 버전 확인 (방법 1)
cat /usr/local/cuda/include/cudnn_version.h 2>/dev/null | grep CUDNN_MAJOR -A 2

# cuDNN 버전 확인 (방법 2)
python3 -c "import torch; print(torch.backends.cudnn.version())"

# cuDNN 라이브러리 존재 확인
ldconfig -p | grep cudnn
```

cuDNN이 설치되어 있지 않다면:

```bash
# cuDNN 설치 (CUDA 12.x용)
sudo apt-get install -y libcudnn8 libcudnn8-dev
```

### 2.4 GPU Compute Capability 확인

Gaussian Splatting은 CUDA Compute Capability 7.0 이상을 요구합니다.

| GPU 모델 | Compute Capability | 지원 여부 |
|----------|-------------------|----------|
| A100 | 8.0 | O |
| H100 | 9.0 | O |
| RTX 4090 | 8.9 | O |
| RTX 3090 | 8.6 | O |
| RTX 3080 | 8.6 | O |
| V100 | 7.0 | O |
| RTX 2080 Ti | 7.5 | O |
| GTX 1080 Ti | 6.1 | X (미지원) |

```bash
# Compute Capability 확인
python3 -c "import torch; print(torch.cuda.get_device_capability())"
# 출력 예시: (8, 0) → Compute Capability 8.0
```

---

## 3. conda 환경 설정

### 3.1 Miniconda 설치 (미설치 시)

```bash
# Miniconda 다운로드 및 설치
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh -b -p $HOME/miniconda3

# conda 초기화
eval "$($HOME/miniconda3/bin/conda shell.bash hook)"
conda init bash
source ~/.bashrc
```

### 3.2 carnerf 환경 생성

```bash
# Python 3.10 기반 환경 생성
conda create -n carnerf python=3.10 -y

# 환경 활성화
conda activate carnerf

# 환경이 올바르게 활성화되었는지 확인
which python
# 출력 예시: /home/<user>/miniconda3/envs/carnerf/bin/python

python --version
# 출력 예시: Python 3.10.x
```

### 3.3 PyTorch 설치

CUDA 버전에 맞는 PyTorch를 설치합니다. **CUDA 버전과 PyTorch의 CUDA 버전을 반드시 일치시켜야 합니다.**

```bash
# CUDA 12.1 기준 PyTorch 설치
conda activate carnerf
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

다른 CUDA 버전을 사용하는 경우:

```bash
# CUDA 11.8
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# CUDA 12.4
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
```

**PyTorch GPU 인식 확인:**

```bash
python -c "
import torch
print(f'PyTorch 버전: {torch.__version__}')
print(f'CUDA 사용 가능: {torch.cuda.is_available()}')
print(f'CUDA 버전: {torch.version.cuda}')
print(f'cuDNN 버전: {torch.backends.cudnn.version()}')
print(f'GPU 이름: {torch.cuda.get_device_name(0)}')
print(f'GPU 메모리: {torch.cuda.get_device_properties(0).total_mem / 1e9:.1f} GB')
"
```

### 3.4 프로젝트 의존성 설치

```bash
conda activate carnerf
cd /home/jjh0709/Project_2026_1

# requirements.txt의 패키지 설치
pip install -r requirements.txt
```

`requirements.txt` 내용:

```
torch>=2.0.0
torchvision>=0.15.0
opencv-python>=4.8.0
numpy>=1.24.0
Pillow>=10.0.0
plyfile>=1.0.0
tqdm>=4.65.0
argparse
```

### 3.5 추가 유틸리티 설치

```bash
# 영상 처리를 위한 FFmpeg (시스템 패키지)
sudo apt-get install -y ffmpeg

# 이미지 처리를 위한 ImageMagick (선택사항)
sudo apt-get install -y imagemagick
```

---

## 4. COLMAP 설치

COLMAP은 Structure-from-Motion(SfM) 파이프라인으로, 여러 가지 방법으로 설치할 수 있습니다.
환경에 가장 적합한 방법을 선택하세요.

### 방법 1: apt 패키지 관리자 (가장 간단)

```bash
sudo apt-get update
sudo apt-get install -y colmap
```

**장점:** 설치가 매우 간단
**단점:** 최신 버전이 아닐 수 있음, GPU 가속이 비활성화되어 있을 수 있음

**설치 확인:**
```bash
colmap --help
colmap feature_extractor --help
```

### 방법 2: conda를 통한 설치

```bash
conda activate carnerf
conda install -c conda-forge colmap -y
```

**장점:** conda 환경 내에서 관리 가능, 의존성 자동 해결
**단점:** GPU 가속이 포함되지 않을 수 있음

### 방법 3: 소스에서 빌드 (GPU 가속 포함, 권장)

A100 GPU의 CUDA 가속을 최대한 활용하려면 소스에서 직접 빌드하는 것이 좋습니다.

```bash
# 1. 빌드 의존성 설치
sudo apt-get update
sudo apt-get install -y \
    git \
    cmake \
    ninja-build \
    build-essential \
    libboost-program-options-dev \
    libboost-filesystem-dev \
    libboost-graph-dev \
    libboost-system-dev \
    libeigen3-dev \
    libflann-dev \
    libfreeimage-dev \
    libmetis-dev \
    libgoogle-glog-dev \
    libgtest-dev \
    libsqlite3-dev \
    libglew-dev \
    qtbase5-dev \
    libqt5opengl5-dev \
    libcgal-dev \
    libceres-dev

# 2. COLMAP 소스 다운로드
cd /tmp
git clone https://github.com/colmap/colmap.git
cd colmap
git checkout main  # 또는 특정 릴리스 태그 (예: 3.9.1)

# 3. 빌드 디렉토리 생성 및 CMake 설정
mkdir build && cd build
cmake .. -GNinja \
    -DCMAKE_CUDA_ARCHITECTURES="80" \
    -DCMAKE_BUILD_TYPE=Release

# A100 GPU의 Compute Capability는 8.0이므로 "80"으로 설정
# 다른 GPU를 사용하는 경우 해당 Compute Capability 값으로 변경
# 예: RTX 3090 → "86", RTX 4090 → "89"

# 4. 빌드 (CPU 코어 수에 따라 시간 소요)
ninja -j$(nproc)

# 5. 설치
sudo ninja install

# 6. 설치 확인
colmap --version
```

**예상 빌드 시간:** 약 10~30분 (CPU 코어 수에 따라 다름)

### 방법 4: Docker 컨테이너 사용

```bash
# COLMAP Docker 이미지 다운로드
docker pull colmap/colmap:latest

# 컨테이너 실행 (GPU 포함)
docker run --gpus all -it \
    -v /home/jjh0709/Project_2026_1/data:/data \
    colmap/colmap:latest \
    colmap automatic_reconstructor \
    --workspace_path /data/colmap_output/car_01 \
    --image_path /data/frames/car_01
```

**장점:** 환경 설정 불필요, 의존성 충돌 없음
**단점:** Docker 설치 필요, 파일 경로 마운트 필요

### COLMAP 설치 방법 비교

| 방법 | 난이도 | GPU 가속 | 최신 버전 | 추천 상황 |
|------|--------|---------|----------|----------|
| apt | 매우 쉬움 | X (보통) | X | 빠른 테스트 |
| conda | 쉬움 | X (보통) | X | conda 환경 선호 시 |
| **소스 빌드** | **어려움** | **O** | **O** | **A100에서 최적 성능 (권장)** |
| Docker | 보통 | O | O | 환경 격리 필요 시 |

### COLMAP GPU 가속 확인

```bash
# GPU 가속이 활성화되었는지 확인
colmap feature_extractor --help | grep -i "sift_gpu"

# 실제 GPU 사용 테스트
colmap feature_extractor \
    --database_path /tmp/test.db \
    --image_path /tmp/test_images \
    --SiftExtraction.use_gpu 1
# GPU 가속이 활성화되어 있다면 에러 없이 실행됨
```

---

## 5. Gaussian Splatting 설정

### 5.1 저장소 클론

프로젝트의 `third_party/` 디렉토리에 Gaussian Splatting 공식 저장소를 클론합니다.

```bash
cd /home/jjh0709/Project_2026_1

# 이미 클론되어 있지 않은 경우
git clone https://github.com/graphdeco-inria/gaussian-splatting.git \
    third_party/gaussian-splatting --recursive
```

### 5.2 서브모듈 확인

Gaussian Splatting은 `diff-gaussian-rasterization`과 `simple-knn`이라는
두 개의 CUDA 커스텀 모듈을 서브모듈로 포함합니다.

```bash
cd /home/jjh0709/Project_2026_1/third_party/gaussian-splatting

# 서브모듈 상태 확인
git submodule status

# 서브모듈이 초기화되지 않은 경우
git submodule update --init --recursive
```

**확인할 서브모듈:**
```
submodules/diff-gaussian-rasterization/    # 미분 가능한 Gaussian 래스터라이저
submodules/simple-knn/                     # 간단한 KNN (최근접 이웃) 모듈
```

### 5.3 CUDA 커스텀 모듈 빌드

```bash
conda activate carnerf
cd /home/jjh0709/Project_2026_1/third_party/gaussian-splatting

# diff-gaussian-rasterization 빌드 및 설치
pip install submodules/diff-gaussian-rasterization/

# simple-knn 빌드 및 설치
pip install submodules/simple-knn/
```

**빌드 성공 확인:**

```bash
python -c "
import diff_gaussian_rasterization
print('diff-gaussian-rasterization 설치 완료')

from simple_knn._C import distCUDA2
print('simple-knn 설치 완료')
"
```

### 5.4 Gaussian Splatting 의존성 설치

```bash
cd /home/jjh0709/Project_2026_1/third_party/gaussian-splatting
pip install -r requirements.txt
```

### 5.5 설치 전체 검증

```bash
python -c "
import torch
print('[1/5] PyTorch:', torch.__version__)
print('[2/5] CUDA 사용 가능:', torch.cuda.is_available())

import diff_gaussian_rasterization
print('[3/5] diff-gaussian-rasterization: OK')

from simple_knn._C import distCUDA2
print('[4/5] simple-knn: OK')

import cv2
print('[5/5] OpenCV:', cv2.__version__)

print()
print('Gaussian Splatting 환경 설정이 완료되었습니다.')
"
```

---

## 6. 전체 설치 검증

모든 설정이 완료되면 아래 검증 스크립트를 실행하여 환경을 점검합니다.

```bash
conda activate carnerf
cd /home/jjh0709/Project_2026_1

python -c "
import sys
import shutil

print('=' * 60)
print('CarNeRF 환경 검증')
print('=' * 60)

# 1. Python 버전
print(f'\n[1] Python 버전: {sys.version}')
assert sys.version_info >= (3, 9), 'Python 3.9 이상이 필요합니다'
print('    -> 통과')

# 2. PyTorch + CUDA
import torch
print(f'\n[2] PyTorch: {torch.__version__}')
print(f'    CUDA 사용 가능: {torch.cuda.is_available()}')
assert torch.cuda.is_available(), 'CUDA를 사용할 수 없습니다'
print(f'    CUDA 버전: {torch.version.cuda}')
print(f'    GPU: {torch.cuda.get_device_name(0)}')
print(f'    GPU 메모리: {torch.cuda.get_device_properties(0).total_mem / 1e9:.1f} GB')
print('    -> 통과')

# 3. COLMAP
colmap_path = shutil.which('colmap')
print(f'\n[3] COLMAP 경로: {colmap_path}')
assert colmap_path is not None, 'COLMAP이 설치되어 있지 않습니다'
print('    -> 통과')

# 4. Gaussian Splatting 모듈
import diff_gaussian_rasterization
print('\n[4] diff-gaussian-rasterization: 설치됨')
from simple_knn._C import distCUDA2
print('    simple-knn: 설치됨')
print('    -> 통과')

# 5. 기타 패키지
import cv2
import numpy as np
from PIL import Image
import plyfile
from tqdm import tqdm
print(f'\n[5] OpenCV: {cv2.__version__}')
print(f'    NumPy: {np.__version__}')
print(f'    Pillow: {Image.__version__}')
print('    plyfile: 설치됨')
print('    tqdm: 설치됨')
print('    -> 통과')

# 6. 디렉토리 구조 확인
import os
base = '/home/jjh0709/Project_2026_1'
required_dirs = [
    'scripts', 'data', 'data/raw', 'data/frames',
    'data/colmap_output', 'data/gaussian_output',
    'third_party/gaussian-splatting', 'web_viewer'
]
print('\n[6] 디렉토리 구조 확인:')
all_ok = True
for d in required_dirs:
    full_path = os.path.join(base, d)
    exists = os.path.isdir(full_path)
    status = '존재' if exists else '없음'
    print(f'    {d}: {status}')
    if not exists:
        all_ok = False
if all_ok:
    print('    -> 통과')
else:
    print('    -> 일부 디렉토리가 없습니다 (생성이 필요합니다)')

print('\n' + '=' * 60)
print('환경 검증 완료')
print('=' * 60)
"
```

---

## 7. 트러블슈팅

### 7.1 CUDA 관련 문제

#### `nvcc` 명령어를 찾을 수 없음

**원인:** CUDA Toolkit이 설치되지 않았거나 PATH에 포함되지 않음

```bash
# PATH에 CUDA 경로 추가
echo 'export PATH=/usr/local/cuda/bin:$PATH' >> ~/.bashrc
echo 'export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc
source ~/.bashrc

# 여전히 안 되면 CUDA Toolkit 설치 확인
ls /usr/local/cuda*
# 여러 버전이 있다면 심볼릭 링크 확인
ls -la /usr/local/cuda
```

#### `torch.cuda.is_available()` 이 `False` 반환

**원인 및 해결:**

```bash
# 1. NVIDIA 드라이버 확인
nvidia-smi
# 출력이 없으면 드라이버 설치 필요

# 2. PyTorch CUDA 버전과 시스템 CUDA 버전 비교
python -c "import torch; print(torch.version.cuda)"
nvcc --version
# 버전이 다르면 PyTorch 재설치

# 3. PyTorch가 CPU 버전으로 설치되었는지 확인
python -c "import torch; print(torch.__version__)"
# "+cu121" 같은 접미사가 없으면 CPU 버전임
# GPU 버전으로 재설치
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

#### CUDA 버전 불일치 경고

```bash
# PyTorch의 CUDA 버전
python -c "import torch; print('PyTorch CUDA:', torch.version.cuda)"

# 시스템 CUDA 버전
nvcc --version

# 일반적으로 마이너 버전 차이는 호환됨 (예: 12.1 vs 12.2)
# 메이저 버전이 다르면 (예: 11.x vs 12.x) PyTorch 재설치 필요
```

---

### 7.2 conda 관련 문제

#### `conda: command not found`

```bash
# conda 초기화
eval "$($HOME/miniconda3/bin/conda shell.bash hook)"
conda init bash
source ~/.bashrc
```

#### 환경 활성화 후에도 시스템 Python이 사용됨

```bash
# 현재 활성화된 환경 확인
conda info --envs
echo $CONDA_DEFAULT_ENV

# Python 경로 확인
which python
# /home/<user>/miniconda3/envs/carnerf/bin/python 이어야 함

# 잘못된 경우 환경 재활성화
conda deactivate
conda activate carnerf
```

#### 패키지 충돌

```bash
# 환경을 처음부터 다시 생성
conda deactivate
conda env remove -n carnerf
conda create -n carnerf python=3.10 -y
conda activate carnerf

# 패키지 재설치
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip install -r /home/jjh0709/Project_2026_1/requirements.txt
```

---

### 7.3 COLMAP 빌드 문제

#### CMake 오류: `Eigen3 not found`

```bash
sudo apt-get install -y libeigen3-dev
```

#### CMake 오류: `Ceres Solver not found`

```bash
sudo apt-get install -y libceres-dev
# 또는 소스에서 빌드
```

#### CMake 오류: `CUDA not found`

```bash
# CMake에 CUDA 경로 명시
cmake .. -GNinja \
    -DCMAKE_CUDA_ARCHITECTURES="80" \
    -DCMAKE_BUILD_TYPE=Release \
    -DCUDA_TOOLKIT_ROOT_DIR=/usr/local/cuda-12.1
```

#### 빌드 중 메모리 부족 (OOM)

```bash
# 병렬 빌드 코어 수를 줄임
ninja -j4  # 기본값 대신 4 코어로 제한
```

#### `libcolmap.so: cannot open shared object file`

```bash
# 라이브러리 경로 갱신
sudo ldconfig

# 또는 LD_LIBRARY_PATH에 추가
echo 'export LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH' >> ~/.bashrc
source ~/.bashrc
```

---

### 7.4 Gaussian Splatting 빌드 문제

#### `diff-gaussian-rasterization` 빌드 실패

**오류 메시지:** `error: identifier "AT_CHECK" is undefined`

```bash
# PyTorch 버전 호환성 문제
# 최신 Gaussian Splatting 소스 사용
cd /home/jjh0709/Project_2026_1/third_party/gaussian-splatting
git pull origin main
git submodule update --init --recursive

# 재빌드
pip install submodules/diff-gaussian-rasterization/ --force-reinstall --no-cache-dir
```

**오류 메시지:** `nvcc fatal: Unsupported gpu architecture 'compute_XX'`

```bash
# CUDA_ARCHITECTURES 환경 변수 설정
# A100의 경우
export TORCH_CUDA_ARCH_LIST="8.0"
# RTX 3090의 경우
export TORCH_CUDA_ARCH_LIST="8.6"
# RTX 4090의 경우
export TORCH_CUDA_ARCH_LIST="8.9"

# 여러 GPU를 지원하려면
export TORCH_CUDA_ARCH_LIST="7.0;7.5;8.0;8.6;8.9"

# 재빌드
pip install submodules/diff-gaussian-rasterization/ --force-reinstall --no-cache-dir
```

**오류 메시지:** `error: #error C++17 or later compatible compiler is required`

```bash
# GCC 버전 확인
gcc --version

# GCC 11 이상이 필요함
sudo apt-get install -y gcc-11 g++-11
sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-11 100
sudo update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-11 100
```

#### `simple-knn` 빌드 실패

```bash
# 대부분 diff-gaussian-rasterization과 동일한 원인
# CUDA 아키텍처 설정 후 재빌드
export TORCH_CUDA_ARCH_LIST="8.0"
pip install submodules/simple-knn/ --force-reinstall --no-cache-dir
```

---

### 7.5 일반적인 런타임 문제

#### `ImportError: libGL.so.1: cannot open shared object file`

```bash
# OpenGL 라이브러리 설치
sudo apt-get install -y libgl1-mesa-glx libglib2.0-0
```

#### `OSError: libcudart.so.XX.X: cannot open shared object file`

```bash
# CUDA 런타임 라이브러리 경로 설정
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH

# 영구 설정
echo 'export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc
source ~/.bashrc
```

#### 디스크 공간 부족

```bash
# 현재 디스크 사용량 확인
df -h

# 큰 파일 찾기
du -sh /home/jjh0709/Project_2026_1/data/*

# 불필요한 COLMAP 데이터베이스 정리 (재실행 시 재생성됨)
rm data/colmap_output/*/database.db

# pip 캐시 정리
pip cache purge

# conda 캐시 정리
conda clean --all -y
```

---

### 7.6 빠른 참조: 자주 사용하는 명령어

```bash
# 환경 활성화
conda activate carnerf

# GPU 상태 확인
nvidia-smi

# GPU 메모리 실시간 모니터링
watch -n 1 nvidia-smi

# PyTorch GPU 확인
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"

# COLMAP 버전 확인
colmap --version

# 프로젝트 디렉토리로 이동
cd /home/jjh0709/Project_2026_1

# 전체 파이프라인 실행
python scripts/run_pipeline.py --input data/raw/car_video.mp4 --output data/gaussian_output/car_01
```

---

## 환경 설정 자동화

위의 모든 설정 과정은 `scripts/setup_env.sh` 스크립트를 통해 자동화할 수 있습니다.

```bash
cd /home/jjh0709/Project_2026_1
bash scripts/setup_env.sh
```

이 스크립트는 conda 환경 생성, 의존성 설치, Gaussian Splatting 서브모듈 빌드를
순차적으로 수행합니다. 단, CUDA Toolkit과 COLMAP 소스 빌드는 시스템 권한이
필요하므로 별도로 진행해야 합니다.
