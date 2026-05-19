"""Orienteering(예산제약 prize-collecting) 경로 플래너들.

공통 시그니처:  plan(dist, nodes, budget) -> list[int]   (1-based 노드 idx 순서)
  dist   : {i: {j: steps}}  (0 = start, 1..N = nodes)
  nodes  : list[Node]       (game.Node; value, solve_cost)
  budget : int              (총 가용 스텝)

비용 모델: cur->nid 이동 = dist[cur][nid] + nodes[nid-1].solve_cost
점수 모델: 방문 노드 value 합. 예산 초과 직전까지만 인정.
"""
from __future__ import annotations

import math
import random

INF = float("inf")


def route_cost(route, dist, nodes):
    cur, used = 0, 0
    for nid in route:
        if nid not in dist.get(cur, {}):
            return INF
        used += dist[cur][nid] + nodes[nid - 1].solve_cost
        cur = nid
    return used


def route_value(route, nodes):
    return sum(nodes[n - 1].value for n in route)


def feasible_prefix(route, dist, nodes, budget):
    """예산 안에 실제로 방문 가능한 prefix만 반환."""
    cur, used, out = 0, 0, []
    for nid in route:
        if nid not in dist.get(cur, {}):
            break
        step = dist[cur][nid] + nodes[nid - 1].solve_cost
        if used + step > budget:
            break
        used += step
        out.append(nid)
        cur = nid
    return out


# --- P0: 최근접 -------------------------------------------------------
def plan_nearest(dist, nodes, budget):
    cur, used, route = 0, 0, []
    remaining = set(range(1, len(nodes) + 1))
    while remaining:
        best, best_d = None, INF
        for nid in remaining:
            d = dist.get(cur, {}).get(nid, INF)
            if d < best_d:
                best, best_d = nid, d
        if best is None:
            break
        step = best_d + nodes[best - 1].solve_cost
        if used + step > budget:
            remaining.discard(best)
            continue
        used += step
        route.append(best)
        remaining.discard(best)
        cur = best
    return route


# --- P1: 탐욕 가치/비용비 --------------------------------------------
def plan_greedy_ratio(dist, nodes, budget):
    cur, used, route = 0, 0, []
    remaining = set(range(1, len(nodes) + 1))
    while True:
        best, best_ratio, best_step = None, -1.0, 0
        for nid in remaining:
            d = dist.get(cur, {}).get(nid, INF)
            if d is INF:
                continue
            step = d + nodes[nid - 1].solve_cost
            if used + step > budget:
                continue
            ratio = nodes[nid - 1].value / max(step, 1)
            if ratio > best_ratio:
                best, best_ratio, best_step = nid, ratio, step
        if best is None:
            break
        used += best_step
        route.append(best)
        remaining.discard(best)
        cur = best
    return route


# --- 지역 탐색: 2-opt + or-opt + 미방문 삽입 --------------------------
def _two_opt(route, dist, nodes, budget):
    improved = True
    while improved:
        improved = False
        for i in range(len(route) - 1):
            for j in range(i + 1, len(route)):
                cand = route[:i] + route[i:j + 1][::-1] + route[j + 1:]
                if route_cost(cand, dist, nodes) < route_cost(route, dist, nodes) - 1e-9:
                    route = cand
                    improved = True
    return route


def _insert_extra(route, dist, nodes, budget):
    """남은 예산으로 미방문 노드를 최선 위치에 삽입 (가치/추가비용 우선)."""
    in_route = set(route)
    cands = [n for n in range(1, len(nodes) + 1) if n not in in_route]
    changed = True
    while changed:
        changed = False
        base_cost = route_cost(route, dist, nodes)
        best_gain, best_new = -1.0, None
        for nid in cands:
            if nid in in_route:
                continue
            for pos in range(len(route) + 1):
                cand = route[:pos] + [nid] + route[pos:]
                c = route_cost(cand, dist, nodes)
                if c <= budget:
                    extra = c - base_cost
                    gain = nodes[nid - 1].value / max(extra, 1)
                    if gain > best_gain:
                        best_gain, best_new = gain, (cand, nid)
        if best_new:
            route, nid = best_new
            in_route.add(nid)
            changed = True
    return route


def _or_opt(route, dist, nodes, budget):
    """길이 1~3 구간을 더 싼 위치로 재배치 (비용 절감)."""
    improved = True
    while improved:
        improved = False
        base = route_cost(route, dist, nodes)
        for seg in (1, 2, 3):
            for i in range(len(route) - seg + 1):
                chunk = route[i:i + seg]
                rest = route[:i] + route[i + seg:]
                for pos in range(len(rest) + 1):
                    if pos == i:
                        continue
                    cand = rest[:pos] + chunk + rest[pos:]
                    if route_cost(cand, dist, nodes) < base - 1e-9:
                        route, base, improved = cand, route_cost(cand, dist, nodes), True
                        break
                if improved:
                    break
            if improved:
                break
    return route


def _local_search(route, dist, nodes, budget):
    """2-opt + or-opt로 비용 최소화 → 남은 예산에 노드 삽입, 안정될 때까지."""
    prev = -1
    while True:
        route = _two_opt(route, dist, nodes, budget)
        route = _or_opt(route, dist, nodes, budget)
        route = _insert_extra(route, dist, nodes, budget)
        v = route_value(feasible_prefix(route, dist, nodes, budget), nodes)
        if v <= prev:
            break
        prev = v
    return feasible_prefix(route, dist, nodes, budget)


def plan_greedy_ls(dist, nodes, budget):
    return _local_search(plan_greedy_ratio(dist, nodes, budget),
                         dist, nodes, budget)


def _randomized_greedy(dist, nodes, budget, rng, k=3):
    """상위 k개 비율 후보 중 무작위 선택 (GRASP용 다양성)."""
    cur, used, route = 0, 0, []
    remaining = set(range(1, len(nodes) + 1))
    while True:
        scored = []
        for nid in remaining:
            d = dist.get(cur, {}).get(nid, INF)
            if d is INF:
                continue
            step = d + nodes[nid - 1].solve_cost
            if used + step > budget:
                continue
            scored.append((nodes[nid - 1].value / max(step, 1), nid, step))
        if not scored:
            break
        scored.sort(reverse=True)
        ratio, nid, step = rng.choice(scored[:k])
        used += step
        route.append(nid)
        remaining.discard(nid)
        cur = nid
    return route


def plan_grasp(dist, nodes, budget, restarts=12, seed=0):
    rng = random.Random(seed)
    best, best_v = [], -1
    base = plan_greedy_ls(dist, nodes, budget)
    bv = route_value(base, nodes)
    if bv > best_v:
        best, best_v = base, bv
    for _ in range(restarts):
        r = _local_search(_randomized_greedy(dist, nodes, budget, rng),
                          dist, nodes, budget)
        v = route_value(r, nodes)
        if v > best_v:
            best, best_v = r, v
    return best


def plan_ils(dist, nodes, budget, iters=60, seed=0):
    """Iterated Local Search: LS → 교란(double-bridge/제거) → LS, 개선시 채택."""
    rng = random.Random(seed)
    cur = plan_greedy_ls(dist, nodes, budget)
    best, best_v = cur[:], route_value(cur, nodes)
    for _ in range(iters):
        r = cur[:]
        if len(r) >= 4 and rng.random() < 0.5:        # double-bridge
            a, b, c = sorted(rng.sample(range(1, len(r)), 3))
            r = r[:a] + r[b:c] + r[a:b] + r[c:]
        else:                                          # 무작위 제거
            for _ in range(rng.randint(1, max(1, len(r) // 3))):
                if r:
                    r.pop(rng.randrange(len(r)))
        r = _local_search(r, dist, nodes, budget)
        v = route_value(r, nodes)
        if v >= best_v:
            best, best_v = r[:], v
            cur = r
        elif v >= route_value(cur, nodes) - max(best_v * 0.02, 1):
            cur = r  # 약한 악화 허용 (탐색 다양성)
    return best


def plan_best(dist, nodes, budget, seed=0):
    """실전 배포용 앙상블: 여러 솔버 중 최고 가치 경로 채택."""
    cands = [
        plan_greedy_ls(dist, nodes, budget),
        plan_grasp(dist, nodes, budget, restarts=10, seed=seed),
        plan_ils(dist, nodes, budget, iters=50, seed=seed),
        plan_sa(dist, nodes, budget, iters=5000, seed=seed),
    ]
    return max(cands, key=lambda r: route_value(
        feasible_prefix(r, dist, nodes, budget), nodes))


# --- P3: 빔 서치 ------------------------------------------------------
def plan_beam(dist, nodes, budget, width=200):
    N = len(nodes)
    # state: (value, used, cur, frozenset visited, route)
    start = (0, 0, 0, frozenset(), [])
    beam = [start]
    best = start
    for _ in range(N):
        nxt = []
        for val, used, cur, vis, route in beam:
            for nid in range(1, N + 1):
                if nid in vis:
                    continue
                d = dist.get(cur, {}).get(nid, INF)
                if d is INF:
                    continue
                step = d + nodes[nid - 1].solve_cost
                if used + step > budget:
                    continue
                nv = val + nodes[nid - 1].value
                st = (nv, used + step, nid, vis | {nid}, route + [nid])
                nxt.append(st)
                if nv > best[0]:
                    best = st
        if not nxt:
            break
        # 가치 우선, 동점 시 사용시간 적은 순
        nxt.sort(key=lambda s: (-s[0], s[1]))
        beam = nxt[:width]
    return best[4]


# --- P4: 시뮬레이티드 어닐링 (집합+순서 동시 최적화) -----------------
def plan_sa(dist, nodes, budget, iters=6000, seed=0, init=None):
    rng = random.Random(seed)
    N = len(nodes)
    cur = feasible_prefix(init or plan_greedy_ls(dist, nodes, budget),
                          dist, nodes, budget)

    def val(r):
        return route_value(r, nodes)

    best = cur[:]
    best_v = cur_v = val(best)
    T0, T1 = max(best_v, 1) * 0.4, 0.5
    stale = 0
    for k in range(iters):
        T = T0 * (T1 / T0) ** (k / max(iters - 1, 1))
        r = cur[:]
        move = rng.random()
        if move < 0.35 and N > len(r):                 # 삽입
            outside = [n for n in range(1, N + 1) if n not in r]
            if outside:
                r.insert(rng.randint(0, len(r)), rng.choice(outside))
        elif move < 0.5 and r:                          # 제거
            r.pop(rng.randrange(len(r)))
        elif move < 0.78 and len(r) >= 2:               # 2-opt 구간 반전
            i = rng.randrange(len(r) - 1)
            j = rng.randrange(i + 1, len(r))
            r[i:j + 1] = r[i:j + 1][::-1]
        elif move < 0.92 and len(r) >= 2:               # or-opt 단일 재배치
            i = rng.randrange(len(r))
            x = r.pop(i)
            r.insert(rng.randrange(len(r) + 1), x)
        elif len(r) >= 2:                                # 교환
            i, j = rng.sample(range(len(r)), 2)
            r[i], r[j] = r[j], r[i]
        r = feasible_prefix(r, dist, nodes, budget)
        rv = val(r)
        d = rv - cur_v
        if d >= 0 or rng.random() < math.exp(d / max(T, 1e-9)):
            cur, cur_v = r, rv
            if rv > best_v:
                best, best_v, stale = r[:], rv, 0
            else:
                stale += 1
        else:
            stale += 1
        if stale > iters // 6:                           # 정체 시 best로 재시작 + 강화
            cur = _local_search(best[:], dist, nodes, budget)
            cur_v = val(cur)
            if cur_v > best_v:
                best, best_v = cur[:], cur_v
            stale = 0
    return _local_search(best, dist, nodes, budget)


# --- 진짜 최적해: Held-Karp 비트마스크 DP (벤치마크 optimality gap용) --
def plan_exact(dist, nodes, budget, node_cap=18):
    """O(2^N · N^2) 정확 Orienteering 해.
    mincost[mask][last] = mask 노드 집합을 방문하고 last에서 끝나는 최소 비용.
    예산 내 달성 가능한 최대 가치 집합을 역추적해 경로 반환. N>node_cap이면 None.
    """
    N = len(nodes)
    if N > node_cap:
        return None
    # 0=start; 노드 j 진입비용 = dist[i][j] + solve_cost[j]
    INFc = budget + 1
    full = 1 << N

    def edge(i, j):  # i,j: 0=start, 1..N -> nodes; 노드 인덱스
        d = dist.get(i, {}).get(j, None)
        return None if d is None else d + nodes[j - 1].solve_cost

    # mincost[mask] = dict{last_bitpos: cost}
    mincost = [dict() for _ in range(full)]
    for j in range(1, N + 1):
        e = edge(0, j)
        if e is not None and e <= budget:
            mincost[1 << (j - 1)][j - 1] = e

    best_val, best_mask, best_last = 0, 0, -1
    val = [0] + [n.value for n in nodes]
    # 마스크를 popcount 오름차순에 가깝게: 단순 증가 순회로 충분(부분집합 먼저)
    for mask in range(1, full):
        cur = mincost[mask]
        if not cur:
            continue
        mval = 0
        mm = mask
        while mm:
            b = (mm & -mm).bit_length() - 1
            mval += val[b + 1]
            mm &= mm - 1
        for last, c in cur.items():
            if mval > best_val:
                best_val, best_mask, best_last = mval, mask, last
            for j in range(N):
                if mask & (1 << j):
                    continue
                e = edge(last + 1, j + 1)
                if e is None:
                    continue
                nc = c + e
                if nc > budget:
                    continue
                nm = mask | (1 << j)
                if mincost[nm].get(j, INFc) > nc:
                    mincost[nm][j] = nc

    # 역추적
    route = []
    mask, last = best_mask, best_last
    while mask:
        route.append(last + 1)
        c = mincost[mask][last]
        pm = mask ^ (1 << last)
        if pm == 0:
            break
        found = False
        for p, pc in mincost[pm].items():
            e = edge(p + 1, last + 1)
            if e is not None and abs(pc + e - c) < 1e-9:
                mask, last = pm, p
                found = True
                break
        if not found:
            break
    route.reverse()
    return route


PLANNERS = {
    "nearest":     plan_nearest,
    "greedy":      plan_greedy_ratio,
    "greedy+LS":   plan_greedy_ls,
    "GRASP":       plan_grasp,
    "ILS":         plan_ils,
    "SA":          plan_sa,
    "BEST(앙상블)": plan_best,
}
