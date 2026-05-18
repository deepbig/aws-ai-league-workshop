# 03. 에이전트 아키텍처

분석 대상: [assets/key-images/agent-architecture.png](../assets/key-images/agent-architecture.png)

---

## 1. 안내자료 제시 아키텍처 [확정]

다이어그램 구성 요소(이미지에서 직접 판독):

```
                         AgentCore Runtime  (점선 박스 = 실행 컨테이너)
                        ┌─────────────────────────────────────┐
   Bedrock              │            Supervisor Agent          │            AgentCore
   Guardrails  ───────▶ │                  │                   │ ─────────▶  Memory
   (입출력 제어)         │     ┌────────────┼────────────┐      │            (기억/재사용)
                        │  Sub-Agent     Sub-Agent    Sub-Agent│
                        └─────┼────────────┼────────────┼──────┘
                              └────────────┼────────────┘
                                           ▼
                                   AgentCore Gateway
                                           │
                              ┌────────────┴───────────────┐
                          Navigation/Tool   Code Interpreter / Lambda Tools
```

- **AgentCore Runtime**: 에이전트들이 실제 실행되는 격리 환경.
- **Supervisor Agent**: 상위 조율자. 작업을 분해해 Sub-Agent에 위임.
- **Sub-Agents (다수)**: 전문화된 하위 에이전트(예: 탐색 담당 / 챌린지 풀이 담당 / 의사결정 담당).
- **AgentCore Gateway**: 에이전트 ↔ 외부 도구 연결 통로. Lambda 기반 Tool 호출.
- **AgentCore Memory**: 중요한 정보(힌트·키 값·이전 응답·맵) 저장/재사용.
- **Bedrock Guardrails**: 입력/출력 제어, 부적절·규칙이탈 응답 차단.

> 안내자료: 워크샵에서 에이전트 생성·역할 정의·도구/메모리/가드레일 연결, 모델 선택, Lambda Tool 호출, 결과 활용을 다룸.

---

## 2. 1등을 위한 권장 설계 [추론 — 검증 대상]

게임 메커니즘([docs/02](02-game-mechanics.md))에 맞춘 역할 분해:

### Supervisor Agent — "게임 마스터"
- 입력: 현재 맵 상태, 코인/생명/타이머, 미해결 챌린지.
- 책임: **턴마다 무엇을 할지 결정** (이동 / 코인 수집 / 챌린지 풀이 / 보물 추적 / 회피).
- 핵심: 시간·생명 예산 하에서 **기대 점수 최대 행동** 선택. 결정론적이고 간결한 정책 프롬프트.

### Sub-Agent A — Navigator (경로/탐색)
- Navigation Tool(Lambda) 호출로 경로 계산.
- 알고리즘: BFS/A\* + **예산 제약 코인 수집 최적화**(가치/거리 비 우선, 시간 내 회수 가능 노드만).
- 출력: 다음 이동 시퀀스 (좌표 기반, 결정론적).

### Sub-Agent B — Challenge Solver (챌린지 풀이)
- 입력: Combat Log의 문제 텍스트.
- **반드시 Code Interpreter / Lambda로 계산 실행 후 답 산출** (암산 금지 — 오답 = 생명/점수 손실).
- 출력: 규정 포맷의 정답만. (Guardrails로 포맷 강제)

### Sub-Agent C — Memory/Recon (상태 관리)
- 탐색한 맵·벽·코인 위치, 푼 챌린지 유형·정답 패턴, 적 위치를 AgentCore Memory에 기록.
- 재방문/재계산 회피, 후속 챌린지 가속.

### Guardrails
- 답안 출력 스키마 고정(예: 숫자만 / JSON 한 줄).
- 무한 루프·무의미 이동·금지 행동 차단. 추가 규칙[당일] 반영.

### Memory 운영
- 키: `map_layout`, `collected_coins`, `solved_challenges`, `enemy_positions`, `treasure_clues`.
- System Prompt에서 "행동 전 Memory 조회 → 행동 후 Memory 갱신" 루프 명시.

---

## 3. 모델 선택 [추론]

- **Supervisor/Solver**: 가장 강한 추론 모델(정답률·계획 품질이 점수 직결). 단, **반드시 코드 실행으로 검산**.
- **Navigator**: 결정론적 알고리즘(Lambda 코드)이 LLM보다 정확·저렴 → LLM은 호출/해석만.
- 비용보다 **정확도·반복 속도** 우선(워크샵 인프라 비용은 주최 제공).

## 4. 검증 포인트 (당일)

- [ ] Sub-Agent 개수/위임 방식 실제 제약 확인
- [ ] Navigation Tool이 제공되는지 / 직접 구현인지
- [ ] Code Interpreter 사용 가능 여부 (챌린지 풀이 전제)
- [ ] 행동 인터페이스(좌표 이동 vs 자연어 명령) 확정
- [ ] Memory 용량/지속성 제약
