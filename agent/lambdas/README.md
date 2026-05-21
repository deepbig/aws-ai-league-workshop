# agent/lambdas/ — SageMaker 코드 에디터 붙여넣기용

워크샵 Lambda(`pathfinding-lambda`). **표준 라이브러리만** 사용.

> **편집 주의**: 연필 아이콘은 에디터만 열 뿐 해당 lambda로 딥링크하지 않음.
> AWS 플러그인에서 `pathfinding-lambda`의 `lambda_function.py`를 직접 찾아 편집할 것.
> **실격 주의**: 도구 안에서 외부 모델/API 호출 금지, 정답 하드코딩 금지.

| 파일 | UI 이름 | 용도 |
|---|---|---|
| [pathfinding.py](pathfinding.py) | `pathfinding-lambda` | 보물=종착 전략 경로(swift/get_coins/avoid_spikes/get_challenges/**max_loot**) |
| [code_executor.py](code_executor.py) | `code-executor` | c2 Blue Brain — Python 코드 **실행**(계산). Code_Specialist 연결 |
| [web_scraper.py](web_scraper.py) | `web-scraper` | c4 Dark Prophet — URL 스크래핑(stdlib만). Web_Researcher 연결 |

> 나머지 챌린지는 Lambda 불필요: c1=Guardrails, c3/c30/c40=Memory+추론, c5/c18=프롬프트.
> (c18·c30은 LLM 추론이라 람다 안에서 LLM 쓰면 실격 → 프롬프트/에이전트가 직접 처리.)

## code-executor 계약 (c2)

```json
event(body) = { "code": "<python source: print()로 결과 출력 또는 result 변수>" }
return       = { "ok": true, "result": "<stdout 또는 result>" }
```
- Code_Specialist(LLM)가 코드를 작성 → 이 람다가 **실행만** 한다(외부 모델 호출 없음 = 실격 아님).
- 자가검증: 3000번째 피보나치 마지막 10자리 → `6709796000`.

## web-scraper 계약 (c4)

```json
event(body) = { "url": "https://...", "max_chars": 4000 }
return       = { "ok": true, "url": "...", "title": "...", "text": "<태그 제거 본문>" }
```
- `urllib.request` + `html.parser`만 사용(**추가 종속성 설치 불가** 준수).
- Web_Researcher가 질문에서 URL을 추출해 호출 → 반환 텍스트에서 답을 해석.

## 실제 인터페이스 (게임 원본과 동일)

```
event(body) = { "game_map": [["start","normal","c7",...], ...],
                "start_pos": [r,c], "strategy": "max_loot" }
return        = { "path": ["right","up",...], "steps": N, "start_position": [r,c] }
```

- `game_map` 셀 타입: `start` `normal` `wall` `treasure` + **c1~c8**
  - c1 Violent Violet(가드레일) · c2 Blue Brain(코드) · c3 Memento(메모리)
  - c4 Dark Prophet(웹) · c5 Bonehead(간단) · c6 Boss(전 스킬)
  - c7 코인(+250) · c8 스파이크(생명 -)
- 출력 `path`는 **이동 배열**(up/down/left/right). 항상 보물에서 끝남.

## 무엇을 개선했나

기본 제공은 `swift`(보물 최단)·`get_coins`만 지원. 보물 도달=게임 종료라 swift는
코인을 거의 못 모은다. 그래서 전략을 추가:
- `avoid_spikes` : c8을 강하게 회피(생명 보존=점수)
- `get_challenges` : 코인 + 챌린지 셀(c1~c6) 순회 후 보물
- `max_loot` (★권장) : 가치/거리 탐욕으로 코인+챌린지 최대 순회 후 보물

자가검증(가이드 예시 맵, 모두 유효·보물 종착): swift 17 / get_coins 47 /
avoid_spikes 61(스파이크 hit 최소) / max_loot 89(코인 8개 전부 + 챌린지 최다).

> `CELL_VALUE`(경로 우선순위용 점수 추정)는 자유 수정 — 정답이 아니라 라우팅 가중치.
> 당일 실제 챌린지 보상으로 보정.

## 전략 활성화

Navigation prompt: `use strategy max_loot` (또는 get_coins / avoid_spikes / get_challenges).
파이널(finale)에서는 레벨별로 즉석 전략이 필요할 수 있음 → 전략을 추가로 정의해 대비.

## 배포

1. AWS 플러그인에서 `pathfinding-lambda` → `lambda_function.py` 열기.
2. [pathfinding.py](pathfinding.py) 내용으로 교체. Handler: `lambda_handler`. 저장.

## 원본 복구

기본 코드로 되돌리려면 게임 가이드의 "Original Code"를 사용(swift/get_coins만 지원).

## 코드 실행 Lambda (c2 Blue Brain용)

Amazon Bedrock Code Interpreter로 코드를 실행하는 Lambda를 별도 구성해
Code_Specialist에 연결(외부 LLM 호출 아님 — 실격 아님).

## 로컬 검증

```bash
python3 agent/lambdas/pathfinding.py    # 전략별 steps/path 출력
```
