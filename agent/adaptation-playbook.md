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
| **보물 도달=게임종료** | (전략) | `use strategy max_loot` — 코인 최대 수집 후 마지막에 보물(swift 금지) |
| 챌린지 배점 ≫ 코인 | `challenge_score.gain↑` | 챌린지를 경로 1순위 |
| 오답 차감 큼 | `challenge_score.loss↑` | 저신뢰 챌린지 SKIP(기대값 음수 회피) |
| 코인 가치 차등 | `coin_value.type=varied` | navigate가 가치가중 경로 산출 |
| **남은 생명 점수 큼** | `life_value↑` | 장애물·위험 전투 회피 가중↑(생명 보존=득점) |
| **장애물 빈번** | `obstacle_rule` | Pathfinder가 obstacles 우회(비용 가산) |
| **막힘 구간 존재** | `blocked_rule` | grid=벽 표기 → 경로 절대 미경유 + Guardrails 차단 |
| **토큰 보너스 큼** | `token_bonus↑` | 출력 더 축약, 호출 최소화, Memory 캐시 적극 |
| **웹서치 챌린지 비중↑** | `type_confidence.web` | Web Researcher 검색 횟수/교차확인 강화 |
| **안정성 챌린지 비중↑** | `type_confidence.safety` | Guardrails + Knowledge&Safety 균형(과도거절 방지) |
| 연속정답/전수집 보너스 | `bonus_triggers+=` | 트리거를 navigate 목표에 1급 삽입 |
| 답안 포맷 규정 | `answer_format` | Guardrails 출력 스키마 갱신 |
| 행동 인터페이스가 자연어 | (Guardrails) | Supervisor 출력 스키마 재정의 |

→ 어느 경우든 **프롬프트는 그대로**, Memory `score_model`/Guardrails 파라미터만 교체.

> ★ 실격 금지(절대): 도구 내 외부 모델/API 호출, 프롬프트 정답 하드코딩, 범위 외 작업.
> 챌린지는 런타임 해결(코드 실행/웹 검색/추론)만으로 푼다.

## 반복 개선 (사이클당 1변수)

```
플레이 → run_stats 로그 → 실패유형 분류
  게임강제종료 → ★막힘 셀 이동 발생: grid 벽 표기·Guardrails 차단 즉시 점검(최우선)
  경로비효율   → navigate mode=precise / value 규칙·obstacles 입력 점검
  챌린지오답   → 유형별 도구 라우팅 확인(math→코드, web→검색) / 2-방법 검산
  챌린지감점   → 저신뢰(type_confidence 낮음) 챌린지 SKIP 임계 상향
  시간초과     → 조기 END 임계 / 저가치 원거리 포기 (5분 예산)
  생명손실     → 장애물 회피 가중↑(life_value 반영) / 위험 전투 회피
  토큰과다     → 출력 축약 / 중복 호출 제거 / Memory 캐시 (토큰 보너스)
  규칙오해     → Recon 재실행, score_model.unknowns 해소
→ 가장 큰 손실원 1개만 수정 → 재플레이 → 귀속 확인
```
- AI Assistant 입력 세트: (로그 + 본 플레이북 + 현재 score_model + sim 결과).
- 변경 1건 = 비교 1쌍. 두 변수 동시 변경 금지(귀속 불가).

## 강건성 사전 검증

`sim/`에 여러 가상 규칙 레짐을 넣어, 위 정책이 레짐이 바뀌어도
상위권을 유지하는지 사전 확인(로드맵: [docs/07](../docs/07-simulation-plan.md) §강건성).
목적: 당일 어떤 규칙이 나와도 "정책 구조는 그대로, 값만 교체"가 통함을 보장.
