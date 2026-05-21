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

서브에이전트 최대 5개(시작 시 Pathfinding 1개 제공). **Memory·Guardrails는 Supervisor 전용**(폼 확정) — 기억·안전은 Supervisor가 직접:

```
  AgentCore Memory ─┐         ┌─ Bedrock Guardrails
   (Supervisor 전용) │         │   (Supervisor 전용)
                     ▼         ▼
  Supervisor (Dungeon-Orchestrator)
   · 오케스트레이션 + Memory(여정 기억) + Guardrails(안전)
   · 일반상식·안정성 챌린지 직접 처리, 나머지는 서브에이전트로 위임
   ├─ Pathfinding ....... Pathfinding Lambda (Orienteering, 막힘 회피·장애물 우회)
   ├─ Code_Specialist ... 코드 실행 Lambda — 수학/알고리즘 챌린지
   ├─ Web_Researcher .... 웹 검색 Lambda — 웹서치 챌린지
   ├─ Knowledge_Specialist (선택) — 일반상식 오프로드
   └─ (예비) ............ 당일 변수용
```

서브에이전트 = "Lambda Tool로 특정 기술 수행하는 전문가". 모델은 모두 Claude Sonnet 4.

확정 규칙 반영: **남은 생명=점수**(장애물 회피), **막힘 강제통과=게임종료**(경로 유효성 최우선),
**토큰 보너스**(출력 축약·캐시), **챌린지 점수 획득/차감**(저신뢰 SKIP), **LLM-as-judge 채점**(응답 품질).

각 구성요소의 실제 프롬프트·계약·슬롯배치는 `agent/` 참조:
- 슬롯 배치도: [agent/orchestration.md](../agent/orchestration.md)
- 프롬프트: [supervisor](../agent/prompts/supervisor.md) · [navigator(Pathfinder)](../agent/prompts/navigator.md) · [code-specialist](../agent/prompts/challenge-solver.md) · [web-researcher](../agent/prompts/web-researcher.md) · [knowledge-safety](../agent/prompts/knowledge-safety.md) · [memory-recon](../agent/prompts/memory-recon.md)
- [tools.md](../agent/tools.md) · [guardrails.md](../agent/guardrails.md) · [memory-schema.md](../agent/memory-schema.md) · [lambdas/](../agent/lambdas/)

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
