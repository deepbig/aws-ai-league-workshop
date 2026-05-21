# agent/ — AgentCore 배포 산출물

워크샵 당일 그대로 이식할 LLM 에이전트 구성. 설계 배경: [docs/09-agent-design.md](../docs/09-agent-design.md).

| 파일 | 용도 |
|---|---|
| **[PASTE-SHEET.md](PASTE-SHEET.md)** | **★ 당일 복사·붙여넣기 시트** (한 파일에서 위→아래 순서대로) |
| **[orchestration.md](orchestration.md)** | **★ UI 슬롯 배치도** (당일 브라우저에서 무엇을 어디에 넣을지) |
| **[prompt-types.md](prompt-types.md)** | **★ System vs Runtime 프롬프트** — 제어 가능한 건 Navigation prompt뿐 |
| [prompts/supervisor.md](prompts/supervisor.md) | **Supervisor** `Dungeon-Orchestrator` — 오케스트레이션 + Memory + Guardrails + 일반상식/안정성 직접 처리 |
| [prompts/navigator.md](prompts/navigator.md) | `Pathfinding` 서브(기본 제공) — Pathfinding Lambda(막힘 회피·장애물 우회) |
| [prompts/challenge-solver.md](prompts/challenge-solver.md) | `Code_Specialist` 서브 — 수학/알고리즘 (코드 실행) |
| [prompts/web-researcher.md](prompts/web-researcher.md) | `Web_Researcher` 서브 — 웹서치 (웹 검색 Lambda) |
| [prompts/knowledge-safety.md](prompts/knowledge-safety.md) | `Knowledge_Specialist` 서브(선택) — 일반상식. 안정성은 Supervisor가 처리 |
| [prompts/memory-recon.md](prompts/memory-recon.md) | (서브 아님) Supervisor의 Recon/Memory 운영 지침 |
| [lambdas/pathfinding.py](lambdas/pathfinding.py) | **★ SageMaker 에디터에 그대로 붙여넣을 Lambda 코드** |
| [tools.md](tools.md) | `navigate` / `solve_challenge` / `memory_io` Tool 입출력 계약 |
| [guardrails.md](guardrails.md) | 출력 스키마·행동 유효성·규칙 준수 강제 |
| [memory-schema.md](memory-schema.md) | Memory 키 + `score_model` 구조 |
| [adaptation-playbook.md](adaptation-playbook.md) | 당일 규칙 → 행동 변경 의사결정 트리 + 반복개선 |

## 핵심 원칙 (3줄)

1. **LLM은 판단, 계산은 Lambda Tool** — 경로·수학 추측 금지.
2. **Memory·Guardrails는 Supervisor 전용** — 기억(여정)·안전(안정성)은 Supervisor가 직접.
3. **정책 = score_model 함수** — 당일 규칙이 바뀌어도 프롬프트 불변, 값만 교체.
   강건성 실측: 6개 규칙 레짐 전부 진짜 최적의 100% (`sim/robustness.py`).

## 당일 적용 순서 (브라우저에서 ~10분)

1. **도구 등록**: Memory + Guardrails(`guardrails.md`)를 **Supervisor에 연결** + Lambda(`lambdas/pathfinding.py` 붙여넣기 + 코드/웹 도구).
2. **슈퍼바이저 설정**: `prompts/supervisor.md` 본문을 시스템 프롬프트로, Memory·Guardrails 연결.
3. **서브 에이전트 추가**: `Pathfinding`(기본 확인) → `Code_Specialist` · `Web_Researcher` 추가, 각 Lambda 연결. (선택: `Knowledge_Specialist`). 슬롯 배치 → [orchestration.md](orchestration.md).
4. **Recon → 보드 플레이**: 인게임 규칙/탭 + 워크숍 문서 → `memory-schema.md`의 `score_model` 채움 → `sim/config.json` 반영 → `python3 sim/robustness.py` 사전 검증.
5. **반복 개선**: 플레이 → 로그 → 실패유형 1개 수정 → 재플레이 ([adaptation-playbook.md](adaptation-playbook.md)).
