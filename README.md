# AWS AI League — 1등 준비 저장소

AWS AI League 워크샵(경쟁형 핸즈온)에서 **최고 점수로 1등**을 하기 위한 저장소입니다.
워크샵의 본질은 **AgentCore LLM 에이전트를 만들고 반복 개선**하는 것 → 중심 문서는
**[docs/09-agent-design.md](docs/09-agent-design.md)** 와 배포 산출물 **[`agent/`](agent/)**.

> 출처: `AWS AI League 워크샵 사전 안내자료` (Notion → PDF, 12p).
> 원문 텍스트 추출본은 [`assets/source-text-extract.txt`](assets/source-text-extract.txt),
> 원본 페이지 이미지는 [`assets/guide-pages/`](assets/guide-pages/)에 보관.

---

## 30초 요약

- **무엇인가**: 강의가 아니라 **경쟁형 워크샵**. 제한 시간 안에 그리드 미로 지도를 탐색하는 **AI 에이전트를 만들고 반복 개선**해 점수를 높이는 대회.
- **무엇으로 만드나**: **Amazon Bedrock AgentCore** 중심. Supervisor + Sub-Agents 멀티에이전트 구조에 **Memory / Tools(Gateway) / Guardrails / Lambda**를 연결. 코드는 SageMaker 내장 에디터 + Lambda(Python).
- **게임 목표(확정)**: *"보물을 찾으면서 모든 코인을 수집하고 챌린지를 물리치세요!"* — 코인(점수), 생명 3개, 카운트다운 타이머, 챌린지(추론/수학 문제) 풀이.
- **에이전트 설계(중심)**: Supervisor + Sub-Agents(Navigator/Challenge Solver/Memory-Recon). **LLM은 판단, 계산은 결정론적 Tool**; **챌린지는 전량 Code Interpreter**; **정책은 규칙 파라미터(score_model)의 함수** → 당일 규칙이 바뀌어도 프롬프트 불변, 값만 교체. 실제 프롬프트·Tool 계약·Guardrails: [`agent/`](agent/).
- **확정 규칙 반영**: 제한시간 5분 / 점수원 4종(코인·보물·**토큰 보너스**·**남은 생명**) / 장애물(생명-1, 회피가능) / **막힘 구간 강제통과=게임종료** / 챌린지 4종(상식·수학알고리즘·**안정성**·**웹서치**, 점수 획득·차감) / **LLM-as-judge 채점**. → 서브에이전트 5종·Guardrails·회피정책에 반영.
- **변수 상황 강건성(검증)**: 6개 규칙 레짐 전부에서 권장 정책이 **진짜 최적해의 100%**(naive 9~21%, 페널티중심 레짐은 음수) — 생명=점수를 반영하면 격차가 더 큼. "구조 불변, 값만 교체"로 미지의 당일 규칙 적응. `python3 sim/robustness.py`.
- **하위 근거**: 경로는 LLM 추정 대신 검증된 navigate Tool(진짜 최적의 99.8~100%, Held-Karp 검증)에 위임 — [docs/08](docs/08-routing-findings.md).
- **중요**: **세부 채점식·보너스·챌린지·추가 규칙은 워크샵 당일 공개**됩니다. 안내자료의 해당 영역은 의도적으로 가려져 있음 → 본 저장소는 *관찰로 확정된 것*과 *추론*, *당일 확인 필요*를 명확히 구분해 정리.

---

## 문서 가이드

| 문서 | 내용 |
|---|---|
| [docs/01-overview.md](docs/01-overview.md) | 워크샵이 무엇인지, 형식, 진행 방식 |
| [docs/02-game-mechanics.md](docs/02-game-mechanics.md) | **게임 화면 정밀 분석** — UI·규칙·챌린지(이미지 기반) |
| [docs/03-agent-architecture.md](docs/03-agent-architecture.md) | **에이전트 아키텍처 다이어그램 분석** + 1등용 설계 |
| [docs/04-aws-services.md](docs/04-aws-services.md) | AgentCore/Memory/Gateway/Guardrails/Lambda 치트시트 |
| [docs/05-prep-checklist.md](docs/05-prep-checklist.md) | **행사 전 필수 준비** 체크리스트 |
| [docs/06-winning-strategy.md](docs/06-winning-strategy.md) | **1등 전략** — 점수 극대화 플레이북 |
| [docs/07-simulation-plan.md](docs/07-simulation-plan.md) | 시뮬레이터 설계 + 당일 운영 루프 |
| [docs/08-routing-findings.md](docs/08-routing-findings.md) | (부속) Navigator Tool 설계 근거 — 라우팅 알고리즘 검증 |
| **[docs/09-agent-design.md](docs/09-agent-design.md)** | **★ AgentCore LLM 에이전트 실전 청사진 (중심 문서)** |
| **[agent/](agent/)** | **★ 배포 산출물**: 시스템 프롬프트·Tool 계약·Guardrails·Memory·당일 적응 플레이북 |
| [sim/](sim/) | 시뮬레이터: 정책 강건성 검증(`robustness.py`) + Tool 알고리즘 벤치 |

## 표기 규칙

문서 전반에서 다음 태그로 신뢰도를 구분합니다.

- **[확정]** — 안내자료 텍스트/이미지에서 직접 확인됨
- **[추론]** — 화면·구조로부터 합리적으로 도출 (검증 필요)
- **[당일]** — 워크샵 당일 공개. 사전엔 가려져 있음 → 당일 최우선 확인 항목

## 핵심 이미지

| 파일 | 설명 |
|---|---|
| [assets/key-images/game-play.png](assets/key-images/game-play.png) | 게임 플레이 화면 (코인/생명/타이머/맵/Combat Log) |
| [assets/key-images/agent-architecture.png](assets/key-images/agent-architecture.png) | AgentCore 멀티에이전트 아키텍처 |
| [assets/key-images/objective-and-tabs.png](assets/key-images/objective-and-tabs.png) | 목표 + 도구/보너스/챌린지 탭 (가려진 규칙 영역 포함) |
