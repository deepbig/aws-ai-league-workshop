# 멀티 에이전트 오케스트레이션 — UI 슬롯 배치도

워크샵 UI("Amazon Bedrock AgentCore를 사용하여 AI 에이전트 생성")의 빈 슬롯에
**무엇을 어디에 넣을지** 그대로 매핑. 스크린샷 기반 구조이므로 당일 동일하게 적용.

## UI 구성 요소(스크린샷)

- **도구 섹션**
  - AgentCore 메모리 (슬롯 0..N)
  - Amazon Bedrock Guardrails (슬롯 0..N)
  - AWS Lambda 함수 (슬롯 0..N)
- **멀티 에이전트 오케스트레이션**
  - 슈퍼바이저 1개 + **서브 에이전트 최대 5개** ("서브 에이전트 추가 (1/5)")
  - 노드 색: 에이전트(흰)/서브에이전트(노랑)/메모리(파랑)/가드레일(초록)/Lambda(빨강)

## 권장 배치 (전부 사전 준비됨)

```
[Memory: agent_memory]   [Guardrails: guardrail]
       │                          │
       └─────────┐    ┌───────────┘
                 ▼    ▼
            ┌─────────────────────┐
            │  Supervisor (슈퍼바이저)│ ← agent/prompts/supervisor.md
            │  Agent-Navigator     │
            └──────────┬───────────┘
                       │
   ┌───────────┬───────┼───────┬────────────┐
   ▼           ▼       ▼       ▼            ▼
Pathfinder  Code    Memory   Bonus       (예비)
서브에이전트  Specialist Curator  Hunter     ← 당일 발견 규칙에
   │           │       │       │            맞춰 추가
   ▼           ▼       ▼       ▼
[Pathfinding [CodeExec  (Memory  (조건부 Lambda
 Lambda]      내장 tool) tool 직접) 또는 미사용)
```

### 슬롯별 등록 내용

| UI 슬롯 | 등록 이름 | 내용 출처 |
|---|---|---|
| 도구 > 메모리 | `agent_memory` | (Memory는 정책/스키마가 본질, 실제 콘솔은 인스턴스 생성만) [memory-schema.md](memory-schema.md) |
| 도구 > Guardrails | `guardrail` | 정책 명세 [guardrails.md](guardrails.md) (Bedrock Guardrails 콘솔에서 출력 스키마·금지 패턴·주제 차단 입력) |
| 도구 > Lambda | `Pathfinding` | **코드 그대로** [lambdas/pathfinding.py](lambdas/pathfinding.py) |
| 슈퍼바이저 시스템 프롬프트 | — | [prompts/supervisor.md](prompts/supervisor.md) 본문 |
| 서브 에이전트 1: `Pathfinder` | 시스템 프롬프트 | [prompts/navigator.md](prompts/navigator.md) — `Pathfinding` Lambda 연결 |
| 서브 에이전트 2: `Code Specialist` | 시스템 프롬프트 | [prompts/challenge-solver.md](prompts/challenge-solver.md) — `CodeExecution` 도구 사용 (스크린샷에서 관찰된 패턴) |
| 서브 에이전트 3: `Memory Curator` | 시스템 프롬프트 | [prompts/memory-recon.md](prompts/memory-recon.md) — `agent_memory` 연결 |
| 서브 에이전트 4 (예비) | — | 당일 보너스 트리거 발견 시 `Bonus Hunter` 등으로 추가 |
| 서브 에이전트 5 (예비) | — | 그 외 변수 |

## 슈퍼바이저 ↔ 서브에이전트 위임 규칙

| 상황 (Supervisor가 판단) | 위임 대상 |
|---|---|
| 경로/이동 결정 필요 | `Pathfinder` (navigate Lambda 호출 → 좌표 시퀀스 반환) |
| Combat Log에 챌린지 문제 발견 | `Code Specialist` (CodeExecution으로 Python 실행 → 정답) |
| 게임 시작 / 규칙 단서 발견 / 상태 누적 | `Memory Curator` (`score_model`·맵·푼 챌린지 저장·조회) |

> Supervisor 프롬프트의 출력 스키마 한 줄(`RECON|NAVIGATE|SOLVE|...`)이 위임을
> 명시적으로 표현. Guardrails가 그 외 출력을 차단.

## 당일 동선 (브라우저에서 ~10분)

1. **도구 등록**
   - Memory `+` → 인스턴스 1개 생성(`agent_memory`).
   - Guardrails `+` → [guardrails.md](guardrails.md) 정책 입력 (또는 기본 `guardrail` 사용).
   - Lambda `+` → SageMaker 에디터 열림 → [lambdas/pathfinding.py](lambdas/pathfinding.py) 붙여넣기.
2. **슈퍼바이저 설정** → [prompts/supervisor.md](prompts/supervisor.md) 본문 붙여넣기. Memory·Guardrails 연결.
3. **서브 에이전트 추가 × 3** (Pathfinder/Code Specialist/Memory Curator):
   - 각각 [prompts/](prompts/)의 해당 파일 본문을 시스템 프롬프트로 붙여넣기.
   - Pathfinder ↔ `Pathfinding` Lambda 연결.
   - Code Specialist ↔ `CodeExecution`(내장 도구로 추정).
   - Memory Curator ↔ `agent_memory`.
4. **저장 → 보드 플레이**.
5. **Recon 1회 후 즉시 score_model 채움** ([adaptation-playbook.md](adaptation-playbook.md)) → `sim/config.json`에도 반영해 사전 검증.

## "변수 존재" — 당일 분기

| 발견 사실 | 슬롯 추가/변경 |
|---|---|
| 특정 보너스 트리거(연속 정답·전수집·특정 타일) | 서브 4: `Bonus Hunter` 추가 (Pathfinder에 보너스를 가치노드로 주입) |
| 규칙이 단순 → 슬롯 압박 | Memory Curator를 Supervisor에 흡수(Supervisor가 Memory 직접 read/write) |
| 챌린지 매우 무거움 | Code Specialist 프롬프트에 2-방법 검산 강화 |
| 경로가 비결정적(맵 점진 공개) | Pathfinder를 receding-horizon 모드로(짧은 구간만 호출) |

→ 프롬프트/Lambda는 거의 그대로, **slot 추가/연결만으로 적응**.
