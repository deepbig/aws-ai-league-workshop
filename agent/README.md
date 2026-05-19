# agent/ — AgentCore 배포 산출물

워크샵 당일 그대로 이식할 LLM 에이전트 구성. 설계 배경: [docs/09-agent-design.md](../docs/09-agent-design.md).

| 파일 | 용도 |
|---|---|
| [prompts/supervisor.md](prompts/supervisor.md) | Supervisor 시스템 프롬프트 (매 턴 단일 행동, 정책=score_model 함수) |
| [prompts/navigator.md](prompts/navigator.md) | Navigator — navigate Tool에 경로 위임 |
| [prompts/challenge-solver.md](prompts/challenge-solver.md) | Challenge Solver — Code Interpreter로 100% 정답 |
| [prompts/memory-recon.md](prompts/memory-recon.md) | Recon(규칙 구조화) + Memory(world model) |
| [tools.md](tools.md) | `navigate` / `solve_challenge` / `memory_io` Tool 입출력 계약 |
| [guardrails.md](guardrails.md) | 출력 스키마·행동 유효성·규칙 준수 강제 |
| [memory-schema.md](memory-schema.md) | Memory 키 + `score_model` 구조 |
| [adaptation-playbook.md](adaptation-playbook.md) | 당일 규칙 → 행동 변경 의사결정 트리 + 반복개선 |

## 핵심 원칙 (3줄)

1. **LLM은 판단, 계산은 결정론적 Tool** — 경로·수학 추측 금지.
2. **챌린지는 전량 Code Interpreter** — 정답률 100%, 생명 손실 0.
3. **정책 = score_model 함수** — 당일 규칙이 바뀌어도 프롬프트 불변, 값만 교체.
   강건성 실측: 6개 규칙 레짐 전부 진짜 최적의 100% (`sim/robustness.py`).

## 당일 적용 순서

1. Recon: 인게임 규칙/탭 + 워크숍 스튜디오 문서 → `memory-schema.md`의 `score_model` 채움.
2. 같은 값을 `sim/config.json`에 입력 → `python3 sim/bench.py`로 우선순위 사전 확인.
3. `prompts/`·`tools.md`·`guardrails.md`를 AgentCore에 이식, `<<자리표시자>>` 채움.
4. 플레이 → 로그 → 실패유형 1개 수정 → 재플레이 (adaptation-playbook 루프).
