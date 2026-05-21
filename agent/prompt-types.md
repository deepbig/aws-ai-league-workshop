# 프롬프트 유형 — System vs Runtime (중요 제약)

워크샵 가이드라인 확정 사항. 무엇을 우리가 제어할 수 있고 없는지 명확히.

## 1. System Prompt (우리가 작성·제어)

- 에이전트의 **행동·역량·도구 사용법**을 정의하는 기반 지시문. 게임 내내 적용.
- 에이전트별로 존재: Supervisor + 각 서브에이전트. → [prompts/](prompts/)
- **새 도구를 추가하면 반드시 system prompt를 수정**해 에이전트가 그 도구를 쓸 줄 알게 해야 함.
  (예: Web 검색 Lambda 추가 → Web_Researcher 프롬프트에 호출법 명시)

## 2. Runtime Prompt (대부분 제어 불가)

- 매 턴/매 챌린지에 전달되는 프롬프트.
- **챌린지 runtime prompt는 게임이 자동 생성하며 수정 불가.**
- **우리가 제어 가능한 runtime prompt는 단 하나 — Navigation prompt(아래).**

> ★ 핵심 함의: 챌린지별 지시를 따로 주입할 수 없다. 따라서 **모든 챌린지 대응 로직은
> system prompt에 self-contained**로 담겨야 한다. 서브에이전트 프롬프트는 해당 유형의
> 어떤 챌린지가 와도 처리할 수 있도록 일반화되어 있어야 한다(특정 문제 가정 금지).

## 3. Navigation Prompt (우리가 제어하는 유일한 runtime prompt)

- Submit & Play 직전 입력. 런타임에 전달되어 **pathfinding lambda가 'strategy'로 처리**.
- 사용법: `use strategy max_loot` (또는 swift / get_coins / 커스텀).
- 세션 동안 **메모리에 주입**될 수도 있음(활용 방식은 가변) → 전략 의도를 메모리에 심어
  Supervisor 결정에 일관되게 반영 가능.

## 4. Delegation Prompt (Supervisor 내부)

- Supervisor가 서브에이전트에 **어떻게 위임**할지 제어. supervisor.md의 DELEGATE 항목.
- 챌린지 유형 → 담당 서브에이전트 라우팅을 명시(수학→Code_Specialist 등).

## 5. Prompt Constraints (출력 제어)

- 출력을 **제한/변형**해 원하는 형태로: "정답만, 설명 금지"(LLM-judge 포맷), 간결화(토큰 보너스).
- Guardrails와 함께 출력 스키마·안전성 강제.

## Key Learnings (가이드 요약)

- System prompt와 runtime prompt의 차이를 이해한다.
- 도구와 효율적으로 동작하도록 system prompt를 수정한다.
- 출력을 제어하도록 system prompt를 수정한다.
- runtime prompt는 챌린지마다 전송된다(자동 생성, 수정 불가 — Navigation 제외).
- **생성형 AI(Code Editor의 Amazon Q 등)로 프롬프트를 개선**한다.

> 적용: 본 저장소의 [prompts/](prompts/)는 전부 **system prompt**다. 챌린지 대응은
> 여기에 일반화되어 있어 runtime 주입 없이도 동작한다. 유일한 runtime 제어는
> Navigation prompt(`use strategy max_loot`).
