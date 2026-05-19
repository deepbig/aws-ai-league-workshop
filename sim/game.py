"""그리드 미로 게임 환경 + 보상 노드/거리 추출.

핵심 최적화 문제: 시작점에서 제한 시간(time_steps) 안에 보상 노드
(코인=가치, 챌린지=격파점수, 보물=보너스)를 방문해 점수 합을 최대화.
챌린지는 코드풀이 가정 시 항상 정답(생명 손실 0) → 순수 Orienteering.

[추론] 기반 모델. 당일 [확정]값으로 config.json 교체 시 그대로 재검증.
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
class Node:
    cell: tuple          # (r, c)
    kind: str            # "coin" | "challenge" | "treasure"
    value: int           # 점수 기여
    solve_cost: int      # 도착 후 추가 소모 스텝 (코인=0)


@dataclass
class Game:
    cfg: dict
    seed: int = 0

    grid: list = field(default_factory=list)     # 0=통로, 1=벽
    start: tuple = (0, 0)
    nodes: list = field(default_factory=list)    # list[Node]
    dist: dict = field(default_factory=dict)     # idx -> {idx: steps}; 0 = start

    def __post_init__(self):
        self._build()
        self._compute_distance_matrix()

    # ---- 맵/노드 생성 --------------------------------------------------
    def _build(self):
        m = self.cfg["map"]
        rng = random.Random((self.seed * 1_000_003) ^ m["seed"])
        W, H = m["width"], m["height"]
        self.grid = [[0] * W for _ in range(H)]
        for r in range(H):
            for c in range(W):
                if (r, c) != (0, 0) and rng.random() < m["wall_ratio"]:
                    self.grid[r][c] = 1
        self.start = (0, 0)
        # 시작점 인접 칸은 개방 (시작점 고립 방지)
        for dr, dc in ((1, 0), (0, 1)):
            if dr < H and dc < W:
                self.grid[dr][dc] = 0

        # 보상 배치에 충분한 도달 가능 칸 확보 (벽 점진 제거로 연결성 보장)
        need = self.cfg["coins"]["count"] + self.cfg["challenges"]["count"] + 2
        walls = [(r, c) for r in range(H) for c in range(W) if self.grid[r][c]]
        rng.shuffle(walls)
        wi = 0
        while len(self._bfs(self.start)) - 1 < need and wi < len(walls):
            r, c = walls[wi]
            self.grid[r][c] = 0
            wi += 1

        reachable = self._bfs(self.start).keys()
        free = [p for p in reachable if p != self.start]
        rng.shuffle(free)

        cc, ch, tr = self.cfg["coins"], self.cfg["challenges"], self.cfg["treasure"]
        nodes: list[Node] = []

        n_coin = min(cc["count"], len(free))
        for p in free[:n_coin]:
            nodes.append(Node(p, "coin", rng.randint(cc["value_min"], cc["value_max"]), 0))

        rest = free[n_coin:]
        n_ch = min(ch["count"], len(rest))
        for p in rest[:n_ch]:
            nodes.append(Node(p, "challenge", ch["score_per_solved"], ch["solve_cost_steps"]))

        rest2 = rest[n_ch:]
        if tr["present"] and rest2:
            nodes.append(Node(rest2[-1], "treasure", tr["bonus_score"], 0))

        self.nodes = nodes

    def _bfs(self, src):
        H, W = len(self.grid), len(self.grid[0])
        dist = {src: 0}
        q = deque([src])
        while q:
            r, c = q.popleft()
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nr, nc = r + dr, c + dc
                if 0 <= nr < H and 0 <= nc < W and self.grid[nr][nc] == 0 \
                        and (nr, nc) not in dist:
                    dist[(nr, nc)] = dist[(r, c)] + 1
                    q.append((nr, nc))
        return dist

    # ---- 거리행렬 (0 = start, 1..N = nodes) ----------------------------
    def _compute_distance_matrix(self):
        anchors = [self.start] + [n.cell for n in self.nodes]
        self.dist = {}
        for i, cell in enumerate(anchors):
            d = self._bfs(cell)
            self.dist[i] = {
                j: d[anchors[j]] for j in range(len(anchors)) if anchors[j] in d
            }

    # ---- 점수 평가: 노드 인덱스(1..N) 방문 순서 -> (score, used_steps) --
    def evaluate(self, route: list[int], time_budget: int) -> tuple[int, int]:
        """route: 방문할 노드 idx 리스트(1-based). 예산 초과분은 미방문 처리."""
        score = 0
        used = 0
        cur = 0  # start
        for nid in route:
            if nid not in self.dist.get(cur, {}):
                break  # 도달 불가
            step = self.dist[cur][nid] + self.nodes[nid - 1].solve_cost
            if used + step > time_budget:
                break
            used += step
            score += self.nodes[nid - 1].value
            cur = nid
        return score, used
