# START — 실행 순서 & 항상 점검할 것

> 🟢 **터미널 새로 열 때마다 제일 먼저:** `source ~/.venvs/jbwoori/bin/activate`
> → 프롬프트 앞에 `(jbwoori)` 가 보여야 함. 없으면 시스템 파이썬이라 `ModuleNotFoundError`(pydantic_settings 등) 발생.

> ⚠️ 명령 복사 시 **`#` 뒤 주석은 빼고** 명령만 붙여넣을 것. (zsh는 인라인 주석을 인자로 인식)
> 백엔드와 프론트는 **각각 다른 터미널**에서 실행. `cd frontend`는 **프로젝트 루트**에서.

> ⚠️ **작업/검색 전 항상 1번(Neo4j)부터 점검한다.** Neo4j가 꺼져 있으면 검색·적재 전부 실패한다.

## venv(가상환경) — 항상 제일 먼저
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

## 0. Neo4j 연결 점검 (제일 먼저)
> 리모트 Neo4j 서버 사용 중(`.env`의 `NEO4J_URI`). 로컬 설치 불필요.
```bash
cd backend
python -m app.scripts.check_neo4j
```
`check_neo4j`가 ✅ 나오면 진행. ❌면:
```bash
nc -z -w5 223.130.140.218 7687     # 서버/포트 도달 확인 (Bolt=7687)
```
- 도달 불가 → 방화벽/사내망(VPN)에서 해당 IP:7687 허용 필요
- 인증 실패 → `.env`의 NEO4J_USER/PASSWORD 확인
- TLS 필요 서버 → `NEO4J_URI`를 `bolt+s://...` 또는 `neo4j+s://...` 로 변경

## 1. 데이터 적재
```bash
cd backend
# (A) source 문서 → 청크 그래프 (실제 값 포함, LLM 불필요) — 권장
python -m app.scripts.ingest_source
# (옵션) 개념 엔티티까지 LLM 추출(사내망): python -m app.scripts.ingest_source --llm
# (B) 기존 개념 그래프(graph.json) 적재 (선택)
python -m app.scripts.load_graph_json ../graph_output/graph.json
```

## 2. 백엔드 / 프론트 (각각 다른 터미널)

> 💡 **스크립트로 실행/종료** (프로젝트 루트에서, venv 활성화·Neo4j 점검·포트 정리까지 자동):
> ```bash
> ./scripts/backend-start.sh    # 터미널 1: Neo4j 점검 → 8000 정리 → uvicorn
> ./scripts/frontend-start.sh   # 터미널 2: npm install(필요시) → 5173 정리 → npm run dev
> ./scripts/backend-stop.sh     # 백엔드 종료
> ./scripts/frontend-stop.sh    # 프론트엔드 종료
> ```
> 아래는 수동 실행 방법.

터미널 1 — 백엔드 (프로젝트 루트에서):
```bash
cd backend
lsof -t -i:8000 | xargs kill -9 2>/dev/null || true
uvicorn app.main:app --reload --port 8000
```

터미널 2 — 프론트엔드 (프로젝트 루트에서):
```bash
cd frontend
npm run dev
```

## 3. 동작 점검
```bash
# 백엔드 단독
curl -s -X POST localhost:8000/search -H 'Content-Type: application/json' \
  -d '{"question":"엔카 슬라이딩 가능해?","model":"hyperclova"}'
# 모델 비교
python -m app.scripts.eval_queries hyperclova
```

## 로그
- API 서버: `backend/logs/YYYY-MM-DD.log` (콘솔에도 출력). 검색/업로드 등 액션·에러 기록.
- 스크립트(check_neo4j, ingest_source 등): `backend/logs/scripts_YYYY-MM-DD.log` (별도 파일).

## 자주 나는 문제
- `Connection refused` / `ServiceUnavailable` → 리모트 Neo4j 도달 불가 → 0번 점검(포트/방화벽/VPN/인증).
- 검색해도 로그 없음 → uvicorn이 옛 코드 → uvicorn 재시작, 브라우저 Cmd+Shift+R.
- Claude 크레딧 부족(400) → HyperCLOVA X 선택해서 사용.
