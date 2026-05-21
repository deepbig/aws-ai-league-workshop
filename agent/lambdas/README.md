# agent/lambdas/ — SageMaker 코드 에디터 붙여넣기용

워크샵 "도구 > AWS Lambda 함수" 슬롯에 등록할 Python 코드. **표준 라이브러리만** 사용.

> **실격 주의**: Lambda 도구 안에서 **외부 모델/LLM/API 호출 금지**, **정답 하드코딩 금지**.
> 본 코드는 순수 알고리즘이라 안전. 절대 외부 호출/하드코딩을 추가하지 말 것.

| 파일 | UI 이름(권장) | 용도 |
|---|---|---|
| [pathfinding.py](pathfinding.py) | `Pathfinding` | 보물=종착 Orienteering 경로(전략 swift/get_coins/**max_loot**) |

## pathfinding.py — 무엇을 개선했나

기본 제공 Pathfinding은 `swift`(보물 직행)·`get_coins`만 지원. 그러나 **보물 도달 =
게임 종료**라 swift는 코인을 거의 못 모은다. 그래서 **`max_loot` 전략**을 추가:
시간 예산 내 코인 가치 합을 최대화하고 **마지막에 보물로 종료**(검증된 Orienteering,
docs/08). 자가검증 예: swift=300 < get_coins=480 < **max_loot=1080**.

### Tool 계약 (mapId 기반)

```json
event = {
  "start": [r,c],
  "grid":  [[0,1,...], ...],            // 0=통로 1=벽/막힘
  "items": [
    {"id":"c1","cell":[r,c],"kind":"coin|challenge|treasure|obstacle",
     "value":<코인>,"solve_cost":<스텝>}
  ],
  "time_budget": <int>,
  "strategy": "max_loot | get_coins | swift",
  "obstacle_penalty": 4
}
return { "route": ["c3","c1",...,"<treasure id>"], "expected_value": <int>,
         "used_steps": <int>, "strategy": "max_loot" }
```

- **route는 mapId(c1..cN) 순서**, 항상 보물 id로 끝남(보물=종착).
- 막힘/벽 = grid 1 → 미경유. 장애물(spikes) = `obstacle_penalty` 가산으로 우회.
- **Navigation prompt**(Submit & Play 직전): `use strategy max_loot`.

## 배포

1. UI "AWS Lambda 함수" `+` → SageMaker 에디터에 [pathfinding.py](pathfinding.py) 붙여넣기.
2. Handler: `lambda_handler`. 저장 → Pathfinding 서브에이전트에 연결.

## 코드 실행 Lambda (Code 챌린지용)

c2 같은 코드 챌린지는 **Amazon Bedrock Code Interpreter 기반 Lambda**가 필요
("build a lambda tool that can handle writing and executing code"). 이 도구는
Bedrock Code Interpreter API로 코드를 실행하고 결과를 반환하도록 구성한다
(외부 LLM 호출 아님 — 실격 아님). Code_Specialist 서브에이전트에 연결.

## 로컬 검증

```bash
python3 agent/lambdas/pathfinding.py    # swift/get_coins/max_loot 비교 출력
python3 sim/bench.py                     # 진짜 최적해(Held-Karp) 대비 %opt
python3 sim/robustness.py                # 규칙 레짐 6종 강건성
```
