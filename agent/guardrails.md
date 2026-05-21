# Bedrock Guardrails 설정 (이 게임용)

목적: 에이전트가 **챌린지 규칙을 벗어나지 않고 의도한 포맷으로** 동작하도록 입출력 제어.
무효 행동·파싱 실패·규칙 위반을 0으로.

## 출력 스키마 강제

| 대상 | 허용 출력 | 차단 |
|---|---|---|
| Supervisor | `RECON\|NAVIGATE\|SOLVE\|MOVE\|COLLECT\|END` 한 줄 정확 | 사고과정·설명·여러 행동·스키마 외 |
| Challenge Solver | `score_model.answer_format` 정확히 일치 | 단위·설명·여분 공백·근사(요구 없을 시) |
| Navigator | navigate Tool 반환 경로 그대로 | LLM 생성 경로·좌표 변형 |

## 행동 유효성

- **막힘(통과 불가) 셀로의 MOVE 차단 ★최우선** — 강제 통과 시 게임 즉시 종료(치명적).
  Pathfinder 검증 경로만 허용, 그 외 좌표 이동 거부.
- 벽/맵 밖/도달 불가 좌표로의 MOVE 차단.
- 회피 가능 장애물(생명 -1) 경유 경고 — 남은 생명=점수이므로 회피 우선.
- 시간(5분)·생명 예산 초과 행동 차단.
- 코드 미실행 상태의 수학 챌린지 답안 제출 차단(검증 플래그 필수).
- score_model 미파악 상태에서 비-RECON 행동 억제(초반).

## 안정성(safety) 챌린지 — 득점 역할

- 안정성 챌린지에서는 Guardrails가 **점수원**: 유해/부적절 요청 차단 + 안전 응답 유도.
- 단, **과도한 거절(over-refusal) 방지** — 무해한 요청은 정상 통과시켜 유용성 점수 확보.
- Knowledge & Safety Responder([prompts/knowledge-safety.md](prompts/knowledge-safety.md))와 연계.

## 규칙 준수

- 당일 "추가 규칙"에서 금지된 행동/입력 패턴을 거부 목록에 등록(파라미터화).
- 프롬프트 인젝션/주제 이탈(게임 외 대화) 차단.

## 운영

- 규칙 항목은 **Guardrails 정책 파라미터로 외부화** → 당일 값만 갱신, 정책 구조 불변.
- 위반 발생 로그를 Memory `run_stats`에 적재 → 반복 개선 루프 입력.
