#!/usr/bin/env bash
# CarNeRF Flutter Web 배포: 빌드 → 백엔드 정적폴더로 동기화
# 사용: bash scripts/deploy_web.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FLUTTER_DIR="$ROOT/carnerf-flutter"
WEB_OUT="$ROOT/backend/app/static/flutter_web"
API_BASE="${API_BASE_URL:-http://223.195.111.31:5199}"

echo "▸ Flutter Web 빌드 시작 (API=$API_BASE)"
cd "$FLUTTER_DIR"
flutter build web --release \
  --base-href "/app/" \
  --dart-define=API_BASE_URL="$API_BASE"

echo "▸ $WEB_OUT 으로 동기화"
mkdir -p "$WEB_OUT"
rsync -a --delete "$FLUTTER_DIR/build/web/" "$WEB_OUT/"

echo ""
echo "✅ 배포 완료"
echo "   미리보기:  $API_BASE/preview"
echo "   풀스크린:  $API_BASE/app"
echo ""
echo "💡 팀원은 F5 새로고침으로 새 버전 확인"
