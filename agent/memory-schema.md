# AgentCore Memory 스키마

> **Memory는 Supervisor 전용**(폼 확정). 서브에이전트는 Memory 접근 불가 →
> Supervisor가 직접 저장/조회하고, 필요한 컨텍스트를 위임 시 함께 전달.

행동 경계마다 조회/갱신. "행동 전 조회 → 행동 후 갱신" 루프를 Supervisor 프롬프트에 명시.

| 키 | 내용 | 갱신 시점 |
|---|---|---|
| `score_model` | 당일 발견한 채점 규칙(구조화). 정책 구동의 핵심 | Recon / 규칙 변동 감지 |
| `nav_strategy` | Navigation prompt 전략(예: `max_loot`) — 메모리에 주입돼 결정 일관화 | 레벨 시작/전략 변경 |
| `map_layout` | 벽·통로·아이템 mapId(c1..cN) 위치(점진 공개 시 누적) | 새 영역 관측 |
| `collected` | 이미 획득한 코인/보물 mapId | COLLECT 후 |
| `solved_challenges` | 챌린지 유형 → 해법/정답 캐시 | SOLVE 성공 후 |
| `enemy_positions` | 적·챌린지 노드 mapId | 관측 시 |
| `treasure_clues` | 보물 단서/추정 위치 | 단서 획득 시 |
| `policy_params` | 정책 튜닝값(임계치 등). 반복 개선으로 조정 | 개선 사이클 |
| `run_stats` | 점수·실패유형·Guardrails 위반 로그 | 매 턴/에피소드 |

## `score_model` 구조 (변수 상황 적응의 중심)

```json
{
  "time_limit_sec":  300,                       // 제한시간 5분(확정)
  "coin_value":      {"type": "uniform|varied", "rule": "<관측 규칙>"},
  "treasure_value":  <int>,
  "challenge_score": {"gain": <int>, "loss": <int>},   // 정답 획득 / 오답 차감
  "challenge_types": ["math", "web", "knowledge", "safety"],  // 4종
  "type_confidence": {"math": 1.0, "web": <0~1>, "knowledge": <0~1>, "safety": <0~1>},
  "life_value":      <int>,                      // 남은 생명 1개당 점수(확정: 생명=점수)
  "obstacle_rule":   {"life_cost": 1, "avoidable": true},  // 장애물(회피 가능)
  "blocked_rule":    "강제 통과 시 게임 종료",     // 막힘 구간(치명적)
  "token_bonus":     {"exists": true, "rule": "<효율 보상 규칙>"},  // 토큰 보너스
  "bonus_triggers":  [{"when": "<조건>", "reward": <int>}],
  "answer_format":   "<제출 포맷>",
  "judge":           "LLM-as-judge(별도 환경)",   // 응답 품질 평가
  "unknowns":        ["<미파악 항목>"]
}
```

- `type_confidence`가 낮은 챌린지(예: 불확실 웹/상식)는 `challenge_score.loss`가 크면
  Supervisor가 SKIP(기대값 음수 회피).
- `life_value`·`obstacle_rule`로 회피 정책이 점수와 직접 연결.
- `token_bonus` 존재 시 출력 축약·Memory 캐시 재사용으로 보너스 확보.

- Supervisor 정책은 이 값을 읽어 우선순위를 **재계산**(프롬프트 불변, 값만 변경).
- `unknowns`가 비워질수록 행동 최적성↑ → Recon이 초반 최우선.
- 시뮬레이터 `sim/config.json`은 이 `score_model`의 사전 검증용 미러.
