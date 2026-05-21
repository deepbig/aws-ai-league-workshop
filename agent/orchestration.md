# 멀티 에이전트 오케스트레이션 — UI 슬롯 배치도

워크샵 생성 폼(Edit Supervisor / Edit Sub-Agent) 기반. 당일 확정 규칙·제약 반영.

## 핵심 제약 (폼/안내문 확정)

- **Memory와 Guardrails는 Supervisor만 사용 가능.** 기억(여정)·안전(유해 콘텐츠/안정성 챌린지)은 Supervisor가 직접 처리.
- **모든 에이전트는 Lambda Tool 연결 가능.** 서브에이전트 = "특정 기술을 Lambda로 수행하는 전문가".
- **서브에이전트 최대 5개**, 시작 시 **Pathfinding 1개 제공**.
- Agent Name: Supervisor는 하이픈 허용, **서브에이전트는 영문/숫자/언더스코어만**(하이픈 불가), 48자.
- Model: 둘 다 `Claude Sonnet 4` 기본.

## 권장 배치

```
        ┌──── AgentCore Memory ────┐   ┌── Bedrock Guardrails ──┐
        │   (Supervisor 전용)       │   │   (Supervisor 전용)    │
        └────────────┬──────────────┘   └───────────┬───────────┘
                     └───────────┐        ┌──────────┘
                                 ▼        ▼
                       ┌────────────────────────┐
                       │  Supervisor             │ ← prompts/supervisor.md
                       │  Dungeon-Orchestrator   │   (+ 일반상식·안정성 직접 처리)
                       └────────────┬────────────┘
              ┌───────────┬─────────┼─────────┬───────────┐
              ▼           ▼         ▼         ▼           ▼
        Pathfinding  Code_Specialist Web_Researcher (Knowledge_  (예비)
        (기본 제공)                                  Specialist 선택)
              │           │            │
              ▼           ▼            ▼
        [Pathfinding  [Code 실행    [웹 검색
         Lambda]       Lambda]      Lambda]
```

### 슬롯별 등록 내용

| UI 슬롯 | 이름 | 출처 |
|---|---|---|
| 도구 > 메모리 (Supervisor에 연결) | `agent_memory` | [memory-schema.md](memory-schema.md) |
| 도구 > Guardrails (Supervisor에 연결) | `guardrail` | [guardrails.md](guardrails.md) |
| 도구 > Lambda | `Pathfinding` | [lambdas/pathfinding.py](lambdas/pathfinding.py) 코드 그대로 |
| 도구 > Lambda | 코드 실행 / 웹 검색 | CodeExecution·WebSearch(내장 추정) 또는 커스텀 Lambda |
| Supervisor 프롬프트 | `Dungeon-Orchestrator` | [prompts/supervisor.md](prompts/supervisor.md) |
| 서브1 (기본) | `Pathfinding` + Pathfinding Lambda | [prompts/navigator.md](prompts/navigator.md) |
| 서브2 | `Code_Specialist` + 코드 실행 Lambda | [prompts/challenge-solver.md](prompts/challenge-solver.md) |
| 서브3 | `Web_Researcher` + 웹 검색 Lambda | [prompts/web-researcher.md](prompts/web-researcher.md) |
| 서브4 (선택) | `Knowledge_Specialist` (도구 없음) | [prompts/knowledge-safety.md](prompts/knowledge-safety.md) |
| 서브5 (예비) | — | 당일 변수(보너스 트리거 등)용 |

> 일반 상식·안정성을 Supervisor가 직접 처리하면 서브4를 비워 예비 슬롯 2개 확보 가능.

## 챌린지 유형 → 처리 주체 (Supervisor가 라우팅)

| 챌린지 유형 | 처리 |
|---|---|
| 수학/알고리즘 | → `Code_Specialist` (코드 실행) |
| 웹 서치 | → `Web_Researcher` (웹 검색) |
| 일반 상식 | Supervisor 직접 (또는 `Knowledge_Specialist`) |
| 안정성(safety) | **Supervisor 직접** (Guardrails 전용 보유) |

| 게임 상황 | 처리 |
|---|---|
| 경로/이동 | → `Pathfinding` (막힘 회피·장애물 우회) |
| 규칙/맵/진행 기억 | **Supervisor 직접** (Memory 전용 보유) |

## 점수 레버 반영

- **보물 = 게임 종료**: 코인·챌린지 최대 수집 후 **마지막에 보물**. Navigation prompt에
  `use strategy max_loot` 입력(swift 직행 금지). Pathfinding Lambda가 보물=종착으로 최적화.
- **생명 = 점수**: Pathfinding이 장애물(spikes) 우회, Supervisor가 위험 회피.
- **막힘 = 게임오버**: 막힘=벽(1) 표기 → 경로 미경유 + Supervisor가 비검증 이동 금지.
- **토큰 보너스(챌린지당 평균)**: 모든 프롬프트 "정답만/짧게", 중복 호출 금지, Memory 캐시.
- **챌린지 보상/데미지**: 정답 +코인, 오답 ♥-1 → 저신뢰·고데미지 챌린지는 SKIP.

## ★ 실격 방지 (반드시)

- Lambda 도구 내 **외부 모델/LLM/API 호출 금지**(우리 pathfinding.py는 순수 알고리즘 — 안전).
- 프롬프트에 **정답 하드코딩 금지**(Code_Specialist는 런타임 코드 실행으로 해결).
- 대회 **범위 밖 작업 금지**.

## 당일 동선 (~10분)

1. **도구**: Memory·Guardrails 생성 후 **Supervisor에 연결**. Lambda(`pathfinding.py` 붙여넣기 + 코드/웹 도구) 등록.
2. **Supervisor**: `prompts/supervisor.md` 붙여넣기, Memory·Guardrails 연결.
3. **서브에이전트 추가**: Pathfinding(기본) 확인 → Code_Specialist·Web_Researcher 추가, 각 Lambda 연결. (필요 시 Knowledge_Specialist)
4. **Recon → score_model 채움** ([adaptation-playbook.md](adaptation-playbook.md)) → `sim/config.json` 반영 → `python3 sim/robustness.py` 사전 확인.
5. **보드 플레이 → 반복 개선**.

## "변수 존재" — 당일 분기

| 발견 | 조치 |
|---|---|
| 특정 보너스 트리거 | 예비 슬롯에 전용 서브에이전트 / `score_model.bonus_triggers` |
| 웹 검색 도구 미제공 | Web_Researcher 제거, 해당 챌린지는 Supervisor가 신중 대응 |
| 코드 실행 도구 형태 상이 | Code_Specialist의 도구 연결만 교체(프롬프트 유지) |
| 슬롯 부족 | 일반상식을 Supervisor로 흡수해 슬롯 확보 |

→ 프롬프트·Lambda는 그대로, **연결/슬롯 + score_model 값**만으로 적응.
