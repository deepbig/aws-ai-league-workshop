"""AgentCore Lambda — web-scraper (c4 Dark Prophet 웹 스크래핑 챌린지)

특정 웹사이트에서 정보를 가져와 에이전트가 해석할 수 있게 텍스트로 반환한다.

[제약] 추가 종속성 설치 불가 → **표준 라이브러리만**(urllib, html.parser) 사용.
       requests/bs4 등 외부 패키지 금지.
[실격 방지] 외부 모델/LLM 호출 없음. 단순 HTTP fetch + HTML 텍스트 추출.

Tool 계약:
  event(body) = { "url": "https://...", "max_chars": 4000(선택) }
  return = { "ok": true, "url": "...", "text": "<태그 제거된 본문>", "title": "..." }
          오류 시 { "ok": false, "error": "..." }
"""
import json
import urllib.request
from html.parser import HTMLParser


class _Extract(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.title = ""
        self._skip = 0
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self._skip += 1
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript") and self._skip:
            self._skip -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._skip:
            return
        text = data.strip()
        if not text:
            return
        if self._in_title and not self.title:
            self.title = text
        self.parts.append(text)


def lambda_handler(event, context=None):
    try:
        body = event.get("body", event) if isinstance(event, dict) else event
        if isinstance(body, str):
            body = json.loads(body)
        url = body.get("url", "").strip()
        max_chars = int(body.get("max_chars", 4000))
        if not url:
            return _resp({"ok": False, "error": "no url provided"})

        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (AgentCore)"})
        with urllib.request.urlopen(req, timeout=10) as r:
            charset = r.headers.get_content_charset() or "utf-8"
            html = r.read().decode(charset, errors="replace")

        p = _Extract()
        p.feed(html)
        text = " ".join(p.parts)
        text = " ".join(text.split())[:max_chars]
        return _resp({"ok": True, "url": url, "title": p.title, "text": text})
    except Exception as e:
        return _resp({"ok": False, "error": f"{type(e).__name__}: {e}"})


def _resp(obj):
    return {"statusCode": 200, "body": json.dumps(obj, ensure_ascii=False)}


if __name__ == "__main__":
    print(lambda_handler({"url": "https://example.com"}))
