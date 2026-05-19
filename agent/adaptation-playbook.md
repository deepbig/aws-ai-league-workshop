# 당일 규칙 적응 플레이북

워크샵 핵심 난이도 = **미지의 규칙을 빨리 파악하고 행동을 바꾸는 것**.
정책은 고정, **`score_model` 값만 바꿔** 적응한다.

## T-0 ~ 첫 플레이 전 (Recon)

1. 인게임 정독: 목표 / **극대화하는 방법** / **추가 규칙** / **챌린지 탭** / **보너스 탭** + 워크숍 스튜디오 문서.
2. 읽은 즉시 [agent/memory-schema.md](memory-schema.md)의 `score_model` 채움. 모르면 `unknowns`에.
3. 동일 값을 `sim/config.json`에 입력 → `python3 sim/bench.py`로 어떤 우선순위가 최고인지 사전 확인.
4. `unknowns`는 첫 플레이에서 *관측 대상*으로 지정(예: 오답 시 실제 손실 확인).

## 규칙 → 행동 변경 의사결정 트리

| 관측된 규칙 | score_model 변경 | 정책 자동 반응 |
|---|---|---|
| 챌린지 배점 ≫ 코인 | `challenge_score↑` | 챌린지를 경로 1순위, 전투 적극 |
| 코인 가치 차등 | `coin_value.type=varied` | navigate가 가치가중 경로 산출 |
| 오답 페널티 큼 | `wrong_penalty↑` | 미검증 답안 제출 보류(2-방법 검산만) |
| 연속정답/전수집 보너스 | `bonus_triggers+=` | 트리거를 navigate 목표에 1급 삽입 |
| 시간 보너스 존재 | `time_rule.bonus_per_step` | 한계가치<보너스 시 조기 END |
| 생명 소모 트리거 변경 | `life_rule` | 위험 회피 게이트 갱신 |
| 답안 포맷 규정 | `answer_format` | Guardrails 출력 스키마 갱신 |
| 행동 인터페이스가 자연어 | (Guardrails) | Supervisor 출력 스키마 재정의 |

→ 어느 경우든 **프롬프트는 그대로**, Memory `score_model`/Guardrails 파라미터만 교체.

## 반복 개선 (사이클당 1변수)

```
플레이 → run_stats 로그 → 실패유형 분류
  경로비효율  → navigate mode=precise / score_model.value 규칙 점검
  챌린지오답  → solver 2-방법 검산 강제 / answer_format 확인
  시간초과    → 조기 END 임계 / 저가치 원거리 포기
  생명손실    → life_rule 갱신 / 위험 회피 게이트
  규칙오해    → Recon 재실행, score_model.unknowns 해소
→ 가장 큰 손실원 1개만 수정 → 재플레이 → 귀속 확인
```
- AI Assistant 입력 세트: (로그 + 본 플레이북 + 현재 score_model + sim 결과).
- 변경 1건 = 비교 1쌍. 두 변수 동시 변경 금지(귀속 불가).

## 강건성 사전 검증

`sim/`에 여러 가상 규칙 레짐을 넣어, 위 정책이 레짐이 바뀌어도
상위권을 유지하는지 사전 확인(로드맵: [docs/07](../docs/07-simulation-plan.md) §강건성).
목적: 당일 어떤 규칙이 나와도 "정책 구조는 그대로, 값만 교체"가 통함을 보장.
