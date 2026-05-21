# agent/ — AgentCore 배포 산출물

워크샵 당일 그대로 이식할 LLM 에이전트 구성. 설계 배경: [docs/09-agent-design.md](../docs/09-agent-design.md).

| 파일 | 용도 |
|---|---|
| **[orchestration.md](orchestration.md)** | **★ UI 슬롯 배치도** (당일 브라우저에서 무엇을 어디에 넣을지) |
| [prompts/supervisor.md](prompts/supervisor.md) | Supervisor (매 턴 단일 행동, 정책=score_model 함수, 챌린지 유형별 라우팅) |
| [prompts/navigator.md](prompts/navigator.md) | Pathfinder — `Pathfinding` Lambda(막힘 회피·장애물 우회) |
| [prompts/challenge-solver.md](prompts/challenge-solver.md) | Code Specialist — 수학/알고리즘 (CodeExecution) |
| [prompts/web-researcher.md](prompts/web-researcher.md) | Web Researcher — 웹서치 챌린지 (웹 검색 도구) |
| [prompts/knowledge-safety.md](prompts/knowledge-safety.md) | Knowledge & Safety — 일반상식/안정성 챌린지 |
| [prompts/memory-recon.md](prompts/memory-recon.md) | Memory Curator — Recon(규칙 구조화) + world model |
| [lambdas/pathfinding.py](lambdas/pathfinding.py) | **★ SageMaker 에디터에 그대로 붙여넣을 Lambda 코드** |
| [tools.md](tools.md) | `navigate` / `solve_challenge` / `memory_io` Tool 입출력 계약 |
| [guardrails.md](guardrails.md) | 출력 스키마·행동 유효성·규칙 준수 강제 |
| [memory-schema.md](memory-schema.md) | Memory 키 + `score_model` 구조 |
| [adaptation-playbook.md](adaptation-playbook.md) | 당일 규칙 → 행동 변경 의사결정 트리 + 반복개선 |

## 핵심 원칙 (3줄)

1. **LLM은 판단, 계산은 결정론적 Tool** — 경로·수학 추측 금지.
2. **챌린지는 전량 Code Interpreter** — 정답률 100%, 생명 손실 0.
3. **정책 = score_model 함수** — 당일 규칙이 바뀌어도 프롬프트 불변, 값만 교체.
   강건성 실측: 6개 규칙 레짐 전부 진짜 최적의 100% (`sim/robustness.py`).

## 당일 적용 순서 (브라우저에서 ~10분)

1. **도구 등록**: Memory 인스턴스 + Guardrails(`guardrails.md` 정책) + Lambda(`lambdas/pathfinding.py` 코드 그대로 붙여넣기).
2. **슈퍼바이저 설정**: `prompts/supervisor.md` 본문을 시스템 프롬프트로.
3. **서브 에이전트 3종 추가**: Pathfinder / Code Specialist / Memory Curator (각각 `prompts/`의 해당 파일). 슬롯 배치 상세 → [orchestration.md](orchestration.md).
4. **Recon → 보드 플레이**: 인게임 규칙/탭 + 워크숍 스튜디오 문서 → `memory-schema.md`의 `score_model` 채움 → 같은 값을 `sim/config.json`에 넣고 `python3 sim/bench.py`로 사전 검증.
5. **반복 개선**: 플레이 → 로그 → 실패유형 1개 수정 → 재플레이 ([adaptation-playbook.md](adaptation-playbook.md)).
