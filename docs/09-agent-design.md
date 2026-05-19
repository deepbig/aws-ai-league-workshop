# 09. AgentCore LLM 에이전트 설계 (실전 청사진)

> 워크샵의 본질 = **LLM 에이전트를 만들고 반복 개선**해 점수를 높이는 것.
> 본 문서가 중심. 라우팅 알고리즘([docs/08](08-routing-findings.md))은 *Navigator Tool 구현 근거*로만 편입.

배포 산출물: [`agent/`](../agent/) — 시스템 프롬프트·Tool 계약·Guardrails·Memory 스키마·당일 적응 플레이북.

---

## 1. 설계 원칙 (점수와 직결)

| 원칙 | 이유 |
|---|---|
| **LLM은 판단, 계산은 Tool** | 경로·수학은 LLM이 추측하면 부정확 → 결정론적 Tool에 위임 |
| **챌린지는 무조건 코드 실행** | 암산 오답 = 점수/생명 손실. Code Interpreter로 정답률 100% |
| **정책은 규칙 파라미터로 구동** | 당일 규칙이 바뀌어도 프롬프트 재작성 없이 *값만* 교체해 적응 |
| **Recon → Act → Memory 루프** | 변수 상황(미지의 규칙)을 먼저 탐지·기록 후 그 위에서 행동 |
| **출력은 스키마 고정** | Guardrails로 행동/답안 포맷 강제 → 무효 행동·파싱 실패 0 |

## 2. 역할 분해 (안내자료 아키텍처 매핑)

```
AgentCore Runtime
├─ Supervisor Agent ........ 매 턴 단일 행동 결정 (정책 = 규칙 파라미터 함수)
│   ├─ Navigator Sub-Agent .. navigate Tool(Lambda, 결정론적 Orienteering) 호출
│   ├─ Challenge Solver ..... solve_challenge Tool(Code Interpreter) 호출
│   └─ Memory/Recon ......... 규칙·맵·진행상태를 AgentCore Memory에 구조화
├─ AgentCore Gateway ....... Sub-Agent ↔ Lambda Tool 연결
├─ AgentCore Memory ........ world model + 발견한 채점규칙(score_model)
└─ Bedrock Guardrails ...... 입출력 스키마/규칙준수 강제
```

각 구성요소의 실제 프롬프트·계약은 `agent/` 참조:
- [agent/prompts/supervisor.md](../agent/prompts/supervisor.md)
- [agent/prompts/navigator.md](../agent/prompts/navigator.md)
- [agent/prompts/challenge-solver.md](../agent/prompts/challenge-solver.md)
- [agent/prompts/memory-recon.md](../agent/prompts/memory-recon.md)
- [agent/tools.md](../agent/tools.md) · [agent/guardrails.md](../agent/guardrails.md) · [agent/memory-schema.md](../agent/memory-schema.md)

## 3. 변수 상황 대응 = 이 워크샵의 핵심 난이도

세부 규칙·보너스·배점은 **당일 공개**. 잘하는 에이전트 = *주어진 규칙을 빨리 파악하고 그에 맞춰 행동을 바꾸는* 에이전트.

설계: **정책을 규칙 파라미터의 함수로** 만든다.

```
행동 = Supervisor정책( 상태, score_model )
  score_model = { coin_value_fn, challenge_score, penalties,
                  bonus_triggers, time_bonus, life_rule, ... }
```

- **Recon 단계(게임 시작 직후)**: 인게임 "목표/극대화하는 방법/추가 규칙/챌린지/보너스" 탭 + 워크숍 스튜디오 문서를 읽어 `score_model`을 **구조화해 Memory에 기록**.
- 이후 Supervisor는 프롬프트 변경 없이 `score_model` 값에 따라 우선순위(챌린지 vs 코인 vs 보물 vs 보너스)를 재계산.
- 사람+AI Assistant 루프: 플레이 로그 관찰 → 규칙 추론 보정 → Memory `score_model` 갱신 → 재플레이.

상세 절차·의사결정 트리: [agent/adaptation-playbook.md](../agent/adaptation-playbook.md).

## 4. 반복 개선 루프 (대회 점수의 실제 동력)

안내자료: *"만들고 **개선하며** 점수를 높여가는"* → 1회 완성도보다 **사이클 수 × 사이클당 개선폭**.

```
플레이 1회 → 로그 수집 → 실패유형 분류
  (경로비효율 / 챌린지오답 / 시간초과 / 생명손실 / 규칙오해)
→ 가장 큰 손실원 1개만 수정 (프롬프트 1줄·파라미터·Tool)
→ 재플레이 → 귀속 확인
```
- 한 번에 한 변수만. AI Assistant에 (로그 + 본 설계 + score_model)을 함께 투입.
- 시뮬레이터는 이 루프의 **사전 리허설 + 규칙 변동 강건성 검증**용([docs/07](07-simulation-plan.md), 로드맵 §6).

## 5. 알고리즘 작업의 위치 (오해 해소)

[docs/08](08-routing-findings.md)의 ILS/Held-Karp 결과는 *그 자체가 목적이 아니라* **"경로는 LLM이 풀지 말고 navigate Tool에 위임하라"**는 에이전트 설계 결정을 데이터로 입증한 것. 즉:
- 결론 = LLM 에이전트 설계(어디까지 LLM, 어디부터 Tool)
- 산출 = navigate Lambda Tool의 검증된 내부 알고리즘 ([agent/tools.md](../agent/tools.md))

→ 라우팅은 "해결된 하위문제(Tool)", 점수 경쟁의 주전장은 **Supervisor 정책·프롬프트·규칙적응·반복개선**.
