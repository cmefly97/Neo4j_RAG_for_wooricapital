#!/usr/bin/env bash
# 프론트엔드(Vite, 포트 5173) 시작 — start.md 2번의 자동화 스크립트
# 순서: node_modules 확인(없으면 설치) → 기존 5173 포트 정리 → npm run dev(포그라운드)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/frontend"

if [ ! -d node_modules ]; then
  echo "── node_modules 없음 → npm install ──"
  npm install
fi

echo "── 기존 5173 포트 프로세스 정리 ──"
lsof -t -i:5173 | xargs kill -9 2>/dev/null || true

echo "── 프론트엔드 시작: http://localhost:5173 (Ctrl+C로 종료) ──"
exec npm run dev
