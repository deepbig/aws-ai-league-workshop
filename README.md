# AWS AI League — 1등 준비 저장소

AWS AI League 워크샵(경쟁형 핸즈온)에서 **최고 점수로 1등**을 하기 위한 분석·전략·시뮬레이션 저장소입니다.

> 출처: `AWS AI League 워크샵 사전 안내자료` (Notion → PDF, 12p).
> 원문 텍스트 추출본은 [`assets/source-text-extract.txt`](assets/source-text-extract.txt),
> 원본 페이지 이미지는 [`assets/guide-pages/`](assets/guide-pages/)에 보관.

---

## 30초 요약

- **무엇인가**: 강의가 아니라 **경쟁형 워크샵**. 제한 시간 안에 그리드 미로 지도를 탐색하는 **AI 에이전트를 만들고 반복 개선**해 점수를 높이는 대회.
- **무엇으로 만드나**: **Amazon Bedrock AgentCore** 중심. Supervisor + Sub-Agents 멀티에이전트 구조에 **Memory / Tools(Gateway) / Guardrails / Lambda**를 연결. 코드는 SageMaker 내장 에디터 + Lambda(Python).
- **게임 목표(확정)**: *"보물을 찾으면서 모든 코인을 수집하고 챌린지를 물리치세요!"* — 코인(점수), 생명 3개, 카운트다운 타이머, 챌린지(추론/수학 문제) 풀이.
- **핵심 변수**: ① 경로탐색(코인·보물 효율) ② 챌린지 정답률(코드 실행으로 계산) ③ Memory 활용 ④ 시간·생명 리스크 관리 ⑤ 프롬프트 엔지니어링.
- **시뮬레이션 규명(완료)**: 게임을 Orienteering 문제로 환원 → 강한 플래너(ILS/앙상블)가 **진짜 최적해의 99.8~100%** 달성(Held-Karp DP로 검증). 실시간용 `greedy+LS`는 ~99.8%·15ms. 단순 그리디 대비 **약 +17%**. 상세 [docs/08](docs/08-routing-findings.md).
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
| [docs/08-routing-findings.md](docs/08-routing-findings.md) | **시뮬레이션 결과** — 점수 최대화 경로 방법 규명(최적해 99.8%+) |
| [sim/](sim/) | 실행 가능한 **시뮬레이터** (플래너 7종 + 진짜 최적해 검증) |

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
