# Graph Report - raw/우리캐피탈/2.오토운영팀 온톨로지  (2026-06-22)

## Corpus Check
- 6 files · ~9,000 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 86 nodes · 113 edges · 7 communities detected
- Extraction: 93% EXTRACTED · 6% INFERRED · 1% AMBIGUOUS · INFERRED: 7 edges (avg confidence: 0.76)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]

## God Nodes (most connected - your core abstractions)
1. `중고승용 상품운영기준` - 19 edges
2. `중고차승용 심사운영기준(E09003)` - 17 edges
3. `중고 오토리스 심사운영기준(E09024)` - 15 edges
4. `중고 오토리스 상품운영기준` - 13 edges
5. `중형트럭 시범운영기준` - 11 edges
6. `오토운영팀` - 5 edges
7. `운영기준 데이터 (월별 금리·운영기준)` - 5 edges
8. `심사기준 (CSS)` - 5 edges
9. `잔가율 (리스 잔가)` - 4 edges
10. `채권서류 징구기준 (기본·증빙서류)` - 4 edges

## Surprising Connections (you probably didn't know these)
- `금융리스` --has_class--> `중고 오토리스 상품운영기준`  [EXTRACTED]
  raw/우리캐피탈/2.오토운영팀 온톨로지/8_샘플_중고리스 운영기준(변경).pdf → raw/우리캐피탈/2.오토운영팀 온톨로지/5_재고금융_운영자금심사운영기준.md
- `성능상태점검기록부 확인` --has_property--> `중고 오토리스 상품운영기준`  [EXTRACTED]
  raw/우리캐피탈/2.오토운영팀 온톨로지/8_샘플_중고리스 운영기준(변경).pdf → raw/우리캐피탈/2.오토운영팀 온톨로지/5_재고금융_운영자금심사운영기준.md
- `중고승용 상품운영기준` --references--> `대출한도`  [EXTRACTED]
  raw/우리캐피탈/2.오토운영팀 온톨로지/7_중고차승용심사운영기준.md → raw/우리캐피탈/2.오토운영팀 온톨로지/10_샘플_중형트럭 시범운영기준.pdf
- `론 (구입대출)` --has_class--> `중고승용 상품운영기준`  [EXTRACTED]
  raw/우리캐피탈/2.오토운영팀 온톨로지/9_샘플_중고승용 상품운영기준.pdf → raw/우리캐피탈/2.오토운영팀 온톨로지/7_중고차승용심사운영기준.md
- `중고승용` --applies_to--> `중고승용 상품운영기준`  [EXTRACTED]
  raw/우리캐피탈/2.오토운영팀 온톨로지/9_샘플_중고승용 상품운영기준.pdf → raw/우리캐피탈/2.오토운영팀 온톨로지/7_중고차승용심사운영기준.md

## Hyperedges (group relationships)
- **중고차승용 대출한도 심사체계 (LTV·신용평점·상환능력·한도CAP)** — ltv_criteria, loan_limit_cap, credit_score, repayment_ability, used_car_practice_guideline [INFERRED 0.80]
- **채권서류 심사체계 (서류징구·발급기간·정보확인기관)** — required_documents, document_issuance_period, jabis_system [INFERRED 0.70]

## Communities

### Community 0 - "Community 0"
Cohesion: 0.15
Nodes (20): 전결권자별 전결금액 기준 (지점/본사), 카히스토리 적용기준 (사고·전손·침수·도난), 채권확보·차량설정 기준 (설정률 50%/60%), 고객신용하락 발생시 업무처리 (상담 후 5영업일), DB시세, 채권서류 발급기간 (1개월 이내, 법인인감 3개월), 취급가능고객 (개인/개인사업자/법인/외국인), 대상물품·대상차종 (연식·차종 기준) (+12 more)

### Community 1 - "Community 1"
Cohesion: 0.13
Nodes (17): 신용회복 취급기준, 신용구제 상품, 심사기준 (CSS), 듀얼상품 (Dual Offer), 중도상환 수수료율, 엔카 슬라이딩, 엔카 무수수료 상품, ESM 딜러구입대출 (+9 more)

### Community 2 - "Community 2"
Cohesion: 0.15
Nodes (13): 국산리스 잔가율표, 수입리스 잔가율표, 개인사업자 사업자 기준, 개인회생 취급기준, 대출한도, 중형트럭, 중형트럭 시범운영기준, 주행거리 제한 (LTV 적용) (+5 more)

### Community 3 - "Community 3"
Cohesion: 0.18
Nodes (12): 지점/본사 NEGO 기준, 운용리스 IRR (G/L IRR), 중고리스 취급제한차종, 취급 한도CAP 기준, 운용리스, 견적서 직원 제공 원칙 (딜러→고객 X), 근거: 금소법상 판매 대리·중개(모집인 등록) 준수, 근거: 차량 컨디션(부식·훼손)에 따른 원상회복비 발생 방지 (+4 more)

### Community 4 - "Community 4"
Cohesion: 0.22
Nodes (11): 에이전트(AI Agent), 오토운영팀, 오토운영팀 챗봇, FAQ 데이터 (지점 일반문의), 운영기준 데이터 (월별 금리·운영기준), 규정 데이터 (업무 핵심 내부 규정), 그래프DB, 재고금융 (운영자금심사) (+3 more)

### Community 5 - "Community 5"
Cohesion: 0.29
Nodes (7): 신용평점 (NICE 차주분포), 대출금 최고한도 기준 (신용평점·상환능력별 한도CAP), LTV 적용기준 (신용평점별 80~100%), 운전무면허자 취급기준 (가족·직원 운전자), 상환능력 양호 (재직·소득·재산 증빙), 시스템 판정(S판정/자동승인), 중고차 영업 관행 개선 가이드라인

### Community 6 - "Community 6"
Cohesion: 0.33
Nodes (6): 금융리스, G/L 금리, 금리등급, 최저금리, NEGO 조정금리, NICE 신용점수

## Ambiguous Edges - Review These
- `개인사업자 사업자 기준` → `개인회생 취급기준`  [AMBIGUOUS]
  raw/우리캐피탈/2.오토운영팀 온톨로지/9_샘플_중고승용 상품운영기준.pdf · relation: semantically_similar_to

## Knowledge Gaps
- **37 isolated node(s):** `론 (구입대출)`, `중고승용`, `중고리스`, `최저금리`, `취급 한도CAP 기준` (+32 more)
  These have ≤1 connection - possible missing edges or undocumented components.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `개인사업자 사업자 기준` and `개인회생 취급기준`?**
  _Edge tagged AMBIGUOUS (relation: semantically_similar_to) - confidence is low._
- **Why does `중고승용 상품운영기준` connect `Community 1` to `Community 0`, `Community 2`, `Community 4`, `Community 6`?**
  _High betweenness centrality (0.521) - this node is a cross-community bridge._
- **Why does `중고 오토리스 상품운영기준` connect `Community 3` to `Community 0`, `Community 2`, `Community 4`, `Community 6`?**
  _High betweenness centrality (0.315) - this node is a cross-community bridge._
- **Why does `중고 오토리스 심사운영기준(E09024)` connect `Community 0` to `Community 1`, `Community 3`, `Community 5`?**
  _High betweenness centrality (0.294) - this node is a cross-community bridge._
- **What connects `론 (구입대출)`, `중고승용`, `중고리스` to the rest of the system?**
  _37 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.13 - nodes in this community are weakly interconnected._