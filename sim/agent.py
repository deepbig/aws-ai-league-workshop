"""에피소드 실행기 — 강한 라우터 위에서 '챌린지 코드풀이' 레버를 정량화.

라우팅은 planners(기본 BEST)로 (모든 챌린지 해결 가능 가정) 계획.
실행 시 코드풀이 여부에 따라 챌린지 결과가 달라진다:
  - code_solve=True  : 챌린지 항상 정답 (코드 실행). 가치 획득, 생명 손실 0.
  - code_solve=False : llm_guess_accuracy 확률로 정답. 오답 시 점수 페널티
                       + 생명 -1, 생명 0이면 종료.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

from game import Game
from planners import PLANNERS, feasible_prefix


@dataclass
class Strategy:
    planner: str = "BEST(앙상블)"
    code_solve: bool = True


def play_episode(game: Game, cfg: dict, strat: Strategy, seed: int = 0) -> dict:
    rng = random.Random(seed)
    budget = cfg["budget"]["time_steps"]
    lives = cfg["budget"]["lives"]
    ch = cfg["challenges"]

    route = PLANNERS[strat.planner](game.dist, game.nodes, budget)
    route = feasible_prefix(route, game.dist, game.nodes, budget)

    score = 0
    solved = wrong = 0
    for nid in route:
        node = game.nodes[nid - 1]
        if node.kind == "challenge" and not strat.code_solve:
            if rng.random() < ch["llm_guess_accuracy"]:
                score += node.value
                solved += 1
            else:
                score -= ch["wrong_penalty_score"]
                lives -= ch["wrong_penalty_lives"]
                wrong += 1
                if lives <= 0:
                    break
        else:
            score += node.value
            if node.kind == "challenge":
                solved += 1
    return {"score": score, "lives": lives, "solved": solved, "wrong": wrong}
