"""베이스라인 에이전트 + 전략 토글.

전략 레버 (docs/06-winning-strategy.md):
  - code_solve  : 챌린지를 코드로 풀어 정답률 ~100% (vs 암산 정확도)
  - budget_path : 남은 시간 내 '가치/비용' 최대 타깃 선택 (vs 최근접 코인)
  - use_memory  : 재탐색/재계산 낭비 제거 (vs 가끔 헛스텝)
"""
from __future__ import annotations

import random
from dataclasses import dataclass

from game import Game


@dataclass
class Strategy:
    code_solve: bool = False
    budget_path: bool = False
    use_memory: bool = False


def play_episode(game: Game, cfg: dict, strat: Strategy, seed: int = 0) -> dict:
    rng = random.Random(seed)
    b = cfg["budget"]
    ch = cfg["challenges"]
    bo = cfg["bonus"]

    pos = game.start
    time_left = b["time_steps"]
    lives = b["lives"]
    score = 0
    streak = 0

    coins = dict(game.coins)
    enemies = {k: dict(v) for k, v in game.enemies.items()}
    treasure = game.treasure
    treasure_taken = False

    while time_left > 0 and lives > 0:
        dist = game.bfs_dist(pos)

        # 후보 타깃 수집
        cands = []  # (kind, cell, value, cost_steps)
        for cell, val in coins.items():
            if cell in dist:
                cands.append(("coin", cell, val, dist[cell] * b["move_cost_steps"]))
        for cell, e in enemies.items():
            if e["solved"] or cell not in dist:
                continue
            exp = (
                ch["score_per_solved"]
                if strat.code_solve
                else ch["llm_guess_accuracy"] * ch["score_per_solved"]
                - (1 - ch["llm_guess_accuracy"]) * ch["wrong_penalty_score"]
            )
            cost = dist[cell] * b["move_cost_steps"] + b["solve_cost_steps"]
            cands.append(("enemy", cell, exp, cost))
        if treasure and not treasure_taken and treasure in dist:
            cands.append(
                ("treasure", treasure, cfg["treasure"]["bonus_score"],
                 dist[treasure] * b["move_cost_steps"])
            )

        cands = [c for c in cands if c[3] <= time_left]
        if not cands:
            break

        if strat.budget_path:
            # 가치/비용 비 최대 (예산제약 수집 최적화의 탐욕 근사)
            kind, cell, val, cost = max(cands, key=lambda c: c[2] / max(c[3], 1))
        else:
            # 순진한 베이스라인: 가장 가까운 코인, 없으면 가장 가까운 타깃
            coin_c = [c for c in cands if c[0] == "coin"]
            pool = coin_c or cands
            kind, cell, val, cost = min(pool, key=lambda c: c[3])

        # 메모리 미사용 시 가끔 헛스텝(재탐색 낭비)
        if not strat.use_memory and rng.random() < 0.15:
            time_left -= 1
            if time_left <= 0:
                break

        time_left -= cost
        pos = cell
        if time_left < 0:
            break

        if kind == "coin":
            score += coins.pop(cell)
        elif kind == "treasure":
            score += cfg["treasure"]["bonus_score"]
            treasure_taken = True
        else:  # enemy / challenge
            correct = True if strat.code_solve else (rng.random() < ch["llm_guess_accuracy"])
            enemies[cell]["solved"] = True
            if correct:
                score += ch["score_per_solved"]
                streak += 1
                score += bo.get("consecutive_solve_bonus", 0) * streak
            else:
                score -= ch["wrong_penalty_score"]
                lives -= ch["wrong_penalty_lives"]
                streak = 0

    if time_left > 0:
        score += bo.get("early_finish_bonus_per_step", 0) * time_left

    return {
        "score": score,
        "time_left": max(time_left, 0),
        "lives": lives,
        "coins_left": len(coins),
        "challenges_left": sum(1 for e in enemies.values() if not e["solved"]),
        "treasure": treasure_taken,
    }
