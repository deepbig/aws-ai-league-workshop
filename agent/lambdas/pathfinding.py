"""AgentCore Lambda — pathfinding-lambda (실제 게임 인터페이스)

게임이 제공하는 기본 pathfinding-lambda를 확장한 버전. 기본 'swift'(보물 최단)는
점수가 낮다 → 보물 도달=게임 종료이므로 코인/챌린지를 최대한 모은 뒤 마지막에 보물로
가는 전략들을 추가한다.

입력 (게임 원본과 동일):
  event(body) = { "game_map": [[cell,...],...], "start_pos": [r,c], "strategy": "<name>" }
  cell 타입: "start" "normal" "wall" "treasure" 및 c1..c8
    c1 Violent Violet(가드레일/안정성) · c2 Blue Brain(코드) · c3 Memento(메모리)
    c4 Dark Prophet(웹 스크래핑) · c5 Bonehead(간단) · c6 Boss(전 스킬)
    c7 코인(250점) · c8 스파이크(밟으면 생명 감소)
출력 (게임 원본과 동일):
  { "path": ["right","up",...], "steps": N, "start_position": [r,c] }

전략(navigation prompt: "use strategy <name>"):
  swift        - 보물로 최단 (기본, 점수 낮음)
  get_coins    - c7 코인 수집 후 보물
  avoid_spikes - c8 스파이크를 강하게 회피하며 코인 수집 후 보물
  get_challenges - 코인 + 풀 수 있는 챌린지 방문 후 보물
  max_loot     - 가치/거리 기반으로 코인+챌린지 가치합 최대 순회 후 보물 (★권장)

[실격 방지] 본 코드는 외부 모델/API 호출이 없고, 챌린지 '정답'을 하드코딩하지 않는다.
아래 CELL_VALUE는 '경로 우선순위용 점수 추정치'일 뿐 정답이 아니다(수정 가능).
"""
import heapq
import json
from collections import deque

INF = float("inf")
DIRECTIONS = [(-1, 0, "up"), (1, 0, "down"), (0, -1, "left"), (0, 1, "right")]

COINS = {"c7"}
SPIKES = {"c8"}
CHALLENGES = {"c1", "c2", "c3", "c4", "c5", "c6"}

# 경로 우선순위용 가치 추정(정답 아님, 자유 수정). 당일 실제 보상으로 보정.
CELL_VALUE = {"c7": 250, "c2": 600, "c4": 500, "c5": 200, "c3": 400, "c1": 300, "c6": 1000}
SPIKE_PENALTY = 50  # 스파이크 회피 강도(경로 비용 가산)


def lambda_handler(event, context=None):
    try:
        if isinstance(event, dict) and "body" in event:
            body = json.loads(event["body"]) if isinstance(event["body"], str) else event["body"]
        else:
            body = event

        game_map = body.get("game_map", [])
        start_pos = tuple(body.get("start_pos", [0, 0]))
        strategy = _parse_strategy(body.get("strategy", "swift"))
        if not game_map:
            return _err(400, "Missing game_map")

        rows, cols = len(game_map), len(game_map[0])
        treasure = _find(game_map, rows, cols, "treasure")
        if not treasure:
            return _err(400, "No treasure found on map")

        path = _plan(game_map, rows, cols, start_pos, treasure, strategy)
        result = {"path": path, "steps": len(path), "start_position": list(start_pos),
                  "strategy": strategy}
        print(f"RESULT: strategy={strategy} steps={len(path)}")
        return {"statusCode": 200, "body": json.dumps(result)}
    except Exception as e:
        print(f"ERROR: {e}")
        return _err(500, str(e))


def _parse_strategy(s):
    s = (s or "swift").strip().lower().replace(" ", "_")
    s = s.replace("use_strategy_", "").replace("strategy_", "")
    return s if s in {"swift", "get_coins", "avoid_spikes", "get_challenges", "max_loot"} else "swift"


def _err(code, msg):
    return {"statusCode": code, "body": json.dumps({"error": msg})}


def _find(game_map, rows, cols, kind):
    for r in range(rows):
        for c in range(cols):
            if game_map[r][c] == kind:
                return (r, c)
    return None


def _cells_in(game_map, rows, cols, kinds):
    return [(r, c) for r in range(rows) for c in range(cols) if game_map[r][c] in kinds]


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
    if strategy == "swift":
        return _route(game_map, rows, cols, [], start, treasure, 0)
    if strategy == "get_coins":
        return _ordered(game_map, rows, cols, start, treasure, COINS, 0)
    if strategy == "avoid_spikes":
        return _ordered(game_map, rows, cols, start, treasure, COINS, SPIKE_PENALTY)
    if strategy == "get_challenges":
        return _ordered(game_map, rows, cols, start, treasure, COINS | CHALLENGES, SPIKE_PENALTY)
    # max_loot (권장)
    return _ordered(game_map, rows, cols, start, treasure, COINS | CHALLENGES, SPIKE_PENALTY)


def _ordered(game_map, rows, cols, start, treasure, target_kinds, spike_penalty):
    """가치/거리 탐욕 순서로 타깃 방문 후 보물. 이동 경로(moves) 반환."""
    targets = set(_cells_in(game_map, rows, cols, target_kinds))
    targets.discard(start)
    order, cur = [], start
    while targets:
        dist, _ = _dijkstra(game_map, rows, cols, cur, spike_penalty)
        best, best_ratio = None, -1.0
        for t in targets:
            if t in dist and dist[t] > 0:
                ratio = CELL_VALUE.get(game_map[t[0]][t[1]], 0) / dist[t]
                if ratio > best_ratio:
                    best, best_ratio = t, ratio
        if best is None:
            break
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
            continue  # 도달 불가 — 건너뜀
        path.extend(_moves_to(parent, cell))
        cur = cell
    return path


# ----- 로컬 자가검증 (가이드 예시 맵) ----------------------------------
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
    for strat in ("swift", "get_coins", "avoid_spikes", "max_loot"):
        out = json.loads(lambda_handler(
            {"game_map": game_map, "start_pos": [0, 0], "strategy": strat})["body"])
        print(f"{strat:14} steps={out['steps']:3}  path[:8]={out['path'][:8]}")
