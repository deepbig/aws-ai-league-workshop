"""관찰된 메커니즘을 파라미터화한 그리드 미로 게임 환경.

[추론] 기반 모델. 행동 인터페이스/챌린지 출제 규칙은 워크샵 당일 [확정]값으로
config.json을 교체하면 그대로 재검증된다. 실점수 예측기가 아니라
'어떤 전략 레버가 우월한지'를 가리기 위한 도구.
"""
from __future__ import annotations

import json
import os
import random
from collections import deque
from dataclasses import dataclass, field

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")


def load_config(path: str = CONFIG_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@dataclass
class Game:
    cfg: dict
    seed: int = 0

    grid: list = field(default_factory=list)        # 0=통로, 1=벽
    coins: dict = field(default_factory=dict)       # (r,c) -> value
    enemies: dict = field(default_factory=dict)     # (r,c) -> {"answer", "solved"}
    treasure: tuple | None = None
    start: tuple = (0, 0)

    def __post_init__(self):
        self._build()

    # ---- 맵 생성 -------------------------------------------------------
    def _build(self):
        m = self.cfg["map"]
        rng = random.Random(self.seed ^ m["seed"])
        W, H = m["width"], m["height"]
        self.grid = [[0] * W for _ in range(H)]
        for r in range(H):
            for c in range(W):
                if (r, c) != (0, 0) and rng.random() < m["wall_ratio"]:
                    self.grid[r][c] = 1
        self.start = (0, 0)

        free = [
            (r, c)
            for r in range(H)
            for c in range(W)
            if self.grid[r][c] == 0 and (r, c) != self.start
        ]
        # 시작점에서 도달 가능한 칸만 사용
        reachable = self._bfs_reachable(self.start)
        free = [p for p in free if p in reachable]
        rng.shuffle(free)

        cc = self.cfg["coins"]
        n_coins = min(cc["count"], len(free))
        for p in free[:n_coins]:
            self.coins[p] = rng.randint(cc["value_min"], cc["value_max"])

        rest = free[n_coins:]
        ch = self.cfg["challenges"]
        for p in rest[: min(ch["count"], len(rest))]:
            self.enemies[p] = {"answer": rng.randint(0, 999), "solved": False}

        if self.cfg["treasure"]["present"]:
            pool = rest[ch["count"]:] or rest or free
            self.treasure = pool[-1] if pool else None

    def _bfs_reachable(self, src):
        H, W = len(self.grid), len(self.grid[0])
        seen = {src}
        q = deque([src])
        while q:
            r, c = q.popleft()
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nr, nc = r + dr, c + dc
                if (
                    0 <= nr < H
                    and 0 <= nc < W
                    and self.grid[nr][nc] == 0
                    and (nr, nc) not in seen
                ):
                    seen.add((nr, nc))
                    q.append((nr, nc))
        return seen

    # ---- 경로 거리 -----------------------------------------------------
    def bfs_dist(self, src):
        """src -> 모든 칸 최단거리 (스텝 수)."""
        H, W = len(self.grid), len(self.grid[0])
        dist = {src: 0}
        q = deque([src])
        while q:
            r, c = q.popleft()
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nr, nc = r + dr, c + dc
                if (
                    0 <= nr < H
                    and 0 <= nc < W
                    and self.grid[nr][nc] == 0
                    and (nr, nc) not in dist
                ):
                    dist[(nr, nc)] = dist[(r, c)] + 1
                    q.append((nr, nc))
        return dist
