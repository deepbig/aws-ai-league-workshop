"""AgentCore Lambda — Pathfinding (예산제약 Orienteering 솔버)

SageMaker 코드 에디터에 그대로 붙여넣어 Lambda 함수로 배포.
sim/planners.py의 검증된 알고리즘(진짜 최적의 99.8~100%, docs/08)을
무의존성 표준라이브러리만으로 자급 구현. AgentCore가 Tool로 호출.

Tool 계약 (agent/tools.md `navigate`):
  event = {
    "start": [r, c],
    "grid":  [[0,1,...], ...],         # 0=통로 1=벽
    "rewards": [
      {"cell":[r,c], "kind":"coin|challenge|treasure",
       "value": <int>, "solve_cost": <int>}
    ],
    "time_budget": <int>,
    "mode": "fast" | "precise"          # fast=greedy+LS, precise=ILS
  }

  return {
    "route": [[r,c], ...],              # 시작점 제외, 방문할 보상 셀의 순서
    "expected_value": <int>,
    "used_steps": <int>
  }
"""
from __future__ import annotations

import json
import math
import random
from collections import deque

INF = float("inf")


# ----- BFS 거리행렬 -----------------------------------------------------
def _bfs(grid, src):
    H, W = len(grid), len(grid[0])
    dist = {tuple(src): 0}
    q = deque([tuple(src)])
    while q:
        r, c = q.popleft()
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < H and 0 <= nc < W and grid[nr][nc] == 0 \
                    and (nr, nc) not in dist:
                dist[(nr, nc)] = dist[(r, c)] + 1
                q.append((nr, nc))
    return dist


def _distance_matrix(grid, start, rewards):
    """0=start, 1..N=rewards. {i: {j: steps}}."""
    anchors = [tuple(start)] + [tuple(r["cell"]) for r in rewards]
    dm = {}
    for i, cell in enumerate(anchors):
        d = _bfs(grid, cell)
        dm[i] = {j: d[anchors[j]] for j in range(len(anchors)) if anchors[j] in d}
    return dm, anchors


# ----- 비용/가치 유틸 ---------------------------------------------------
def _route_cost(route, dm, rewards):
    cur, used = 0, 0
    for nid in route:
        if nid not in dm.get(cur, {}):
            return INF
        used += dm[cur][nid] + rewards[nid - 1]["solve_cost"]
        cur = nid
    return used


def _route_value(route, rewards):
    return sum(rewards[n - 1]["value"] for n in route)


def _feasible_prefix(route, dm, rewards, budget):
    cur, used, out = 0, 0, []
    for nid in route:
        if nid not in dm.get(cur, {}):
            break
        step = dm[cur][nid] + rewards[nid - 1]["solve_cost"]
        if used + step > budget:
            break
        used += step
        out.append(nid)
        cur = nid
    return out


# ----- 탐욕(가치/비용비) -----------------------------------------------
def _greedy_ratio(dm, rewards, budget):
    cur, used, route = 0, 0, []
    rem = set(range(1, len(rewards) + 1))
    while True:
        best, best_ratio, best_step = None, -1.0, 0
        for nid in rem:
            d = dm.get(cur, {}).get(nid, INF)
            if d is INF:
                continue
            step = d + rewards[nid - 1]["solve_cost"]
            if used + step > budget:
                continue
            ratio = rewards[nid - 1]["value"] / max(step, 1)
            if ratio > best_ratio:
                best, best_ratio, best_step = nid, ratio, step
        if best is None:
            break
        used += best_step
        route.append(best)
        rem.discard(best)
        cur = best
    return route


# ----- 지역탐색: 2-opt + or-opt + 삽입 ---------------------------------
def _two_opt(route, dm, rewards, budget):
    improved = True
    while improved:
        improved = False
        base = _route_cost(route, dm, rewards)
        for i in range(len(route) - 1):
            for j in range(i + 1, len(route)):
                cand = route[:i] + route[i:j + 1][::-1] + route[j + 1:]
                if _route_cost(cand, dm, rewards) < base - 1e-9:
                    route, base, improved = cand, _route_cost(cand, dm, rewards), True
    return route


def _or_opt(route, dm, rewards, budget):
    improved = True
    while improved:
        improved = False
        base = _route_cost(route, dm, rewards)
        for seg in (1, 2, 3):
            for i in range(len(route) - seg + 1):
                chunk = route[i:i + seg]
                rest = route[:i] + route[i + seg:]
                for pos in range(len(rest) + 1):
                    if pos == i:
                        continue
                    cand = rest[:pos] + chunk + rest[pos:]
                    nc = _route_cost(cand, dm, rewards)
                    if nc < base - 1e-9:
                        route, base, improved = cand, nc, True
                        break
                if improved:
                    break
            if improved:
                break
    return route


def _insert_extra(route, dm, rewards, budget):
    in_route = set(route)
    changed = True
    while changed:
        changed = False
        base = _route_cost(route, dm, rewards)
        best_gain, best = -1.0, None
        for nid in range(1, len(rewards) + 1):
            if nid in in_route:
                continue
            for pos in range(len(route) + 1):
                cand = route[:pos] + [nid] + route[pos:]
                c = _route_cost(cand, dm, rewards)
                if c <= budget:
                    extra = c - base
                    gain = rewards[nid - 1]["value"] / max(extra, 1)
                    if gain > best_gain:
                        best_gain, best = gain, (cand, nid)
        if best:
            route, nid = best
            in_route.add(nid)
            changed = True
    return route


def _local_search(route, dm, rewards, budget):
    prev = -1
    while True:
        route = _two_opt(route, dm, rewards, budget)
        route = _or_opt(route, dm, rewards, budget)
        route = _insert_extra(route, dm, rewards, budget)
        v = _route_value(_feasible_prefix(route, dm, rewards, budget), rewards)
        if v <= prev:
            break
        prev = v
    return _feasible_prefix(route, dm, rewards, budget)


def _greedy_ls(dm, rewards, budget):
    return _local_search(_greedy_ratio(dm, rewards, budget), dm, rewards, budget)


# ----- ILS (precise 모드) ----------------------------------------------
def _ils(dm, rewards, budget, iters=50, seed=0):
    rng = random.Random(seed)
    cur = _greedy_ls(dm, rewards, budget)
    best, best_v = cur[:], _route_value(cur, rewards)
    for _ in range(iters):
        r = cur[:]
        if len(r) >= 4 and rng.random() < 0.5:
            a, b, c = sorted(rng.sample(range(1, len(r)), 3))
            r = r[:a] + r[b:c] + r[a:b] + r[c:]
        else:
            for _ in range(rng.randint(1, max(1, len(r) // 3))):
                if r:
                    r.pop(rng.randrange(len(r)))
        r = _local_search(r, dm, rewards, budget)
        v = _route_value(r, rewards)
        if v >= best_v:
            best, best_v, cur = r[:], v, r
    return best


# ----- Lambda handler --------------------------------------------------
def lambda_handler(event, context=None):
    start = event["start"]
    grid = event["grid"]
    rewards = event.get("rewards", [])
    budget = int(event.get("time_budget", 0))
    mode = event.get("mode", "fast")

    if not rewards or budget <= 0:
        return {"route": [], "expected_value": 0, "used_steps": 0}

    dm, anchors = _distance_matrix(grid, start, rewards)

    if mode == "precise":
        route_ids = _ils(dm, rewards, budget, iters=60)
    else:
        route_ids = _greedy_ls(dm, rewards, budget)

    route_ids = _feasible_prefix(route_ids, dm, rewards, budget)
    return {
        "route": [list(anchors[i]) for i in route_ids],
        "expected_value": _route_value(route_ids, rewards),
        "used_steps": _route_cost(route_ids, dm, rewards) if route_ids else 0,
    }


# ----- 로컬 자가검증 (Lambda 외부에서 python pathfinding.py로 실행) -----
if __name__ == "__main__":
    demo = {
        "start": [0, 0],
        "grid": [[0] * 6 for _ in range(6)],
        "rewards": [
            {"cell": [1, 3], "kind": "coin",      "value": 100, "solve_cost": 0},
            {"cell": [4, 1], "kind": "coin",      "value": 80,  "solve_cost": 0},
            {"cell": [5, 5], "kind": "treasure",  "value": 500, "solve_cost": 0},
            {"cell": [3, 4], "kind": "challenge", "value": 300, "solve_cost": 2},
        ],
        "time_budget": 20,
        "mode": "precise",
    }
    print(json.dumps(lambda_handler(demo), ensure_ascii=False, indent=2))
