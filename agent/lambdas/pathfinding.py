"""AgentCore Lambda — Pathfinding (보물=종착 Orienteering, mapId 기반, 전략 지원)

핵심 게임 규칙 반영:
- 보물(treasure) 도달 시 게임 종료 → 보물은 경로의 '종착 노드'. 코인을 최대한
  모은 뒤 마지막에 보물로 가는 경로를 만든다. (default 'swift'는 최단 보물행이라
  코인을 거의 못 모음 → 개선 전략 'max_loot'가 핵심)
- 맵 아이템은 mapId(c1-cN)로 식별. items[].id 사용, route도 mapId로 반환.
- 장애물(spikes 등)은 통과 시 생명 -1, 회피 가능 → 통과 비용 가산으로 우회.
- 막힘/벽은 grid=1 → 절대 경유 안 함(강제 통과 시 게임 종료).

전략(navigation prompt: "use strategy <name>"):
- swift     : 코인 무시, 보물로 최단 (게임 빨리 종료 — 비권장)
- get_coins : 도달 가능한 모든 코인 수집 후 보물
- max_loot  : 시간 예산 내 코인 가치 합 최대화 후 보물 (★권장, Orienteering)

[중요/실격 방지] 본 Lambda는 외부 모델(LLM/API)을 호출하지 않는 순수 알고리즘이다.
정답 하드코딩·외부 모델 사용은 실격 사유 → 절대 추가하지 말 것.

Tool 계약:
  event = {
    "start": [r,c] | "start",
    "grid":  [[0,1,...], ...],            # 0=통로, 1=벽/막힘
    "items": [
      {"id":"c1","cell":[r,c],"kind":"coin|challenge|treasure|obstacle",
       "value":<코인 가치, 코인/챌린지>, "solve_cost":<도착 후 스텝, 챌린지>}
    ],
    "time_budget": <int>,
    "strategy": "max_loot" | "get_coins" | "swift",
    "obstacle_penalty": <int, 기본 4>
  }
  return { "route": ["c3","c1",...,"<treasure id>"], "expected_value": <int>, "used_steps": <int> }
"""
from __future__ import annotations

import heapq
import json
import random

INF = float("inf")


# ----- Dijkstra: 막힘=통과불가, 장애물=비용 가산(우회) -------------------
def _dijkstra(grid, src, obstacles, penalty):
    H, W = len(grid), len(grid[0])
    src = tuple(src)
    dist = {src: 0}
    pq = [(0, src)]
    while pq:
        d, (r, c) = heapq.heappop(pq)
        if d > dist.get((r, c), INF):
            continue
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < H and 0 <= nc < W and grid[nr][nc] == 0:
                step = 1 + (penalty if (nr, nc) in obstacles else 0)
                if d + step < dist.get((nr, nc), INF):
                    dist[(nr, nc)] = d + step
                    heapq.heappush(pq, (d + step, (nr, nc)))
    return dist


# ----- 비용/가치 (보물 종착 항 포함) ------------------------------------
def _cost(route, dm, solve, terminal):
    """start(0) → route → terminal(보물). 도달 불가 시 INF."""
    cur, used = 0, 0
    for nid in route:
        if nid not in dm.get(cur, {}):
            return INF
        used += dm[cur][nid] + solve[nid]
        cur = nid
    if terminal is not None:
        if terminal not in dm.get(cur, {}):
            return INF
        used += dm[cur][terminal]
    return used


def _value(route, val):
    return sum(val[n] for n in route)


def _prefix(route, dm, solve, val, terminal, budget):
    """예산 안에 '보물까지 포함'해 방문 가능한 prefix."""
    out = []
    for k in range(len(route), -1, -1):
        if _cost(route[:k], dm, solve, terminal) <= budget:
            out = route[:k]
            break
    return out


# ----- Orienteering 솔버 (보물 종착) -----------------------------------
def _greedy(ids, dm, solve, val, terminal, budget):
    cur, used, route = 0, 0, []
    rem = set(ids)
    while True:
        best, best_ratio, best_step = None, -1.0, 0
        for nid in rem:
            if nid not in dm.get(cur, {}):
                continue
            step = dm[cur][nid] + solve[nid]
            # 이 노드 추가 후에도 보물까지 갈 수 있어야 함
            if terminal is not None and terminal not in dm.get(nid, {}):
                continue
            tail = dm[nid][terminal] if terminal is not None else 0
            if used + step + tail > budget:
                continue
            ratio = val[nid] / max(step, 1)
            if ratio > best_ratio:
                best, best_ratio, best_step = nid, ratio, step
        if best is None:
            break
        used += best_step
        route.append(best)
        rem.discard(best)
        cur = best
    return route


def _two_opt(route, dm, solve, val, terminal, budget):
    improved = True
    while improved:
        improved = False
        base = _cost(route, dm, solve, terminal)
        for i in range(len(route) - 1):
            for j in range(i + 1, len(route)):
                cand = route[:i] + route[i:j + 1][::-1] + route[j + 1:]
                c = _cost(cand, dm, solve, terminal)
                if c < base - 1e-9 and c <= budget:
                    route, base, improved = cand, c, True
    return route


def _insert(route, ids, dm, solve, val, terminal, budget):
    inr = set(route)
    changed = True
    while changed:
        changed = False
        base = _cost(route, dm, solve, terminal)
        best_gain, best = -1.0, None
        for nid in ids:
            if nid in inr:
                continue
            for pos in range(len(route) + 1):
                cand = route[:pos] + [nid] + route[pos:]
                c = _cost(cand, dm, solve, terminal)
                if c <= budget:
                    gain = val[nid] / max(c - base, 1)
                    if gain > best_gain:
                        best_gain, best = gain, (cand, nid)
        if best:
            route, nid = best
            inr.add(nid)
            changed = True
    return route


def _local(route, ids, dm, solve, val, terminal, budget):
    prev = -1
    while True:
        route = _two_opt(route, dm, solve, val, terminal, budget)
        route = _insert(route, ids, dm, solve, val, terminal, budget)
        v = _value(_prefix(route, dm, solve, val, terminal, budget), val)
        if v <= prev:
            break
        prev = v
    return _prefix(route, dm, solve, val, terminal, budget)


def _ils(ids, dm, solve, val, terminal, budget, iters=60, seed=0):
    rng = random.Random(seed)
    cur = _local(_greedy(ids, dm, solve, val, terminal, budget),
                 ids, dm, solve, val, terminal, budget)
    best, best_v = cur[:], _value(cur, val)
    for _ in range(iters):
        r = cur[:]
        if len(r) >= 4 and rng.random() < 0.5:
            a, b, c = sorted(rng.sample(range(1, len(r)), 3))
            r = r[:a] + r[b:c] + r[a:b] + r[c:]
        else:
            for _ in range(rng.randint(1, max(1, len(r) // 3))):
                if r:
                    r.pop(rng.randrange(len(r)))
        r = _local(r, ids, dm, solve, val, terminal, budget)
        v = _value(r, val)
        if v >= best_v:
            best, best_v, cur = r[:], v, r
    return best


# ----- Lambda handler --------------------------------------------------
def lambda_handler(event, context=None):
    grid = event["grid"]
    items = event.get("items", [])
    budget = int(event.get("time_budget", 0))
    strategy = event.get("strategy", "max_loot")
    penalty = int(event.get("obstacle_penalty", 4))

    # mapId <-> 내부 인덱스
    treasure_item = next((it for it in items if it["kind"] == "treasure"), None)
    obstacle_cells = set(tuple(it["cell"]) for it in items if it["kind"] == "obstacle")
    reward_items = [it for it in items if it["kind"] in ("coin", "challenge")]

    start = event.get("start", "start")
    start_cell = start if isinstance(start, (list, tuple)) else \
        next((it["cell"] for it in items if it.get("id") == start), [0, 0])

    anchors = [tuple(start_cell)]                    # 0 = start
    idx_of_id, id_of_idx = {}, {}
    for it in reward_items:
        idx = len(anchors)
        anchors.append(tuple(it["cell"]))
        idx_of_id[it["id"]] = idx
        id_of_idx[idx] = it["id"]
    terminal = None
    if treasure_item is not None:
        terminal = len(anchors)
        anchors.append(tuple(treasure_item["cell"]))
        id_of_idx[terminal] = treasure_item["id"]

    # 거리행렬 (장애물 회피 가중)
    dm = {}
    for i, cell in enumerate(anchors):
        d = _dijkstra(grid, cell, obstacle_cells, penalty)
        dm[i] = {j: d[anchors[j]] for j in range(len(anchors)) if anchors[j] in d}

    val = {0: 0}
    solve = {0: 0}
    for it in reward_items:
        idx = idx_of_id[it["id"]]
        val[idx] = it.get("value", 0)
        solve[idx] = it.get("solve_cost", 0)
    if terminal is not None:
        val[terminal] = treasure_item.get("value", 0)
        solve[terminal] = treasure_item.get("solve_cost", 0)

    ids = list(idx_of_id.values())

    # 전략
    if strategy == "swift":
        route = []                                   # 코인 무시, 보물로 직행
    elif strategy == "get_coins":
        coin_ids = [idx_of_id[it["id"]] for it in reward_items if it["kind"] == "coin"]
        route = _local(coin_ids[:], coin_ids, dm, solve, val, terminal, budget)
    else:                                            # max_loot (권장)
        route = _ils(ids, dm, solve, val, terminal, budget, iters=60)

    route = _prefix(route, dm, solve, val, terminal, budget)

    # 보물(종착) 부착
    route_idx = route + ([terminal] if terminal is not None else [])
    return {
        "route": [id_of_idx[i] for i in route_idx],
        "expected_value": _value(route, val) + (val.get(terminal, 0) if terminal is not None else 0),
        "used_steps": _cost(route, dm, solve, terminal) if (route or terminal is not None) else 0,
        "strategy": strategy,
    }


# ----- 로컬 자가검증 ---------------------------------------------------
if __name__ == "__main__":
    demo = {
        "start": [0, 0],
        "grid": [[0] * 6 for _ in range(6)],
        "items": [
            {"id": "c1", "cell": [1, 3], "kind": "coin",      "value": 100, "solve_cost": 0},
            {"id": "c2", "cell": [3, 4], "kind": "challenge", "value": 600, "solve_cost": 2},
            {"id": "c3", "cell": [4, 1], "kind": "coin",      "value": 80,  "solve_cost": 0},
            {"id": "c4", "cell": [2, 3], "kind": "obstacle",  "value": 0,   "solve_cost": 0},
            {"id": "c5", "cell": [5, 5], "kind": "treasure",  "value": 300, "solve_cost": 0},
        ],
        "time_budget": 24,
    }
    for strat in ("swift", "get_coins", "max_loot"):
        print(strat, json.dumps(lambda_handler(dict(demo, strategy=strat), None),
                                ensure_ascii=False))
