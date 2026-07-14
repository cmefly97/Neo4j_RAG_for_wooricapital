#!/usr/bin/env bash
# 프론트엔드(포트 5173) 종료 — 정상 종료(TERM) 후 남아 있으면 강제 종료(KILL)
set -uo pipefail

PIDS="$(lsof -t -i:5173 2>/dev/null || true)"
if [ -z "$PIDS" ]; then
  echo "프론트엔드(5173) 실행 중이 아닙니다."
  exit 0
fi

echo "종료 대상 PID: $PIDS"
kill $PIDS 2>/dev/null || true
sleep 1

REMAIN="$(lsof -t -i:5173 2>/dev/null || true)"
if [ -n "$REMAIN" ]; then
  echo "정상 종료 안 됨 → 강제 종료: $REMAIN"
  kill -9 $REMAIN 2>/dev/null || true
fi

echo "✅ 프론트엔드 종료 완료"
