# sim — 정책 강건성 검증 + Tool 알고리즘 벤치

무의존성(stdlib only). 실점수 예측기가 아니라 **권장 에이전트 정책이 미지의 당일
규칙에도 강건한지** 검증하고, Navigator Tool에 넣을 알고리즘을 고르는 도구.
에이전트 설계 본문: [docs/09-agent-design.md](../docs/09-agent-design.md).

## 실행

```bash
python3 sim/robustness.py   # ★ 규칙 변동 강건성: 정책 vs 진짜 최적 (레짐별)
python3 sim/run.py          # 빠른 요약 (라우팅 레버 / 코드풀이 레버)
python3 sim/bench.py        # Navigator Tool 알고리즘 벤치 (SMALL/MID/FULL %opt)
```

## 파일

- `config.json` — 모든 [당일]-미정 값(=score_model 미러). **여기만 바꾸면 전 검증 재실행.**
- `game.py` — 그리드 미로 환경(보상노드/거리행렬/점수평가, 시작점 연결성 보장)
- `planners.py` — 경로 솔버 7종 + **Held-Karp 진짜 최적해**(`plan_exact`)
- `robustness.py` — 6개 규칙 레짐 × (naive / 권장정책 / 진짜최적) 비교
- `bench.py` — 3단계 최적성 벤치 / `run.py` — 레버 요약 / `agent.py` — 에피소드 실행기

## 핵심 결과

- **강건성**: 6개 규칙 레짐(챌린지중심·페널티중심·코인차등·시간촉박 등) 전부에서
  권장 정책(강한 navigate + 도구 챌린지풀이 + 생명 보존) = **진짜 최적의 100%**,
  naive 9~21%(페널티중심은 음수). 생명=점수·오답 차감 반영 시 격차 더 큼.
  → 프롬프트/구조 불변, `config.json`(score_model) 값만 교체로 변수 상황 적응.
- **Tool 근거**: 경로는 LLM 추정 대신 검증 알고리즘(`greedy+LS` ~99.8%·15ms /
  `plan_ils` 99.9%+)을 navigate Lambda로 → [docs/08](../docs/08-routing-findings.md).

## 당일 사용법

1. 인게임 규칙/탭 + 워크숍 스튜디오 문서 → [agent/memory-schema.md](../agent/memory-schema.md) `score_model`.
2. 같은 값을 `config.json`에 입력 → `python3 sim/robustness.py` / `bench.py`로 사전 확인.
3. 권장 정책/프롬프트를 AgentCore에 이식 ([agent/](../agent/)), 반복 개선 루프 가동.
