#!/usr/bin/env bash
# 백엔드(FastAPI, 포트 8000) 시작 — start.md 2번의 자동화 스크립트
# 순서: venv 활성화 → Neo4j 점검(0번) → 기존 8000 포트 정리 → uvicorn 실행(포그라운드)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$HOME/.venvs/jbwoori"

if [ ! -f "$VENV/bin/activate" ]; then
  echo "❌ venv 없음: $VENV — start.md 'venv' 섹션의 최초 1회 설치를 먼저 실행하세요." >&2
  exit 1
fi
source "$VENV/bin/activate"

cd "$ROOT/backend"

echo "── 0. Neo4j 연결 점검 ──"
if ! python -m app.scripts.check_neo4j; then
  echo "❌ Neo4j 점검 실패 — start.md 0번 참고 (방화벽/VPN/.env 인증 확인)" >&2
  exit 1
fi

echo "── 기존 8000 포트 프로세스 정리 ──"
lsof -t -i:8000 | xargs kill -9 2>/dev/null || true

echo "── 백엔드 시작: http://localhost:8000 (Ctrl+C로 종료) ──"
exec uvicorn app.main:app --reload --port 8000
