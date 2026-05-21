"""pathfinding-lambda — 보물=종착 전략 경로 (원본 입력 방어 + 강한 전략 병합)

원본(게임 제공)의 견고한 입력 처리(_parse_start, jagged row 보정, 다중 start 키,
범위 검증)를 유지하면서, 보물=게임종료에 맞는 전략을 추가:
  swift / get_coins / avoid_spikes / get_challenges / max_loot(★권장)

맵 셀: start normal wall treasure + c1..cN
  c7 코인(+250) · c8 스파이크(생명-) · 그 외 cN = 챌린지
  c40 빨간열쇠 → c30 빨간문(열쇠 없이 밟으면 ♥-5 → 열쇠 뒤에만 방문)

[실격 방지] 외부 모델/API 호출 없음. CELL_VALUE는 경로 우선순위용(정답 아님).
출력(원본과 동일): { "path": ["right",...], "steps": N, "start_position": [r,c] }
"""
import json
import re
import heapq
from collections import deque

INF = float("inf")
DIRECTIONS = [(-1, 0, "up"), (1, 0, "down"), (0, -1, "left"), (0, 1, "right")]

COINS = {"c7"}
SPIKES = {"c8"}
CELL_VALUE = {"c7": 250, "c1": 400, "c2": 600, "c3": 550, "c4": 800,
              "c5": 250, "c6": 1000, "c18": 500, "c30": 1000, "c40": 50}
DEFAULT_CHALLENGE_VALUE = 400
SPIKE_PENALTY = 50
KEY_CELL = "c40"
DOOR_CELL = "c30"


def _is_challenge(v):
    return isinstance(v, str) and len(v) > 1 and v[0] == "c" and v[1:].isdigit() \
        and v not in COINS and v not in SPIKES


def _cell_value(v):
    return CELL_VALUE.get(v, DEFAULT_CHALLENGE_VALUE if _is_challenge(v) else 0)


def _parse_start(pos):
    """다양한 포맷(리스트/문자열/'A1' 체스표기)에서 start 좌표를 파싱."""
    try:
        if isinstance(pos, (list, tuple)):
            if len(pos) == 1:
                return _parse_start(pos[0])
            if len(pos) >= 2:
                a = re.sub(r'[^A-Za-z0-9]', '', str(pos[0]))
                b = re.sub(r'[^A-Za-z0-9]', '', str(pos[1]))
                if a.isalpha():
                    return (int(b) - 1, ord(a.upper()) - ord('A'))
                return (int(a), int(b))
        s = re.sub(r'[^A-Za-z0-9]', '', str(pos))
        m = re.match(r'([A-Za-z])(\d+)', s)
        if m:
            return (int(m.group(2)) - 1, ord(m.group(1).upper()) - ord('A'))
        nums = re.findall(r'\d+', s)
        if len(nums) >= 2:
            return (int(nums[0]), int(nums[1]))
    except (ValueError, TypeError, IndexError):
        pass
    return (0, 0)


def _parse_strategy(s):
    """navigation prompt(예: 'use strategy max_loot')를 전략명으로."""
    s = str(s or "swift").lower()
    if "loot" in s or "max" in s:
        return "max_loot"
    if "challenge" in s:
        return "get_challenges"
    if "spike" in s or "avoid" in s:
        return "avoid_spikes"
    if "coin" in s:
        return "get_coins"
    if "swift" in s or "fast" in s or "quick" in s:
        return "swift"
    return "swift"


def lambda_handler(event, context=None):
    try:
        if isinstance(event, dict) and "body" in event:
            body = json.loads(event["body"]) if isinstance(event["body"], str) else event["body"]
        else:
            body = event

        print(f"DEBUG: Received event: {body}")
        game_map = body.get("game_map", [])

        # jagged row 보정 (모델이 칸을 누락하는 경우)
        if game_map:
            max_cols = max(len(row) for row in game_map)
            game_map = [row + ["normal"] * (max_cols - len(row)) for row in game_map]

        # start 위치 파싱 (다양한 키/포맷)
        map_config = body.get("map_config", {}) or {}
        player_start = map_config.get("playerStart") or body.get("playerStart") or {}
        if isinstance(player_start, str):
            start_pos = _parse_start(player_start)
        elif isinstance(player_start, dict) and player_start:
            start_pos = (player_start.get("row", 0), player_start.get("col", 0))
        else:
            raw = body.get("start_pos") or body.get("start") or body.get("position") or [0, 0]
            start_pos = _parse_start(raw)

        if not game_map:
            return _err(400, "Missing game_map")

        rows, cols = len(game_map), len(game_map[0])
        # 범위 검증
        if not (0 <= start_pos[0] < rows and 0 <= start_pos[1] < cols):
            start_pos = (0, 0)
        start_pos = (int(start_pos[0]), int(start_pos[1]))

        strategy = _parse_strategy(body.get("strategy", "swift"))

        treasure = _find(game_map, rows, cols, "treasure")
        if not treasure:
            return _err(400, "No treasure found on map")

        path = _plan(game_map, rows, cols, start_pos, treasure, strategy)
        result = {"path": path, "steps": len(path), "start_position": list(start_pos),
                  "strategy": strategy}
        print(f"RESULT: strategy={strategy} steps={len(path)} start={list(start_pos)}")
        return {"statusCode": 200, "body": json.dumps(result)}
    except Exception as e:
        print(f"ERROR: {e}")
        return _err(500, str(e))


def _err(code, msg):
    return {"statusCode": code, "body": json.dumps({"error": msg})}


def _find(game_map, rows, cols, kind):
    for r in range(rows):
        for c in range(cols):
            if game_map[r][c] == kind:
                return (r, c)
    return None


def _cells_where(game_map, rows, cols, pred):
    return [(r, c) for r in range(rows) for c in range(cols) if pred(game_map[r][c])]


# ----- 스파이크 가중 Dijkstra (이동 경로 복원) --------------------------
def _dijkstra(game_map, rows, cols, start, spike_penalty):
    dist = {start: 0}
    parent = {start: (None, None)}
    pq = [(0, start)]
    while pq:
        d, (r, c) = heapq.heappop(pq)
        if d > dist.get((r, c), INF):
            continue
        for dr, dc, mv in DIRECTIONS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and game_map[nr][nc] != "wall":
                step = 1 + (spike_penalty if game_map[nr][nc] in SPIKES else 0)
                if d + step < dist.get((nr, nc), INF):
                    dist[(nr, nc)] = d + step
                    parent[(nr, nc)] = ((r, c), mv)
                    heapq.heappush(pq, (d + step, (nr, nc)))
    return dist, parent


def _moves_to(parent, goal):
    moves, cur = [], goal
    while parent.get(cur, (None, None))[0] is not None:
        prev, mv = parent[cur]
        moves.append(mv)
        cur = prev
    moves.reverse()
    return moves


# ----- 전략 디스패치 ---------------------------------------------------
def _plan(game_map, rows, cols, start, treasure, strategy):
    is_coin = lambda v: v in COINS
    is_coin_or_chal = lambda v: v in COINS or _is_challenge(v)
    if strategy == "swift":
        return _route(game_map, rows, cols, [], start, treasure, 0)
    if strategy == "get_coins":
        return _ordered(game_map, rows, cols, start, treasure, is_coin, 0)
    if strategy == "avoid_spikes":
        return _ordered(game_map, rows, cols, start, treasure, is_coin, SPIKE_PENALTY)
    if strategy == "get_challenges":
        return _ordered(game_map, rows, cols, start, treasure, is_coin_or_chal, SPIKE_PENALTY)
    return _ordered(game_map, rows, cols, start, treasure, is_coin_or_chal, SPIKE_PENALTY)


def _ordered(game_map, rows, cols, start, treasure, pred, spike_penalty):
    """가치/거리 탐욕 순서로 타깃 방문 후 보물. 이동 경로(moves) 반환."""
    targets = set(_cells_where(game_map, rows, cols, pred))
    targets.discard(start)
    # 안전: 빨간 문(c30)은 빨간 열쇠(c40)가 맵에 있을 때만 방문(없으면 ♥-5).
    has_key = any(game_map[r][c] == KEY_CELL for (r, c) in targets)
    if not has_key:
        targets = {t for t in targets if game_map[t[0]][t[1]] != DOOR_CELL}
    order, cur, key_taken = [], start, False
    while targets:
        dist, _ = _dijkstra(game_map, rows, cols, cur, spike_penalty)
        best, best_ratio = None, -1.0
        for t in targets:
            v = game_map[t[0]][t[1]]
            if v == DOOR_CELL and not key_taken:   # 열쇠 먼저
                continue
            if t in dist and dist[t] > 0:
                ratio = _cell_value(v) / dist[t]
                if ratio > best_ratio:
                    best, best_ratio = t, ratio
        if best is None:
            break
        if game_map[best[0]][best[1]] == KEY_CELL:
            key_taken = True
        order.append(best)
        targets.discard(best)
        cur = best
    return _route(game_map, rows, cols, order, start, treasure, spike_penalty)


def _route(game_map, rows, cols, order, start, treasure, spike_penalty):
    """start → order[...] → treasure 를 잇는 이동 경로(moves)."""
    path, cur = [], start
    for cell in list(order) + [treasure]:
        dist, parent = _dijkstra(game_map, rows, cols, cur, spike_penalty)
        if cell == cur:
            continue
        if cell not in parent:
            continue   # 도달 불가 — 건너뜀
        path.extend(_moves_to(parent, cell))
        cur = cell
    return path


# ----- 로컬 자가검증 ---------------------------------------------------
if __name__ == "__main__":
    game_map = [
        ["start", "normal", "c5", "normal", "normal", "normal", "c5", "normal", "normal", "c1"],
        ["normal", "wall", "wall", "normal", "wall", "wall", "wall", "wall", "wall", "normal"],
        ["c8", "wall", "wall", "c5", "wall", "c7", "c7", "c7", "wall", "c3"],
        ["normal", "wall", "c8", "normal", "wall", "c8", "wall", "c8", "wall", "normal"],
        ["normal", "wall", "c7", "normal", "wall", "normal", "normal", "normal", "wall", "normal"],
        ["c5", "wall", "c7", "normal", "wall", "c5", "wall", "normal", "wall", "c5"],
        ["normal", "wall", "c7", "normal", "wall", "normal", "wall", "normal", "wall", "normal"],
        ["c1", "wall", "c8", "normal", "c2", "normal", "wall", "normal", "c4", "normal"],
        ["normal", "wall", "wall", "wall", "wall", "wall", "wall", "normal", "normal", "c7"],
        ["c7", "normal", "c3", "normal", "c4", "normal", "c2", "normal", "treasure", "normal"],
    ]
    # jagged + 'A1' 표기 + playerStart dict 등 입력 방어 테스트
    for body in [
        {"game_map": game_map, "start_pos": [0, 0], "strategy": "use strategy max_loot"},
        {"game_map": game_map, "playerStart": "A1", "strategy": "get coins"},
        {"game_map": game_map, "map_config": {"playerStart": {"row": 0, "col": 0}}, "strategy": "avoid spikes"},
    ]:
        out = json.loads(lambda_handler(body)["body"])
        print(f"{out['strategy']:14} start={out['start_position']} steps={out['steps']:3} path[:6]={out['path'][:6]}")
