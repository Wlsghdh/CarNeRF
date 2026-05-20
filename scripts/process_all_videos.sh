#!/bin/bash
# CarNeRF — 모든 업로드 영상을 FastGS HQ 파이프라인으로 순차 처리
# 출력 로그: /tmp/process_all_videos.log

set -u
cd /home/jjh0709/Project_2026_1
source /opt/miniconda3/etc/profile.d/conda.sh
conda activate jjh

PYTHON="/home/jjh0709/.conda/envs/jjh/bin/python"
LOG="/tmp/process_all_videos.log"

# (영상경로, 프로젝트명) 쌍 — 이미 학습된 NF소나타 제외
VIDEOS=(
  "KakaoTalk_Video_2026-05-07-21-52-14.mp4|car_may07"
  "data/2번째 차량 사진.mp4|car_2nd"
  "videos/KakaoTalk_Video_2026-05-12-12-36-30.mp4|car_may12_a"
  "videos/KakaoTalk_Video_2026-05-12-12-36-41.mp4|car_may12_b"
  "videos/KakaoTalk_Video_2026-05-12-12-37-00.mp4|car_may12_c"
)

export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1

echo "=== CarNeRF Batch Pipeline Start: $(date) ===" | tee -a "$LOG"

idx=0
total=${#VIDEOS[@]}
for entry in "${VIDEOS[@]}"; do
  idx=$((idx + 1))
  video="${entry%|*}"
  name="${entry#*|}"
  echo "" | tee -a "$LOG"
  echo "===== [$idx/$total] $name <- $video =====" | tee -a "$LOG"
  start=$(date +%s)

  "$PYTHON" scripts/run_pipeline.py \
    --input "$video" \
    --name "$name" \
    --hq \
    --engine fastgs \
    --max_frames 200 \
    --iterations 30000 \
    --max_gaussians 1500000 2>&1 | tee -a "$LOG"
  rc=${PIPESTATUS[0]}

  elapsed=$(($(date +%s) - start))
  if [ "$rc" -eq 0 ]; then
    echo "[$idx/$total] $name 성공 ($(($elapsed/60))분 $(($elapsed%60))초)" | tee -a "$LOG"
  else
    echo "[$idx/$total] $name 실패 (rc=$rc, $(($elapsed/60))분 $(($elapsed%60))초)" | tee -a "$LOG"
  fi
done

echo "" | tee -a "$LOG"
echo "=== Batch 완료: $(date) ===" | tee -a "$LOG"
