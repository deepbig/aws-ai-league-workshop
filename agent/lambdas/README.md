# agent/lambdas/ — SageMaker 코드 에디터 붙여넣기용

워크샵 UI의 "도구 > AWS Lambda 함수" 슬롯에 등록할 Python 코드.
모두 **표준 라이브러리만** 사용해 zero-dependency.

| 파일 | UI 등록 이름(권장) | 용도 |
|---|---|---|
| [pathfinding.py](pathfinding.py) | `Pathfinding` | 예산제약 Orienteering 경로 산출(진짜 최적의 99.8~100%). Navigator 서브에이전트가 호출 |

> 워크샵에서 `Pathfinding` Lambda가 기본 제공될 수 있음(스크린샷 참조). 그 경우 코드를
> 본 파일 내용으로 **덮어쓰기** 권장 — 본 구현이 우리 시뮬레이션으로 검증된 결과.

## 배포 방법 (Lambda 슬롯에 등록)

1. UI의 "AWS Lambda 함수" 섹션에서 `+` → SageMaker 코드 에디터가 열림.
2. [`pathfinding.py`](pathfinding.py) 내용을 **그대로 붙여넣기**.
3. Handler: `lambda_handler` (파일 하단 함수).
4. 저장 → 워크샵 환경이 Lambda 등록 처리.

## Tool 계약 (재참조)

`event` JSON 형식은 [agent/tools.md](../tools.md)의 `navigate` 입력 스키마와 동일.
이 스키마를 사용하도록 Navigator 서브에이전트의 시스템 프롬프트
([../prompts/navigator.md](../prompts/navigator.md))가 작성되어 있음.

## 로컬 검증

```bash
python3 agent/lambdas/pathfinding.py
# → 데모 입력에 대해 route/expected_value/used_steps 반환 확인
```

`sim/planners.py`(검증된 동일 알고리즘)로 대규모 회귀 검증 가능:
```bash
python3 sim/bench.py          # 진짜 최적해(Held-Karp) 대비 %opt
python3 sim/robustness.py     # 규칙 레짐 6종 강건성
```

## 코드 풀이용(Code Specialist 서브에이전트)

`CodeExecution`은 AgentCore 내장 도구일 가능성이 큼(스크린샷 Combat Log의
"Using tool: CodeExecution"). 별도 Lambda 불필요할 수 있으나, 만약 커스텀이
필요하면 본 디렉토리에 `code_exec.py`를 추가하는 형태로 확장.
