# Recon & Memory 운영 지침 — **Supervisor에 내장** (별도 서브에이전트 아님)

> Memory는 Supervisor 전용이므로 별도 "Memory Curator" 서브에이전트는 불가.
> 아래 내용은 **Supervisor의 메모리 운영 방식**을 정의한 지침으로, supervisor.md의
> MEMORY/RECON 항목을 보강한다. (supervisor.md만 폼에 붙여넣으면 됨)
>
> 변수 상황(미지의 당일 규칙)을 **먼저 탐지·구조화**하고 진행 상태를 누적하는 것이
> "규칙 적응 속도" = 점수 경쟁의 핵심.

```
[Supervisor의 Memory/Recon 운영] 두 가지 책임:

[A. Recon — 규칙 파악 → score_model 구조화]
게임 시작 직후, 그리고 규칙 변동 신호가 보일 때:
1. 인게임 정보를 읽는다: "목표 / 극대화하는 방법 / 추가 규칙 / 챌린지 탭 /
   보너스 탭" + 워크숍 스튜디오 문서.
2. score_model 을 채워 Memory에 저장한다 (전체 스키마: agent/memory-schema.md):
   {
     time_limit_sec: 300(5분),
     coin_value / treasure_value,
     challenge_score: {gain, loss},          # 정답 획득 / 오답 차감
     challenge_types: [math, web, knowledge, safety],  # 4종
     type_confidence: 유형별 정답 신뢰도,
     life_value: 남은 생명 1개당 점수,        # 생명=점수
     obstacle_rule: {life_cost, avoidable},  # 장애물 회피 가능
     blocked_rule: 막힘 강제통과 시 게임종료,
     token_bonus: 효율 보상 규칙,
     bonus_triggers: [조건→보상],
     answer_format, judge(LLM-as-judge),
     unknowns: [아직 모르는 항목]
   }
3. unknowns가 있으면 초반 탐색 행동으로 관측해 채우도록 Supervisor에 신호.

[B. Memory — world model 누적/제공]
키별 저장·조회: map_layout(벽/통로), collected(획득 좌표),
solved_challenges(유형→해법 캐시), enemy_positions, treasure_clues,
score_model, policy_params, run_stats(점수·실패유형).

[규칙]
- Supervisor의 모든 행동 전 관련 키를 제공, 행동 후 즉시 갱신.
- 같은 유형 챌린지 재출제 시 solved_challenges 해법 재사용(재계산 0).
- score_model 변경 시 Supervisor 정책이 자동 재계산되도록 최신값 보장.

[출력] 요청 키의 구조화된 값 또는 갱신 확인. 산문 설명 금지.
```

스키마 상세: [agent/memory-schema.md](../memory-schema.md).
