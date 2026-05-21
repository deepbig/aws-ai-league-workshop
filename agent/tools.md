# Tool 계약 (AgentCore Gateway → Lambda)

LLM이 직접 하면 부정확한 작업을 결정론적 Lambda Tool로 위임. 입출력 계약 고정 → Guardrails로 강제.

---

## 1. `navigate` — 경로 최적화 (결정론적)

게임 = 예산제약 Orienteering. LLM 추정 금지. 내부 알고리즘은 검증됨
(진짜 최적해의 99.8~100%, [docs/08](../docs/08-routing-findings.md)).

**Input**
```json
{
  "start": [r, c],
  "grid":  [[0,1,...], ...],          // 0=통로 1=벽/막힘(통과불가). 막힘은 반드시 1로
  "rewards": [
    {"cell":[r,c], "kind":"coin|challenge|treasure",
     "value": <score_model로 계산된 가치>, "solve_cost": <스텝>}
  ],
  "obstacles": [[r,c], ...],          // 회피 대상(생명 -1). 경로 비용에 가산되어 우회됨
  "time_budget": <남은 스텝>,
  "mode": "fast | precise"            // fast=greedy+LS(~15ms), precise=ILS
}
```

> 막힘 셀은 grid=1로 표기 → 경로에 절대 미포함(강제 통과 시 게임 종료 방지).
> 장애물은 obstacles로 전달 → 통과 비용 가산으로 우회(남은 생명=점수).

**Output**
```json
{ "route": [[r,c], ...], "expected_value": <int>, "used_steps": <int> }
```

**구현**: `sim/planners.py`의 `plan_greedy_ls`(fast) / `plan_ils`(precise) +
`game.py`의 BFS 거리행렬을 Lambda로 이식. `value`는 Memory의 `score_model`로 산출
(코인 가치 규칙·challenge_score 반영) → 규칙이 바뀌어도 Tool 재작성 없이 입력만 변경.

---

## 2. `solve_challenge` — 챌린지 풀이 (Code Interpreter)

**Input**  `{ "problem_text": "<Combat Log 문제>", "answer_format": "<score_model.answer_format>" }`

**Output** `{ "answer": "<포맷된 정답>", "verified": true|false, "method": "<요약>" }`

**규약**: 반드시 Python 실행으로 계산, 가능 시 2-방법 검산(`verified`).
`verified=false`면 Supervisor가 제출 보류 판단(오답 페널티 큰 경우).

---

## 3. `web_search` — 웹 검색 챌린지 (Web Researcher 전용)

**Input**  `{ "query": "<검색어>", "max_results": 3 }`
**Output** `{ "results": [{"title":"...","snippet":"...","url":"..."}], "answer": "<추출 사실>" }`

**규약**: 시점 민감/사실 확인 챌린지는 기억 대신 검색. 1~2회 교차 확인 후 채택.
AgentCore 내장 Browser/WebSearch 도구일 가능성(당일 확인) — 별도 Lambda 불필요할 수 있음.

---

## 4. `memory_io` — 상태/규칙 저장·조회 (AgentCore Memory)

**Input**  `{ "op": "get|put", "key": "<키>", "value": <put 시> }`
**Output** `{ "key": "...", "value": <구조화 값> }`

키 정의: [agent/memory-schema.md](memory-schema.md).

---

## 설계 노트

- **불필요한 Tool 호출 최소화**(안내자료 명시): navigate는 재계획 필요 시에만,
  solve_challenge는 챌린지 조우 시에만, memory_io는 행동 경계에서만.
- 모든 Tool은 **결정론적·검증가능**. LLM은 입력 정리와 결과 해석만 담당.
