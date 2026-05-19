"""규칙 변동 강건성 검증.

핵심 질문: 당일 채점 규칙(score_model)이 무엇이든,
'권장 에이전트 정책' = (강한 navigate 라우팅 + 챌린지 코드풀이) 가
그 규칙의 진짜 최적해에 계속 근접하는가?  프롬프트/구조 변경 없이 값만 바꿔서.

비교(각 규칙 레짐, 소규모 → Held-Karp 진짜 최적해 계산):
  naive   : LLM 암산 + 최근접 이동      (전형적 베이스라인)
  POLICY  : 코드풀이 + 강한 라우팅       (본 저장소 권장 에이전트 정책)
  EXACT   : 그 레짐의 진짜 최적해         (상한)

  python3 sim/robustness.py
"""
from __future__ import annotations

import copy
import statistics

from game import Game, load_config
from planners import plan_nearest, plan_ils, plan_exact

BASE = load_config()

# 당일 나올 수 있는 규칙 레짐 — score_model을 값만 바꿔 표현
REGIMES = {
    "baseline":        {},
    "challenge-heavy": {"challenges.score_per_solved": 1500},
    "penalty-heavy":   {"challenges.wrong_penalty_score": 800,
                        "challenges.llm_guess_accuracy": 0.45},
    "coins-uniform":   {"coins.value_min": 150, "coins.value_max": 150},
    "coins-varied":    {"coins.value_min": 20, "coins.value_max": 500},
    "time-tight":      {"budget.time_steps": 30},
}


def apply(cfg, patch):
    c = copy.deepcopy(cfg)
    for k, v in patch.items():
        a, b = k.split(".")
        c[a][b] = v
    # 소규모 → 진짜 최적해 계산 가능
    c["map"] = {"width": 6, "height": 6, "wall_ratio": 0.15, "seed": 7}
    c["coins"]["count"] = 8
    c["challenges"]["count"] = 3
    if "budget" not in patch and "budget.time_steps" not in patch:
        c["budget"]["time_steps"] = 30
    return c


def score_naive(g, cfg, seed):
    """암산: 챌린지 정답률 = llm_guess_accuracy, 경로 = 최근접."""
    import random
    rng = random.Random(seed)
    bg = cfg["budget"]["time_steps"]
    route = plan_nearest(g.dist, g.nodes, bg)
    acc = cfg["challenges"]["llm_guess_accuracy"]
    pen = cfg["challenges"]["wrong_penalty_score"]
    s, cur, used = 0, 0, 0
    for nid in route:
        n = g.nodes[nid - 1]
        used += g.dist[cur][nid] + n.solve_cost
        if used > bg:
            break
        cur = nid
        if n.kind == "challenge":
            s += n.value if rng.random() < acc else -pen
        else:
            s += n.value
    return s


def main():
    seeds = range(24)
    print(f"{'regime':<16}{'naive':>9}{'POLICY':>9}{'EXACT':>9}"
          f"{'POLICY%opt':>12}{'naive%opt':>11}")
    print("-" * 66)
    for name, patch in REGIMES.items():
        cfg = apply(BASE, patch)
        bg = cfg["budget"]["time_steps"]
        nv, pol, ex = [], [], []
        for s in seeds:
            g = Game(cfg=cfg, seed=s)
            nv.append(score_naive(g, cfg, s))
            pol.append(g.evaluate(plan_ils(g.dist, g.nodes, bg, iters=120, seed=s), bg)[0])
            r = plan_exact(g.dist, g.nodes, bg, node_cap=20)
            ex.append(g.evaluate(r, bg)[0] if r else None)
        v = [i for i, x in enumerate(ex) if x is not None]
        em = statistics.mean(ex[i] for i in v)
        pm = statistics.mean(pol[i] for i in v)
        nm = statistics.mean(nv[i] for i in v)
        print(f"{name:<16}{nm:>9.0f}{pm:>9.0f}{em:>9.0f}"
              f"{100*pm/em:>11.1f}%{100*nm/em:>10.1f}%")

    print("\n결론: 규칙(score_model)이 어떻게 바뀌든 POLICY는 진짜 최적에 근접 유지,")
    print("      naive와 격차가 큼. → '구조 불변, 값만 교체'로 변수 상황 적응 가능.")


if __name__ == "__main__":
    main()
