# backend/data — 수치형 질의용 결정적 테이블

수치형 질의(금리·등급·네고·프로모션)는 **LLM이 아니라 이 CSV에서 값을 뽑아 템플릿으로 답**한다
(빈응답·환각 원천 제거). `app/search/tables.py`가 읽는다.

> ⚠️ 시드행은 `docs/12` 예시·모범답안 기반 **참고값**이다. 실제 서비스 전 **상품운영기준 원문으로 검수·확장**할 것.

## 파일 스키마

- `rate_grade.csv` — `customer_type, grade, term_min_months, gl_rate, source`
  등급/고객유형/최소취급개월별 G/L 금리. 개월수 미지정 질의는 `term_min_months` **최소 구간** 행 선택.
- `nego_rule.csv` — `grade_from, grade_to, nego_type, rate, code, source`
  등급 구간(`grade_from<=등급<=grade_to`)에 적용 가능한 네고(내국인/거점장/증빙/HJ 등)와 율.
- `promotion.csv` — `name, grade_req, nice_min, kcb_min, gl_rate, exclude, source`
  프로모션 적용 **임계값**(금리등급 이상=숫자 낮을수록 상위 / NICE·KCB 최소 점수)·G/L 금리·제외 대상.
  사용자가 "나이스 955점, KCB 800점인데 가능해?"처럼 값을 주면 임계값과 대조해 **가능/불가 판정**한다.

## 값 추가/수정 방법
행만 추가하면 즉시 반영(서버 재시작 불필요, 요청마다 로드). 콤마가 포함된 조건문은 CSV 규칙상 큰따옴표로 감싼다.
