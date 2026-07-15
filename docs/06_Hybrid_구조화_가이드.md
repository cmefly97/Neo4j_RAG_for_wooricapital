# Hybrid 검색 + 데이터 구조화 — 구현/실행 가이드 (2026-06-28, 최종 갱신 2026-06-30)

벡터(bge-m3) + 풀텍스트(cjk)를 RRF로 융합한 **Hybrid 검색**과, 운영기준 표를
값 가진 엔티티로 만드는 **구조화 그래프**를 추가했다. 임베딩은 **사내 게이트웨이 bge-m3**
(`/v1/embeddings`)를 사용한다.

## 추가/변경된 파일
- `backend/app/config.py` — `EMBED_*` 설정 + `embed_base`/`embed_key`(HCX 폴백) 프로퍼티
- `backend/app/llm/embeddings.py` — bge-m3 임베딩 클라이언트(stdlib urllib, 배치)
- `backend/app/search/hybrid.py` — 벡터+풀텍스트 RRF 융합 검색
- `backend/app/search/cypher_qa.py` — `_retrieve()`로 Hybrid 우선, 미비 시 키워드 폴백
- `backend/app/ingestion/structured.py` — 도메인 온톨로지 + LLM 추출(화이트리스트)
- `backend/app/scripts/setup_hybrid.py` — 인덱스 생성 + 청크 임베딩 적재
- `backend/app/scripts/build_structured.py` — 구조화 엔티티/관계 추출·적재
- `.env` / `.env.example` — `EMBED_BASE_URL/API_KEY/MODEL/DIM`

## .env 설정
```
EMBED_BASE_URL=http://223.130.140.218:8001/v1      # 전용 vLLM 서버. /embeddings 는 클라이언트가 부착
EMBED_API_KEY=                                      # 인증 불필요(빈 값). 비우면 HCX_API_KEY 재사용하나 서버가 무시
EMBED_MODEL=BAAI/bge-m3                              # vLLM 모델 ID는 네임스페이스 접두어 필요 (bge-m3 는 404)
EMBED_DIM=1024
```
> 갱신(2026-07-15): 사내 게이트웨이(`namc-aigw`) → **전용 vLLM 서버**(`223.130.140.218:8001`)로 전환.
> 모델 ID도 `bge-m3` → **`BAAI/bge-m3`**(vLLM `/v1/models`의 실제 ID). 차원은 1024로 동일 → 재인덱싱 불필요.

## 실행 순서 (사내망 + venv 활성화)
```bash
source ~/.venvs/jbwoori/bin/activate
cd backend

# 0) 점검
python -m app.scripts.check_neo4j

# 1) 청크 적재(텍스트 보존)  — 아직 안 했다면
python -m app.scripts.ingest_source

# 2) Hybrid 준비: 인덱스(cjk 풀텍스트 + 벡터) 생성 + 청크 bge-m3 임베딩
python -m app.scripts.setup_hybrid
#    (전체 재임베딩: python -m app.scripts.setup_hybrid --reembed)

# 3) 구조화 그래프: 운영기준 표 → 값 가진 엔티티/관계 (LLM 호출)
python -m app.scripts.build_structured --limit 20 --model hyperclova   # 먼저 소량 확인
python -m app.scripts.build_structured --model hyperclova              # 전체

# 4) 검색 품질 비교
python -m app.scripts.eval_queries hyperclova
```
> `setup_hybrid`·`build_structured`·`check_*`·`eval_*` 는 모두 `backend/logs/scripts_*.log`에
> 실행/에러(전체 traceback)를 남긴다. 문제 시 이 로그를 확인.

## 동작 원리
- **검색**: 질문을 bge-m3로 임베딩 → 벡터 인덱스 top-N + cjk 풀텍스트 top-N → **RRF 융합**으로
  상위 청크 선정 → 선택 LLM이 답변 생성. 벡터=의미(표현 달라도 뜻), 풀텍스트=정확 키워드/한글 토큰.
  한↔영 별칭(듀얼=Dual/Dual_C/Dual_O 등)은 풀텍스트 쿼리에서 자동 확장.
- **폴백**: 임베딩 미설정/벡터 인덱스 미완성 시 기존 키워드 청크검색으로 자동 폴백(무중단).
- **구조화**: 청크에서 `Product/RateGrade/Nego/Decision/VehicleCondition/...`(고정 화이트리스트)
  엔티티와 값 속성(예: grade=2, gl_rate="21.0%", max_months=72)을 LLM이 추출 →
  `(:Entity {origin:'structured', ...})-[:REL]->(:Entity)`로 적재(개념 그래프·청크와 분리, 멱등).

## 인덱스 확인용 Cypher (브라우저)
```cypher
SHOW INDEXES YIELD name, type, state WHERE name IN ['chunkText','chunkVec'];
MATCH (c:Chunk) WHERE c.embedding IS NOT NULL RETURN count(c);          // 임베딩 적재 수
MATCH (e:Entity {origin:'structured'}) RETURN e.etype, count(*) ORDER BY count(*) DESC;
MATCH (e:Entity {etype:'RateGrade'}) RETURN e.label, e.grade, e.gl_rate, e.max_months LIMIT 20;
```

## 검증 상태 (2026-06-30 라이브 동작 확인)
네트워크 무관 로직은 오프라인 검증 완료:
- 임베딩 요청 빌드(`/v1/embeddings`, Bearer, bge-m3, 배치) + 1024차원 응답 파싱 ✅
- Lucene 쿼리 동의어 확장(듀얼→Dual/Dual_C/Dual_O) ✅
- RRF 융합(양쪽 등장 문서 최상위) ✅
- 구조화 추출 JSON 파싱 + etype/relation 화이트리스트 + 값 속성 ✅

사내망 라이브 확인 완료: bge-m3 임베딩 189청크 적재, 벡터(chunkVec)+풀텍스트(chunkText) 인덱스
ONLINE, Hybrid 검색 동작, HCX-30B-Text 연결 성공. (구조화 추출 정확도는 표 품질에 따라 계속 보강)

## 주의
- bge-m3 = **1024차원**. 다른 임베딩으로 바꾸면 `EMBED_DIM`과 벡터 인덱스를 함께 변경(`--reembed`).
- HCX Think는 추론 모델이라 느림 → `build_structured`는 `--limit`로 먼저 소량 확인.
- 게이트웨이에 임베딩 엔드포인트가 채팅과 별도일 수 있음 → 위 curl로 먼저 200 확인:
  `curl -X POST $EMBED_BASE_URL/embeddings -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" -d '{"input":"테스트","model":"bge-m3"}'`


---

## 갱신 (2026-06-30) — 추가/변경 요약

### 1) Hybrid 안정화
- **인덱스 이름 자동 탐지**: `hybrid.py`가 `:Chunk(embedding)`/`:Chunk(text)` 위의 ONLINE 인덱스를
  이름과 무관하게 찾는다(`chunkVec`/`chunk_embedding_index` 등 환경차 대응).
- **인덱스 생성 후 ONLINE 대기**: `setup_hybrid`가 `CALL db.awaitIndexes()`로 ONLINE까지 기다린 뒤
  검증(생성 직후 POPULATING 오판으로 중단되던 버그 수정).
- **차원 충돌 주의**: 공유 DB에 타 프로젝트의 `chunk_embedding_index`(3072차원)가 있으면 1024 벡터와
  충돌. 아래 reset으로 격리.

### 2) DB 초기화/격리 + 진단 스크립트
- `app/scripts/reset_db.py` — 모든 노드/관계 + 인덱스/제약 삭제(`--yes` 필수). 공유 영화 데이터·충돌 인덱스 제거용.
  이후 `ingest_source → setup_hybrid → build_structured`로 우리 데이터만 재구축.
- `app/scripts/check_hybrid.py` — 임베딩·인덱스·벡터/풀텍스트 쿼리를 단계별 점검(폴백 원인 진단).

### 3) 구조화 사실의 검색 반영 (#2)
- `cypher_qa._structured_facts(question, kws)` — `origin='structured'` 엔티티를 조회해
  `[참고: 구조화 사실]` 블록으로 컨텍스트에 주입(깨진 표 대신 정밀값). ※ 배치·비중은 아래 "컨텍스트 구성 원칙" 참고
  (문서 발췌 뒤에 보조로 배치, 저점수 컷).
- 답변 결과에 `facts`(엔티티·속성·관계) 포함 → UI에 "🧩 구조화 사실" + "🕸 그래프보기"로 표시.

**매칭 고도화 (2026-06-30, 개선 ①②)**
- ① **매칭 범위 확대** — 라벨뿐 아니라 **값 속성·이웃(관계 대상) 라벨**까지 검색하고
  `label_hits*2 + prop_hits*2 + nbr_hits`로 **점수화해 정렬**(메타 키는 제외).
- ② **질문 의도별 etype 가산점** — `_intent_etypes(question)`가 질문을 보고 우선 유형을 정해
  매칭 etype이 의도와 맞으면 **+5점**. (개월수·취급→`Product/RateGrade`, 금리·등급·네고→`RateGrade/Nego`,
  판정→`Decision`, 엔카·연식·차량→`VehicleCondition`)
- 시그니처가 `_structured_facts(question, kws)`로 변경(읽기전용 단일 Cypher 유지).
- ③ 커버리지는 `build_structured` 전체 적재로 향상(운영 작업).

### 4) 벡터 vs Hybrid 비교 (#3)
- `hybrid.vector_only_retrieve()` + `cypher_qa.search_compare()` + **`POST /search/compare`** 엔드포인트.
- 같은 질문을 벡터 전용 / Hybrid로 각각 검색·답변해 나란히 반환(데모용).

### 5) 검색 과정 상세 노출
- `retrieval_detail.steps`에 **전 과정**을 단계로 기록: 임베딩→벡터검색→풀텍스트검색→RRF →
  구조화 사실 조회→컨텍스트 구성→LLM 답변. UI "🔎 검색 과정 / 쿼리 상세"에 그대로 표시(실제 Cypher 포함).

### 6) 새 LLM: HCX-30B-Text
- `registry.py`에 `hcx30` 추가(label `HCX-30B-Text (hcx-agent-05)`), provider `openai_compat`.
- 사내 게이트웨이 `http://<host>:11000/v1/chat/completions`, thinking 모드.
- `ModelSpec.extra_body` 지원 → factory가 OpenAI SDK `extra_body`로 `chat_template_kwargs:{thinking:true}` 전달.
- `.env`: `HCX30_BASE_URL/HCX30_API_KEY/HCX30_MODEL`. **기본 모델은 HCX-30B-Text**(대화·답변용, 배치 추출은 Qwen 권장).

### 7) 프론트 UI 개편 (`frontend/src/tabs/UserTab.tsx`, `components/FactsGraph.tsx`)
- LLM 답변 **마크다운 렌더링**, 출처 칩 + **클릭 시 관련 청크 팝업**.
- **에러 상태별 안내**(LLM오류/RateLimit/DB미연결/키미설정/결과없음) + 발췌 폴백.
- **벡터 vs Hybrid 2단 비교** 토글, **🧩 구조화 사실 + 🕸 관계 그래프(Cytoscape)** 팝업.
- ⚠️ `src/`의 옛 컴파일 `.js`(App.js 등)는 vite가 `.tsx`보다 먼저 로드하므로 삭제해야 최신 UI 반영.

### 8) 운영/문서
- venv는 홈(`~/.venvs/jbwoori`)에 두고 **터미널마다 활성화**(README/start/CLAUDE 상단 배너).
- Docker 의존 제거(리모트 Neo4j 사용). `.env`만 사용(.env.example는 예제).
- 발표자료 `presentation.html`(16장) 추가.

### 추가된 주요 명령 (사내망 + venv)
```bash
python -m app.scripts.reset_db --yes        # (필요시) DB 초기화·격리
python -m app.scripts.check_hybrid          # Hybrid 동작/폴백 원인 진단
python -m app.scripts.check_llm hcx30        # HCX-30B-Text 연결 점검
# 라이브: uvicorn app.main:app --reload --port 8000  +  frontend: npm run dev
```

---

## 검색 품질의 핵심 — 컨텍스트 구성 원칙 ★ (2026-06-30)

정밀 검색만으로는 정답이 보장되지 않는다. 답변 정확도는 근거를 **무엇을·어떤 순서로·어떤 권위로**
LLM 컨텍스트에 담느냐에 크게 좌우된다. 구조화 사실은 **고정밀일 때만 이득**이고, 저품질·부분적이면
청크 원문의 뉘앙스를 가려 오답을 낸다(예: "프로모션 법인 가능?"의 `(개인고객 限)`은 청크에만 존재).

적용(코드 반영):
1. `_structured_facts` — **저점수 컷**(`score ≥ 3`, 상위 8)으로 주변적 fact 제외.
2. `_build_context` — **[문서 발췌] 먼저(1차 근거)**, **[참고: 구조화 사실 — 보조]는 뒤**.
   프롬프트는 "자료만 근거·환각 금지·출처 명시"로 단순화됨(발췌 우선 지시는 컨텍스트 라벨
   `[참고: 구조화 사실 — 보조, 발췌와 상충 시 발췌 우선]`에 유지).

**답변 스타일 옵션 (2026-07-02)**
- `ANSWER_STYLES` 3종: `standard`(기본) · `concise`(간단히, 1~2문장) · `detailed`(자세히·상담사 톤).
- `/search`·`/search/compare`의 `answer_mode` 파라미터로 선택(UI "✍️ 답변 스타일" 드롭다운), 미지정=기본.
- 공통 가드(자료 근거·환각 금지·출처)는 모든 스타일 동일, 첫 지시어만 변경.
3. `search_compare` — 구조화 사실을 양쪽에 동일 적용 → **비교 뷰 Hybrid = 기본 검색과 동일 파이프라인**.

원칙: 1차 근거는 원문(청크), 그래프 사실은 정밀값·검증 보조. 구조화는 정밀도를 *보강*하되 원문을 *대체하지 않는다*.
