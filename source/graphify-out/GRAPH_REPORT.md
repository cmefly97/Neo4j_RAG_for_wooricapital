# Graph Report - .  (2026-06-27)

## Corpus Check
- Corpus is ~14,051 words - fits in a single context window. You may not need a graph.

## Summary
- 62 nodes · 58 edges · 17 communities (7 shown, 10 thin omitted)
- Extraction: 84% EXTRACTED · 16% INFERRED · 0% AMBIGUOUS · INFERRED: 9 edges (avg confidence: 0.84)
- Token cost: 169,763 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_중고승용 상품·온톨로지 설계|중고승용 상품·온톨로지 설계]]
- [[_COMMUNITY_취급조건·NEGO 금리|취급조건·NEGO 금리]]
- [[_COMMUNITY_FAQ·실물확인·시세|FAQ·실물확인·시세]]
- [[_COMMUNITY_리스 차량가격·금리등급|리스 차량가격·금리등급]]
- [[_COMMUNITY_재고금융·NICE 등급|재고금융·NICE 등급]]
- [[_COMMUNITY_중고 오토리스 상품|중고 오토리스 상품]]
- [[_COMMUNITY_취급불가 대상·안티프로드|취급불가 대상·안티프로드]]
- [[_COMMUNITY_여신 전결기준|여신 전결기준]]
- [[_COMMUNITY_취급불가·카히스토리|취급불가·카히스토리]]
- [[_COMMUNITY_업력 기준|업력 기준]]
- [[_COMMUNITY_주행거리 제한 LTV|주행거리 제한 LTV]]
- [[_COMMUNITY_재고금융 차량가격 조건|재고금융 차량가격 조건]]
- [[_COMMUNITY_오토리스 실물확인|오토리스 실물확인]]
- [[_COMMUNITY_오토리스 무면허 취급|오토리스 무면허 취급]]
- [[_COMMUNITY_차량설정 기준|차량설정 기준]]
- [[_COMMUNITY_중형상용 차량|중형상용 차량]]
- [[_COMMUNITY_중고승용 무면허 취급|중고승용 무면허 취급]]

## God Nodes (most connected - your core abstractions)
1. `중고승용 상품운영기준 (26.03)` - 7 edges
2. `오토운영팀 FAQ (가명샘플)` - 6 edges
3. `중고승용 론 (구입대출) 상품` - 5 edges
4. `중고차승용심사운영기준 (E09003)` - 4 edges
5. `3종 데이터 출처 (FAQ/규정/운영기준)` - 4 edges
6. `샘플 질의셋 (론/할부/듀얼/엔카슬라이딩/신용구제)` - 4 edges
7. `신용구제 상품 (개인회생/신용회복, R판정)` - 4 edges
8. `재고금융/운영자금심사운영기준 (E09012)` - 3 edges
9. `중고차승용 상품 (할부금융/론)` - 3 edges
10. `오토운영팀 온톨로지 및 에이전트 설계` - 3 edges

## Surprising Connections (you probably didn't know these)
- `금리등급 / NICE 점수구간` --semantically_similar_to--> `NICE CB점수 등급별 취급기준`  [INFERRED] [semantically similar]
  /Users/mac_al03256431/Library/CloudStorage/WORKS드라이브-jinkyu.yoon@navercorp.com/내 드라이브/Dev/JB_Wooricapital_Auto_Agent/source/9_샘플_중고승용 상품운영기준.pdf → /Users/mac_al03256431/Library/CloudStorage/WORKS드라이브-jinkyu.yoon@navercorp.com/내 드라이브/Dev/JB_Wooricapital_Auto_Agent/source/5_재고금융_운영자금심사운영기준.md
- `중고승용 론 (구입대출) 상품` --semantically_similar_to--> `중고차승용 상품 (할부금융/론)`  [INFERRED] [semantically similar]
  /Users/mac_al03256431/Library/CloudStorage/WORKS드라이브-jinkyu.yoon@navercorp.com/내 드라이브/Dev/JB_Wooricapital_Auto_Agent/source/9_샘플_중고승용 상품운영기준.pdf → /Users/mac_al03256431/Library/CloudStorage/WORKS드라이브-jinkyu.yoon@navercorp.com/내 드라이브/Dev/JB_Wooricapital_Auto_Agent/source/7_중고차승용심사운영기준.md
- `FAQ: 재고 이용 불가 차종` --conceptually_related_to--> `카히스토리 적용기준 (재고금융)`  [INFERRED]
  /Users/mac_al03256431/Library/CloudStorage/WORKS드라이브-jinkyu.yoon@navercorp.com/내 드라이브/Dev/JB_Wooricapital_Auto_Agent/source/4_오토운영팀 FAQ 가명샘플.pdf → /Users/mac_al03256431/Library/CloudStorage/WORKS드라이브-jinkyu.yoon@navercorp.com/내 드라이브/Dev/JB_Wooricapital_Auto_Agent/source/5_재고금융_운영자금심사운영기준.md
- `FAQ: 실물확인 조건 발생 이유` --conceptually_related_to--> `차량 실물확인 기준 (중고승용)`  [INFERRED]
  /Users/mac_al03256431/Library/CloudStorage/WORKS드라이브-jinkyu.yoon@navercorp.com/내 드라이브/Dev/JB_Wooricapital_Auto_Agent/source/4_오토운영팀 FAQ 가명샘플.pdf → /Users/mac_al03256431/Library/CloudStorage/WORKS드라이브-jinkyu.yoon@navercorp.com/내 드라이브/Dev/JB_Wooricapital_Auto_Agent/source/7_중고차승용심사운영기준.md
- `3종 데이터 출처 (FAQ/규정/운영기준)` --references--> `오토운영팀 FAQ (가명샘플)`  [EXTRACTED]
  /Users/mac_al03256431/Library/CloudStorage/WORKS드라이브-jinkyu.yoon@navercorp.com/내 드라이브/Dev/JB_Wooricapital_Auto_Agent/source/오토운영팀 온톨로지 및 에이전트.md → /Users/mac_al03256431/Library/CloudStorage/WORKS드라이브-jinkyu.yoon@navercorp.com/내 드라이브/Dev/JB_Wooricapital_Auto_Agent/source/4_오토운영팀 FAQ 가명샘플.pdf

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **오토금융 상품군 (론/할부/리스/재고/듀얼/신용구제)** — source_9_product_ron_sangpum, source_9_product_halbu_sangpum, source_6_otolease_junggo_otolease, source_5_jaego_junggocha_jaegogeumyung, source_9_product_dual_offer, source_9_product_sinyong_guje [INFERRED 0.75]
- **차량가격/시세 산정 흐름 (DB시세·잔가율·LTV·카히스토리)** — source_7_seungyong_db_sisye, source_8_lease_jangaryul, source_7_seungyong_chaeryangggagyeok_ltv, source_7_seungyong_carhistory [INFERRED 0.75]
- **금리등급→NEGO/슬라이딩 금리결정 메커니즘** — source_9_product_geumri_deunggeup_nice, source_9_product_nego_jojeong_geumri, source_9_product_sliding [INFERRED 0.85]

## Communities (17 total, 10 thin omitted)

### Community 0 - "중고승용 상품·온톨로지 설계"
Cohesion: 0.23
Nodes (13): 중고차승용심사운영기준 (E09003), 차량가격 적용기준 / LTV, 중고승용 상품운영기준 (26.03), 듀얼상품 (Dual Offer C/O), 엔카 무수수료 상품 (엔카_Zero), ESM / 딜러구입대출 상품, 중고승용 할부 구입대출 상품, 신용구제 상품 (개인회생/신용회복, R판정) (+5 more)

### Community 1 - "취급조건·NEGO 금리"
Cohesion: 0.25
Nodes (8): 중형트럭 시범운영기준 (제5차), 취급톤수/물품 조건 (카고·탑차·크레인 등), 중형트럭 상품 (2~10톤 화물차), FAQ: 등급변경 금리오류/신용점수 업데이트, 중고차승용 상품 (할부금융/론), 취급기간/개월수 (12~72개월), NEGO 조정금리 (내국인/외국인, 거점장·증빙), 중고승용 론 (구입대출) 상품

### Community 2 - "FAQ·실물확인·시세"
Cohesion: 0.29
Nodes (7): FAQ: 차량 매칭/DB시세 노출 기준, 오토운영팀 FAQ (가명샘플), FAQ: 재고 이용 불가 차종, FAQ: 서류 면제/발급일자 기준, FAQ: 실물확인 조건 발생 이유, 카히스토리 적용기준 (재고금융), 차량 실물확인 기준 (중고승용)

### Community 3 - "리스 차량가격·금리등급"
Cohesion: 0.29
Nodes (7): 차량가격 취급기준 (오토리스), DB시세 (차량가격 산정), 중고리스 운영기준(변경) (26.03), 금리등급 (1~8, 법인 대표자 준용), 금융리스 상품 (금리등급별 금리table), 잔가율 / 잔가군표 (국산·수입), 운용리스 상품 (잔가/IRR Nego)

### Community 4 - "재고금융·NICE 등급"
Cohesion: 0.33
Nodes (6): 재고금융/운영자금심사운영기준 (E09012), 중고차 재고금융, 중고차 운영자금, NICE CB점수 등급별 취급기준, 수입차 재고금융, 금리등급 / NICE 점수구간

### Community 5 - "중고 오토리스 상품"
Cohesion: 0.40
Nodes (5): 중고오토리스심사운영기준 (E09024), 중고 오토리스, 운용리스/금융리스, 중고리스 취급제한차종, 성능상태점검기록부 확인 (랭크/사고)

### Community 6 - "취급불가 대상·안티프로드"
Cohesion: 0.50
Nodes (4): 취급불가/제한 대상자, GRAS 등급 / 안티프로드 운영지침, JABIS 전산조회 시스템, 중고승용 취급불가 대상자

## Knowledge Gaps
- **26 isolated node(s):** `중고차 재고금융`, `수입차 재고금융`, `대출금액별 전결기준`, `카히스토리 적용기준 (재고금융)`, `차량가격 취급조건 (재고금융)` (+21 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **10 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `중고승용 론 (구입대출) 상품` connect `취급조건·NEGO 금리` to `중고승용 상품·온톨로지 설계`, `재고금융·NICE 등급`?**
  _High betweenness centrality (0.180) - this node is a cross-community bridge._
- **Why does `중고승용 상품운영기준 (26.03)` connect `중고승용 상품·온톨로지 설계` to `취급조건·NEGO 금리`?**
  _High betweenness centrality (0.156) - this node is a cross-community bridge._
- **Why does `금리등급 / NICE 점수구간` connect `재고금융·NICE 등급` to `취급조건·NEGO 금리`, `리스 차량가격·금리등급`?**
  _High betweenness centrality (0.149) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `3종 데이터 출처 (FAQ/규정/운영기준)` (e.g. with `중고차승용심사운영기준 (E09003)` and `중고승용 상품운영기준 (26.03)`) actually correct?**
  _`3종 데이터 출처 (FAQ/규정/운영기준)` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `중고차 재고금융`, `수입차 재고금융`, `대출금액별 전결기준` to the rest of the system?**
  _27 weakly-connected nodes found - possible documentation gaps or missing edges._