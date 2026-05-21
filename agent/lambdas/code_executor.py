"""AgentCore Lambda — code-executor (c2 Blue Brain 코드 챌린지)

LLM이 직접 못 푸는 계산을, Code_Specialist가 작성한 Python을 '실행'해 정확히 푼다.

[실격 방지] 이 도구는 외부 모델/LLM/API를 호출하지 않는다. 코드를 '실행'만 한다.
코드 작성은 Code_Specialist(서브에이전트 LLM)가 하고, 이 람다는 실행기 역할.

Tool 계약:
  event(body) = { "code": "<python source>" }
     - code는 결과를 print(...) 하거나 변수 result 에 담아야 함.
  return = { "result": "<stdout 또는 result 값>", "ok": true }
          오류 시 { "ok": false, "error": "..." }

예: 3000번째 피보나치 마지막 10자리
  code = "a,b=0,1\\nfor _ in range(3000): a,b=b,a+b\\nprint(str(a)[-10:])"
"""
import io
import json
import contextlib

# 실행 시 사용 가능한 표준 모듈(추가 종속성 설치 불가 → stdlib만)
import math, itertools, functools, collections, re, statistics, fractions, decimal, random


def lambda_handler(event, context=None):
    try:
        body = event.get("body", event) if isinstance(event, dict) else event
        if isinstance(body, str):
            body = json.loads(body)
        code = body.get("code", "")
        if not code:
            return _resp({"ok": False, "error": "no code provided"})

        safe_globals = {
            "__builtins__": __builtins__,
            "math": math, "itertools": itertools, "functools": functools,
            "collections": collections, "re": re, "statistics": statistics,
            "fractions": fractions, "decimal": decimal, "random": random,
        }
        ns = {}
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            exec(code, safe_globals, ns)

        printed = out.getvalue().strip()
        result = ns.get("result", None)
        value = printed if printed else ("" if result is None else str(result))
        return _resp({"ok": True, "result": value})
    except Exception as e:
        return _resp({"ok": False, "error": f"{type(e).__name__}: {e}"})


def _resp(obj):
    return {"statusCode": 200, "body": json.dumps(obj, ensure_ascii=False)}


if __name__ == "__main__":
    demo = {"code": "a,b=0,1\nfor _ in range(3000): a,b=b,a+b\nprint(str(a)[-10:])"}
    print(lambda_handler(demo))
