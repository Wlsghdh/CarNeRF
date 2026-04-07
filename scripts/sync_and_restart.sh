#!/bin/bash
# CarNeRF 원격 트리거 동기화 + 서버 재시작
# 사용법: bash scripts/sync_and_restart.sh

set -e
cd "$(dirname "$0")/.."

echo "=== git pull ==="
git pull --rebase

echo "=== 서버 재시작 ==="
fuser -k 5199/tcp 2>/dev/null || true
sleep 1
rm -f backend/carnerf.db

source /opt/miniconda3/etc/profile.d/conda.sh
conda activate jjh
cd backend
nohup python run.py > /tmp/carnerf_server.log 2>&1 &
SERVER_PID=$!
echo "서버 PID: $SERVER_PID"

sleep 4
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5199/ 2>/dev/null)
if [ "$HTTP_CODE" = "200" ]; then
  echo "✓ 서버 정상 (200 OK)"
else
  echo "✗ 서버 오류 (HTTP $HTTP_CODE)"
  tail -20 /tmp/carnerf_server.log
  exit 1
fi
