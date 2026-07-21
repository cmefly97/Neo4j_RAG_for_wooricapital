# CLAUDE.md

> ⚠️ **작업 시작 전 항상 Neo4j부터 점검한다.** `start.md` 0번 참고 →
> `cd backend && python -m app.scripts.check_neo4j`.
> **리모트 Neo4j 서버 사용**(`.env`의 NEO4J_URI, Bolt 7687). 로컬 설치/Docker 불필요.
> 연결 안 되면 검색·적재가 전부 실패한다(방화벽/VPN/인증 확인).
>
> 🟢 **venv는 홈(`~/.venvs/jbwoori`)에 만들고, 터미널마다 `source ~/.venvs/jbwoori/bin/activate` 를 제일 먼저 실행한다.**
> (Homebrew 파이썬은 externally-managed라 전역 설치 불가. 활성화 안 하면 `ModuleNotFoundError` 발생.)

이 파일은 Claude Code가 이 저장소에서 작업할 때 참고하는 가이드입니다.

## 프로젝트 개요
우리캐피탈 오토운영팀의 기존 벡터DB 챗봇을 **지식그래프(KG) 기반 검색**으로 전환하는 PoC.
핵심 가설: 비슷한 상품을 다루는 3종 출처(FAQ/규정/운영기준)에서, 그래프 구조가
벡터 검색 대비 멀티홉·교차참조 질의에 강점을 보이는지 검증한다.

## 아키텍처
- **backend/** FastAPI. 두 흐름으로 나뉜다.
  - 관리자(`app/api/admin.py`): 업로드 → 파싱/추출 → Neo4j 적재 / 문서리스트 / 그래프 뷰
  - 사용자(`app/api/search.py` → `app/search/cypher_qa.py`): 자연어 → Cypher → 답변
  - **LLM**: `app/llm/`(registry+factory). `/models`로 목록 제공, `/search`의 `model` 파라미터로 선택.
    **HCX-30B-Text(hcx-agent-06, 사내 게이트웨이) 단일 운영.** 다른 모델(Qwen·HyperCLOVA X·Claude)은
    모델 관리 부담으로 제거됨(2026-07-20). 다시 추가하려면 `app/llm/registry.py`의 MODELS에 1개 추가. 키는 `.env`.
- **Neo4j** 단일 저장소. 모든 엔티티는 `:Entity {id, label, norm_label, file_type, source_file, community}`,
  관계는 `:REL {relation, confidence, confidence_score, source_file, weight}` (relation은 속성으로 저장).
- **frontend/** React + TS + Cytoscape. 탭 2개(UserTab, AdminTab).

## 데이터 흐름의 출발점
`graph_output/graph.json` (networkx node-link 포맷)에 이미 86노드/113엣지가 추출돼 있다.
`backend/app/scripts/load_graph_json.py`가 이를 Neo4j에 적재한다(개념 그래프).
문서 본문은 `app/scripts/ingest_source.py`가 source/ 파일을 파싱→청크화→적재한다
(:Document/:Chunk, 텍스트 보존). **실제 값(취급개월수·금리·판정 등)은 Chunk.text로 검색**한다.

## 주요 명령어
```bash
python -m app.scripts.check_neo4j                      # Neo4j(리모트) 점검(항상 먼저)
source ~/.venvs/jbwoori/bin/activate              # venv(홈) 활성화 — 터미널마다
cd backend && python -m pip install -r requirements.txt
python -m app.scripts.ingest_source                   # source 문서 → 청크 그래프 적재
python -m app.scripts.load_graph_json ../graph_output/graph.json   # (선택) 개념 그래프
uvicorn app.main:app --reload --port 8000              # API
cd frontend && npm install && npm run dev              # UI (5173)
```

## 코딩 규약 / 주의사항
- **읽기 전용 가드**: 사용자 검색 경로는 반드시 `Neo4jClient.run_readonly()` 사용
  (쓰기 키워드 차단). 적재 등 쓰기는 `run()` 사용.
- **출처 추적**: 모든 노드/엣지에 `source_file`을 유지한다. 답변에는 출처를 노출한다.
- **xlsx는 LLM 추출이 아니라 결정적 매핑**으로 처리한다 (시트→엔티티, 컬럼→속성/관계, 행→인스턴스).
- **온톨로지**(`app/ingestion/ontology.py`)는 `graph_output/GRAPH_REPORT.md`의 실제
  god-node/community 결과를 보며 조정한다. 임의 확장 금지 — 스키마 드리프트 방지.
- 비밀값은 `.env`에만 둔다(커밋 금지). `.env.example`은 최초 예제일 뿐, 이후엔 `.env`만 사용·갱신한다.
- 한국어 도메인 용어(론/할부/듀얼상품/잔가율/엔카 슬라이딩 등)는 번역하지 말고 그대로 사용.

## 로깅 (사용자 액션 추적)
- **날짜별 로그 파일**: `backend/logs/YYYY-MM-DD.log` (자정 기준 자동 분리). `app/logging_setup.py`의
  `DailyFileHandler`가 처리하며 콘솔(uvicorn 터미널)에도 동시 출력된다.
- **액션 로깅**: 엔드포인트에서 `log_action(action, **fields)` 호출로 사용자 액션 1건을 구조화 기록.
  형식: `시각 | LEVEL | ACTION <이름> | key=value ...`
  - 검색: `SEARCH_REQUEST`(질문/모델) → `SEARCH_OK`(rows/cypher) 또는 `SEARCH_ERROR`(에러)
  - 관리자: `UPLOAD` / `UPLOAD_REJECT` / `DOCUMENTS_LIST` / `REPROCESS` / `DELETE` / `GRAPH_VIEW`
  - 노드: `NODE_DETAIL`
- **요청/예외 로깅**: `main.py`의 미들웨어가 모든 요청을 `REQ <메서드> <경로> | <상태> | <ms>`로 기록하고,
  전역 예외 핸들러가 미처리 예외를 traceback과 함께 남긴 뒤 `{"error": "..."}` JSON(HTTP 500)으로 응답한다.
- **프론트 가시화**: `frontend/src/api/client.ts`가 모든 호출을 콘솔에 로깅하고, 응답 에러/네트워크
  실패를 throw → 각 탭이 화면 상단에 에러 박스로 표시한다. (브라우저 콘솔에도 `[API]/[USER]/[ADMIN]` 로그)
- 새 엔드포인트/액션을 추가하면 반드시 `log_action(...)`을 호출해 추적 일관성을 유지한다.
- `logs/`는 `.gitignore` 대상(커밋 금지).

## 미구현(TODO) — PoC 완료까지
1. ~~`app/ingestion/parsers.py` — md/docx/pdf/xlsx 파서~~ (구현됨)
2. ~~`app/ingestion/extract.py` — 청크 그래프(결정적) + LLM 엔티티 추출~~ (구현됨, LLM 추출은 사내망 실행)
3. `app/search/cypher_qa.py::_llm_nl_to_cypher_and_answer` — 선택 모델(`build_chat_model`)로
   NL→Cypher 생성 + 답변 생성 (GraphCypherQAChain 등). 현재 LLM 미설정/미구현 시 라벨 부분일치 폴백.
4. 새 모델 추가는 `app/llm/registry.py`의 MODELS에 항목 1개 추가 (확장성 유지).

## 검증
- `docs/02_Phase1_PoC_설계서.md`의 "성공 기준"과 샘플 질의셋으로 검증한다.
- 적재 직후 `MATCH (n) RETURN count(n)` 으로 노드 수(=86) 확인.
