"""전략 레버 ablation 러너.

사용:
  python3 sim/run.py            # 기본 30 에피소드
  python3 sim/run.py 100        # 100 에피소드

config.json 값을 워크샵 당일 [확정]값으로 바꾼 뒤 다시 실행해
어떤 전략 분기가 최고 점수인지 확인한다.
"""
import statistics
import sys

from agent import Strategy, play_episode
from game import Game, load_config

SCENARIOS = {
    "Baseline (암산+최근접)":            Strategy(False, False, False),
    "+코드풀이":                          Strategy(True,  False, False),
    "+예산경로":                          Strategy(False, True,  False),
    "+메모리":                            Strategy(False, False, True),
    "Full (전부 ON)":                     Strategy(True,  True,  True),
}


def run(n_episodes: int) -> None:
    cfg = load_config()
    print(f"에피소드/시나리오: {n_episodes}  | config: map "
          f"{cfg['map']['width']}x{cfg['map']['height']}, "
          f"time {cfg['budget']['time_steps']}, lives {cfg['budget']['lives']}\n")

    header = f"{'시나리오':<22}{'평균점수':>10}{'중앙값':>10}{'표준편차':>10}{'코인잔여':>9}{'챌린지잔여':>11}"
    print(header)
    print("-" * len(header))

    baseline_mean = None
    for name, strat in SCENARIOS.items():
        scores, coins_left, ch_left = [], [], []
        for ep in range(n_episodes):
            g = Game(cfg=cfg, seed=ep)
            r = play_episode(g, cfg, strat, seed=ep)
            scores.append(r["score"])
            coins_left.append(r["coins_left"])
            ch_left.append(r["challenges_left"])
        mean = statistics.mean(scores)
        if baseline_mean is None:
            baseline_mean = mean
        med = statistics.median(scores)
        sd = statistics.pstdev(scores)
        delta = "" if name.startswith("Baseline") else f"  ({mean - baseline_mean:+.0f} vs base)"
        print(f"{name:<22}{mean:>10.0f}{med:>10.0f}{sd:>10.0f}"
              f"{statistics.mean(coins_left):>9.1f}{statistics.mean(ch_left):>11.1f}{delta}")

    print("\n해석: 각 레버의 '평균점수 vs base' 증가폭 = 워크샵 당일 우선순위 근거.")
    print("      config.json을 [확정]값으로 교체 후 재실행하면 분기 우열이 갱신됨.")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    run(n)
