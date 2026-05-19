# AgentCore Memory 스키마

행동 경계마다 조회/갱신. "행동 전 조회 → 행동 후 갱신" 루프를 모든 프롬프트에 명시.

| 키 | 내용 | 갱신 시점 |
|---|---|---|
| `score_model` | 당일 발견한 채점 규칙(구조화). 정책 구동의 핵심 | Recon / 규칙 변동 감지 |
| `map_layout` | 벽·통로·좌표계(점진 공개 시 누적) | 새 영역 관측 |
| `collected` | 이미 획득한 코인/보물 좌표 | COLLECT 후 |
| `solved_challenges` | 챌린지 유형 → 해법/정답 캐시 | SOLVE 성공 후 |
| `enemy_positions` | 적·챌린지 노드 위치 | 관측 시 |
| `treasure_clues` | 보물 단서/추정 위치 | 단서 획득 시 |
| `policy_params` | 정책 튜닝값(임계치 등). 반복 개선으로 조정 | 개선 사이클 |
| `run_stats` | 점수·실패유형·Guardrails 위반 로그 | 매 턴/에피소드 |

## `score_model` 구조 (변수 상황 적응의 중심)

```json
{
  "coin_value":   {"type": "uniform|varied", "rule": "<관측 규칙>"},
  "challenge_score": <int>,
  "wrong_penalty":   {"score": <int>, "lives": <int>},
  "bonus_triggers":  [{"when": "<조건>", "reward": <int>}],
  "time_rule":       {"bonus_per_step": <num>, "penalty": "<유무>"},
  "life_rule":       "<생명 소모 트리거>",
  "answer_format":   "<제출 포맷>",
  "unknowns":        ["<미파악 항목>"]
}
```

- Supervisor 정책은 이 값을 읽어 우선순위를 **재계산**(프롬프트 불변, 값만 변경).
- `unknowns`가 비워질수록 행동 최적성↑ → Recon이 초반 최우선.
- 시뮬레이터 `sim/config.json`은 이 `score_model`의 사전 검증용 미러.
