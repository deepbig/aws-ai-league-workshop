"""플래너 벤치마크 — 최고 점수 방법 규명.

3단계:
  SMALL : N~11  → Held-Karp EXACT(진짜 최적해) 대비 %opt
  MID   : N~18  → Held-Karp EXACT 대비 %opt (최적해 계산 가능 최대 규모)
  FULL  : N~28  → 최적해 계산 불가. 장기 ILS = REF(최선근사) 대비 %ref + 절대점수

  python3 sim/bench.py            # 기본
  python3 sim/bench.py 60         # seed 수
"""
from __future__ import annotations

import copy
import statistics
import sys
import time

from game import Game, load_config
from planners import PLANNERS, plan_exact, plan_ils, feasible_prefix, route_value


def _ref_full(g, budget):
    """FULL용 최선근사 레퍼런스: 장기 ILS."""
    r = plan_ils(g.dist, g.nodes, budget, iters=400, seed=12345)
    return g.evaluate(r, budget)[0]


def _tier(title, cfg, n_seeds, use_exact):
    m = cfg["map"]
    budget = cfg["budget"]["time_steps"]
    seeds = list(range(n_seeds))
    print(f"\n=== {title} ===")
    print(f"map {m['width']}x{m['height']} wall {m['wall_ratio']} | budget {budget}"
          f" | coins {cfg['coins']['count']} ch {cfg['challenges']['count']}"
          f" | seeds {n_seeds}")

    rows = {name: {"s": [], "t": 0.0} for name in PLANNERS}
    ref = []
    ref_label = "EXACT" if use_exact else "REF(장기ILS)"
    for s in seeds:
        g = Game(cfg=cfg, seed=s)
        if use_exact:
            r = plan_exact(g.dist, g.nodes, budget, node_cap=20)
            ref.append(g.evaluate(r, budget)[0] if r is not None else None)
        else:
            ref.append(_ref_full(g, budget))
        for name, fn in PLANNERS.items():
            t0 = time.perf_counter()
            route = fn(g.dist, g.nodes, budget)
            rows[name]["t"] += time.perf_counter() - t0
            rows[name]["s"].append(g.evaluate(route, budget)[0])

    valid = [i for i, v in enumerate(ref) if v is not None]
    ref_mean = statistics.mean(ref[i] for i in valid) if valid else None

    hdr = f"{'planner':<13}{'평균':>9}{'중앙':>9}{'최소':>8}{'%' + ref_label:>14}{'ms/seed':>10}"
    print(hdr)
    print("-" * len(hdr))
    if ref_mean:
        rv = [ref[i] for i in valid]
        print(f"{ref_label:<13}{ref_mean:>9.0f}{statistics.median(rv):>9.0f}"
              f"{min(rv):>8.0f}{'100.00':>14}{'-':>10}")
    for name in PLANNERS:
        sc = rows[name]["s"]
        mean = statistics.mean(sc)
        pct = (100 * statistics.mean(sc[i] for i in valid) / ref_mean) if ref_mean else 0
        print(f"{name:<13}{mean:>9.0f}{statistics.median(sc):>9.0f}{min(sc):>8.0f}"
              f"{pct:>14.2f}{1000 * rows[name]['t'] / n_seeds:>10.1f}")


def main(n):
    cfg = load_config()

    small = copy.deepcopy(cfg)
    small["map"] = {"width": 6, "height": 6, "wall_ratio": 0.15, "seed": 7}
    small["coins"]["count"] = 8
    small["challenges"]["count"] = 2
    small["budget"]["time_steps"] = 28
    _tier("SMALL (vs 진짜 최적해)", small, min(n, 40), use_exact=True)

    mid = copy.deepcopy(cfg)
    mid["map"] = {"width": 8, "height": 8, "wall_ratio": 0.15, "seed": 7}
    mid["coins"]["count"] = 14
    mid["challenges"]["count"] = 3
    mid["budget"]["time_steps"] = 44
    _tier("MID (vs 진짜 최적해, N~18)", mid, min(n, 24), use_exact=True)

    _tier("FULL (관찰 규모, vs 장기 레퍼런스)", cfg, n, use_exact=False)

    print("\n결론 지표: SMALL/MID의 %EXACT가 100에 가까우면 그 플래너는 '최적에 근접'.")
    print("           FULL은 최적 계산 불가 → %REF + 절대점수로 우열 판단.")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 40)
