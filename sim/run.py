"""빠른 요약 러너 — 1등 전략의 두 핵심 레버를 한 번에 확인.

  python3 sim/run.py            # 기본 40 seed
  python3 sim/run.py 80

상세 최적성 검증은: python3 sim/bench.py
"""
from __future__ import annotations

import statistics
import sys

from agent import Strategy, play_episode
from game import Game, load_config
from planners import PLANNERS


def _mean_score(cfg, planner, seeds):
    sc = []
    for s in seeds:
        g = Game(cfg=cfg, seed=s)
        r = PLANNERS[planner](g.dist, g.nodes, cfg["budget"]["time_steps"])
        sc.append(g.evaluate(r, cfg["budget"]["time_steps"])[0])
    return statistics.mean(sc)


def main(n):
    cfg = load_config()
    seeds = list(range(n))
    m = cfg["map"]
    print(f"map {m['width']}x{m['height']} | budget {cfg['budget']['time_steps']}"
          f" | coins {cfg['coins']['count']} ch {cfg['challenges']['count']}"
          f" | seeds {n}\n")

    # 레버 A: 라우팅 품질 (낮은→높은)
    print("[레버 A] 경로 플래너별 평균 점수 (라우팅이 최대 점수원)")
    base = None
    for name in ("nearest", "greedy", "greedy+LS", "GRASP", "ILS", "SA", "BEST(앙상블)"):
        mean = _mean_score(cfg, name, seeds)
        if base is None:
            base = mean
        print(f"  {name:<13}{mean:>9.0f}  ({mean - base:+.0f} vs nearest)")

    # 레버 B: 챌린지 코드풀이 vs 암산 (동일 BEST 라우팅 위)
    print("\n[레버 B] 챌린지 처리: 코드풀이 vs LLM 암산 (BEST 라우팅 고정)")
    for label, code in (("코드풀이(권장)", True), ("LLM 암산", False)):
        sc = []
        for s in seeds:
            g = Game(cfg=cfg, seed=s)
            sc.append(play_episode(g, cfg, Strategy("BEST(앙상블)", code), s)["score"])
        print(f"  {label:<14}{statistics.mean(sc):>9.0f}")

    print("\n→ 결론: 강한 라우팅(BEST/ILS) + 챌린지 코드풀이 결합이 최고 점수.")
    print("  최적해 대비 검증은 sim/bench.py (SMALL/MID에서 %EXACT 확인).")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 40)
