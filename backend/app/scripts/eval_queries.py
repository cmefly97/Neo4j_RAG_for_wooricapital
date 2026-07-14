"""모델 비교 평가(라이브) + 실행/에러 자동 로깅(backend/logs/scripts_*.log).

동일 질의셋을 여러 모델로 실행해 결과를 나란히 비교. 실제 LLM/Neo4j 연결 필요.
실행:
    cd backend && python -m app.scripts.eval_queries                 # 사용 가능한 모든 모델
    cd backend && python -m app.scripts.eval_queries claude hyperclova
결과: 콘솔/로그 + eval_results/eval_YYYY-MM-DD_HHMM.md
"""
import sys
import datetime
from pathlib import Path
from app.scripts._runlog import run, log_exc

# 샘플 질의셋 + 기대 답안(채점 기준)
QUESTIONS = [
    {"q": "론/할부 상품 취급 가능 개월수가 어떻게돼?",
     "expected": "12~72개월"},
    {"q": "론/할부 나이스 885점, 금리등급 2등급일 때 적용 될 수 있는 최저 금리 알려줘",
     "expected": "금리등급 2등급 21.0% G/L금리, NICE 1등급이므로 1% 네고. "
                 "거점장 네고 11.0%, 증빙 네고 15.0%, HJ 네고 18.0%"},
    {"q": "듀얼상품 금리등급 몇등급까지 취급 가능해?",
     "expected": "Dual_C: 내국인 7등급/외국인 7등급, Dual_O: 내국인 7등급/외국인 7등급"},
    {"q": "엔카 슬라이딩 가능해?",
     "expected": "국산/수입차 & 19년식 이내 & 주행거리 연평균 500만km 이하, "
                 "카히스토리 사고 33백만원 이내 & 특수사고(전손·침수·도난) 없는 차량"},
    {"q": "신용구제 상품에서 신용회복, 개인회생 고객인데 판정값이 R 판정이야",
     "expected": "R판정은 '필터링 취급 불가' 대상"},
]


def run_model(log, search, model_id: str, label: str) -> list[dict]:
    rows = []
    log.info("=== 모델 %s (id=%s) ===", label, model_id)
    for i, item in enumerate(QUESTIONS, 1):
        log.info("[%d] Q=%s | 기대=%s", i, item["q"], item["expected"])
        try:
            r = search(item["q"], model_id)
            ans = (r.get("answer") or "").strip()
            cy = (r.get("cypher") or "").strip()
            n = len(r.get("rows", []))
            log.info("[%d] 답변=%s", i, ans[:300])
            log.info("[%d] rows=%d cypher=%s model_used=%s", i, n, cy[:160],
                     r.get("model_used"))
            rows.append({**item, "answer": ans, "cypher": cy, "rows": n,
                         "model_used": r.get("model_used")})
        except Exception as e:  # noqa: BLE001
            log_exc(log, f"[{i}] 질의 실패")
            rows.append({**item, "error": f"{type(e).__name__}: {e}"})
    return rows


def to_markdown(all_results: dict) -> str:
    out = ["# 모델 비교 평가 결과", f"_{datetime.datetime.now():%Y-%m-%d %H:%M}_\n"]
    for i, item in enumerate(QUESTIONS, 1):
        out.append(f"## Q{i}. {item['q']}")
        out.append(f"**기대 답안**: {item['expected']}\n")
        for label, res in all_results.items():
            r = res[i - 1]
            if "error" in r:
                out.append(f"- **{label}**: ❌ {r['error']}")
            else:
                out.append(f"- **{label}** (rows={r['rows']}): {r['answer'][:400]}")
                out.append(f"  - Cypher: `{r['cypher'][:200]}`")
        out.append("")
    return "\n".join(out)


def _body(log):
    try:
        from app.search.cypher_qa import search
        from app.llm import list_models
    except ModuleNotFoundError as e:
        log_exc(log, f"의존성 누락: {e.name}")
        log.error("→ 해결: cd backend && pip install -r requirements.txt. 누락=%s", e.name)
        return 1

    avail = [m for m in list_models() if m["available"]]
    sel = sys.argv[1:]
    targets = [m for m in avail if m["id"] in sel] if sel else avail
    if not targets:
        log.error("실행 가능한 모델이 없습니다. (.env 키/사내망 확인)")
        return 1

    all_results = {}
    for m in targets:
        all_results[m["label"]] = run_model(log, search, m["id"], m["label"])

    out_dir = Path("eval_results"); out_dir.mkdir(exist_ok=True)
    fp = out_dir / f"eval_{datetime.datetime.now():%Y-%m-%d_%H%M}.md"
    fp.write_text(to_markdown(all_results), encoding="utf-8")
    log.info("결과 저장: %s", fp)
    return 0


if __name__ == "__main__":
    sys.exit(run("eval_queries", _body))
