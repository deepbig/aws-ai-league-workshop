# 멀티 에이전트 오케스트레이션 — UI 슬롯 배치도

워크샵 UI("Amazon Bedrock AgentCore를 사용하여 AI 에이전트 생성")의 빈 슬롯에
**무엇을 어디에 넣을지** 매핑. 당일 확정 규칙(챌린지 4종·생명=점수·막힘=게임오버·토큰보너스) 반영.

## UI 구성 요소 (스크린샷)

- **도구 섹션**: AgentCore 메모리 / Amazon Bedrock Guardrails / AWS Lambda 함수
- **멀티 에이전트 오케스트레이션**: 슈퍼바이저 1 + **서브 에이전트 최대 5개**
- 노드 색: 에이전트(흰)/서브에이전트(노랑)/메모리(파랑)/가드레일(초록)/Lambda(빨강)

## 권장 배치 — 서브에이전트 5슬롯 풀가동

챌린지가 4종(상식·수학/알고리즘·안정성·웹서치)이므로 슬롯을 다음과 같이 채운다.

```
[Memory: agent_memory]   [Guardrails: guardrail]
       └──────────┐   ┌──────────┘
                  ▼   ▼
            ┌──────────────────────┐
            │ Supervisor (슈퍼바이저) │ ← prompts/supervisor.md
            └───────────┬───────────┘
        ┌──────┬────────┼────────┬──────────┐
        ▼      ▼        ▼        ▼          ▼
   Pathfinder Code   Web      Knowledge   Memory
              Specialist Researcher &Safety    Curator
        │      │        │        │          │
        ▼      ▼        ▼        ▼          ▼
  [Pathfinding [Code   [Web    (Guardrails  [agent_memory]
   Lambda]      Exec]   Search) 연계)
```

### 슬롯별 등록 내용

| UI 슬롯 | 등록 이름 | 출처 |
|---|---|---|
| 도구 > 메모리 | `agent_memory` | [memory-schema.md](memory-schema.md) |
| 도구 > Guardrails | `guardrail` | [guardrails.md](guardrails.md) (출력 스키마·막힘이동 차단·안전응답) |
| 도구 > Lambda | `Pathfinding` | **코드 그대로** [lambdas/pathfinding.py](lambdas/pathfinding.py) |
| 슈퍼바이저 프롬프트 | — | [prompts/supervisor.md](prompts/supervisor.md) |
| 서브1 `Pathfinder` | 프롬프트 + `Pathfinding` 연결 | [prompts/navigator.md](prompts/navigator.md) |
| 서브2 `Code Specialist` | 프롬프트 + `CodeExecution` | [prompts/challenge-solver.md](prompts/challenge-solver.md) |
| 서브3 `Web Researcher` | 프롬프트 + 웹검색 도구 | [prompts/web-researcher.md](prompts/web-researcher.md) |
| 서브4 `Knowledge & Safety` | 프롬프트 (+ Guardrails 연계) | [prompts/knowledge-safety.md](prompts/knowledge-safety.md) |
| 서브5 `Memory Curator` | 프롬프트 + `agent_memory` | [prompts/memory-recon.md](prompts/memory-recon.md) |

> 슬롯 압박 시 대안: 규칙이 단순하면 Memory Curator를 Supervisor에 흡수(Supervisor가
> Memory 직접 read/write)해 1슬롯을 당일 신규 변수용으로 비워둠.

## 챌린지 유형 → 위임 라우팅 (Supervisor가 결정)

| 챌린지 유형 | 위임 대상 | 도구 |
|---|---|---|
| 수학/알고리즘 | Code Specialist | CodeExecution |
| 웹 서치 | Web Researcher | 웹 검색 |
| 일반 상식 | Knowledge & Safety | LLM(필요 시 웹 재라우팅) |
| 안정성(safety) | Knowledge & Safety | LLM + Guardrails |

| 게임 상황 | 위임 대상 |
|---|---|
| 경로/이동 결정 | Pathfinder (막힘 회피·장애물 우회 포함) |
| 규칙 단서/상태 누적 | Memory Curator |

## 점수 레버 반영 (확정 규칙)

- **생명 = 점수**: Pathfinder가 장애물(생명 -1) 회피, Supervisor가 위험 전투 회피.
- **막힘 = 게임오버**: 막힘 셀은 grid '벽'으로 표기 → Pathfinding이 절대 경유 안 함.
  Guardrails가 막힘 이동을 추가 차단(이중 안전).
- **토큰 보너스**: 모든 프롬프트가 '정답만/짧게' 출력. 같은 유형 재출제는 Memory 캐시.
- **점수 차감**: 신뢰도 낮은 챌린지는 Supervisor가 기대값 음수면 SKIP.

## 당일 동선 (~10분)

1. **도구 등록**: Memory 인스턴스 + Guardrails([guardrails.md](guardrails.md)) +
   Lambda([lambdas/pathfinding.py](lambdas/pathfinding.py) 붙여넣기) + 웹검색 도구 확인.
2. **슈퍼바이저**: [prompts/supervisor.md](prompts/supervisor.md) 붙여넣기, Memory·Guardrails 연결.
3. **서브 에이전트 5개 추가**: 위 표대로 프롬프트 + 도구 연결.
4. **Recon → score_model 채움** ([adaptation-playbook.md](adaptation-playbook.md)) → `sim/config.json` 반영 → `python3 sim/robustness.py`로 사전 확인.
5. **보드 플레이 → 반복 개선**.

## "변수 존재" — 당일 분기

| 발견 사실 | 조치 |
|---|---|
| 특정 보너스 트리거 | `score_model.bonus_triggers` 추가 → Pathfinder가 가치노드로 반영 |
| 특정 챌린지 유형 비중 큼 | 해당 서브에이전트 프롬프트 강화(검산·검색 횟수) |
| 토큰 보너스 비중 큼 | 출력 더 축약, 저신뢰 챌린지 SKIP 임계 상향 |
| 생명 점수 가치 큼 | 장애물 회피·위험 회피 가중 상향(life_value↑) |
| 웹검색 도구 미제공 | Web Researcher를 Knowledge로 흡수, 해당 챌린지 신중 대응 |

→ 프롬프트/Lambda 거의 그대로, **slot 연결 + score_model 값만**으로 적응.
