# 우리캐피탈 오토운영팀 지식그래프 검색 (PoC)

> 🟢 **터미널 새로 열 때마다 제일 먼저:** `source ~/.venvs/jbwoori/bin/activate` (프롬프트에 `(jbwoori)` 확인). 안 하면 `ModuleNotFoundError` 발생.

기존 벡터DB 기반 오토운영팀 챗봇을 **온톨로지/지식그래프(KG) 기반**으로 전환했을 때의
개선 가능성을 검증하는 Phase 1 PoC입니다.

- **데이터**: FAQ(xlsx) · 규정(docx) · 운영기준(pdf/md) — 비슷한 상품을 다루는 3종 출처
- **검색 방식**: 자연어 → Cypher 생성(LLM) → Neo4j 조회 → 답변 (+ Cypher 뷰 노출)
- **LLM 선택**: UI에서 모델 전환 — 기본 **Qwen3.6-35B-A3B**, 옵션 **Claude Opus 4.8**, **HyperCLOVA X Think 32B**
- **UI**: 사용자 탭(모델 선택/검색/답변/Cypher) · 관리자 탭(업로드/문서리스트/그래프 뷰)

> 상세 설계는 [`docs/02_Phase1_PoC_설계서.md`](docs/02_Phase1_PoC_설계서.md),
> 전체 아키텍처는 [`docs/01_전체_아키텍처_설계문서.md`](docs/01_전체_아키텍처_설계문서.md) 참고.

## 프로젝트 구조
```
.
├── docs/                 # 설계 문서
├── source/               # 원본 문서 (xlsx/docx/pdf/md) + 온톨로지 메모
├── graph_output/         # 기 추출된 그래프 (graph.json, GRAPH_REPORT.md)
├── backend/              # FastAPI + Neo4j + 파이프라인/검색
│   └── app/
│       ├── api/          # admin(업로드/리스트/그래프), search(자연어 검색)
│       ├── ingestion/    # 형식별 파서 · 추출 · 온톨로지
│       ├── search/       # NL→Cypher→답변
│       ├── scripts/      # graph.json → Neo4j 적재
│       └── neo4j_client.py
└── frontend/             # React + TS (Cytoscape 그래프 뷰)
```

## 빠른 시작

### 0) 가상환경(venv) 설정 — 필수

> ⚠️ **venv는 홈(`~/.venvs/jbwoori`)에 만든다.** macOS Homebrew 파이썬은 외부 관리(externally-managed)
> 라 전역 설치가 막히고, 클라우드 동기화 폴더 안에선 심볼릭 링크가 깨져 생성이 실패한다.
> 그래서 venv는 홈에 두고 코드만 프로젝트 폴더에서 실행한다.
> **그리고 터미널을 새로 열 때마다 `source ~/.venvs/jbwoori/bin/activate` 를 제일 먼저 실행한다.**

```bash
# 최초 1회만 (홈에 venv 생성 + 설치)
python -m venv ~/.venvs/jbwoori
source ~/.venvs/jbwoori/bin/activate
python -m pip install --upgrade pip
cd backend && python -m pip install -r requirements.txt
python -c "import pydantic_settings; print('ok')"   # ok 뜨면 성공

# 터미널을 새로 열 때마다 (프롬프트에 (jbwoori) 보이면 활성화됨)
source ~/.venvs/jbwoori/bin/activate
cd backend
```

### 1) Neo4j 연결 (리모트 서버)
**리모트 Neo4j 서버**에 연결한다(로컬 설치 불필요). 접속 정보는 `.env`에 둔다.
> `.env`는 이미 존재하며 이후 이 파일만 사용·갱신한다. (`.env.example`은 최초 예제일 뿐, 복사 불필요.)
```bash
# .env 의 NEO4J_URI/USER/PASSWORD, LLM 키를 확인/수정
# 예) NEO4J_URI=bolt://223.130.140.218:7687  (Bolt 포트 7687)
cd backend && python -m app.scripts.check_neo4j   # 연결 확인 (✅ 떠야 진행)
```
- 연결 실패 시: 포트 도달 `nc -z -w5 <host> 7687`, 방화벽/사내망(VPN) 허용, 인증(USER/PASSWORD) 확인
- TLS 필요 서버면 `NEO4J_URI`를 `bolt+s://...` 또는 `neo4j+s://...` 로

### 2) 백엔드 + 기존 그래프 적재
```bash
cd backend     # venv 활성화 상태(위 0번)에서
# source 문서 → 청크 그래프를 (리모트) Neo4j에 적재
python -m app.scripts.ingest_source
# (선택) 기 추출된 개념 그래프 적재
python -m app.scripts.load_graph_json ../graph_output/graph.json
# API 실행
uvicorn app.main:app --reload --port 8000
```

### 3) 프론트엔드
```bash
cd frontend
npm install
npm run dev   # http://localhost:5173
```


## LLM 연결 테스트

`.env`에 키를 넣은 뒤, 등록된 모델에 실제로 짧은 질의를 보내 연결을 점검한다.

```bash
cd backend     # venv 활성화 상태(위 0번)에서
python -m app.scripts.check_llm           # 전체 모델 점검
python -m app.scripts.check_llm claude    # 특정 모델만
# 또는 pytest
pytest tests/test_llm_connection.py -v -s
```

- **Claude**: 일반 인터넷이면 동작 (api.anthropic.com)
- **HyperCLOVA X**: 사내 게이트웨이(`namc-aigw.io.naver.com`) 대상 → **사내망/VPN에서 실행**해야 도달
- 키 미설정·엔드포인트 도달 불가 시 자동으로 건너뛰거나 명확한 사유를 출력한다.

## PoC 범위 / 현재 상태
- [x] 프로젝트 골격, Neo4j 적재 스크립트(graph.json), API/UI 스켈레톤
- [x] LLM 선택 기능: 레지스트리/팩토리, `/models`·`/search(model)`, 사용자 탭 모델 드롭다운
- [ ] 형식별 파서 구현 (`backend/app/ingestion/parsers.py`)
- [ ] LLM 추출(`extract.py`) · NL→Cypher 체인(`search/cypher_qa.py::_llm_nl_to_cypher_and_answer`) 실제 연동
- [ ] 온톨로지 확정 (`ingestion/ontology.py` ↔ `graph_output/GRAPH_REPORT.md`)

## 검증용 샘플 질의
- 론/할부 상품 취급 가능 개월수가 어떻게 돼?
- 듀얼상품 금리등급 몇 등급까지 취급 가능해?
- 엔카 슬라이딩 가능해?
- 신용구제 상품에서 개인회생 고객, 판정값이 R 판정이야
