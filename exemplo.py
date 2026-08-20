"""Exemplo mínimo: gera um setup de venda no topo e roda o backtest.

    python3 exemplo.py
"""

from robo import Candle, StrategyParams, backtest

# Série sintética: sobe até o topo, engolfo de baixa e depois despenca.
candles = [
    Candle(170_000, 170_200, 169_900, 170_100),
    Candle(170_100, 170_400, 170_000, 170_300),
    Candle(170_300, 170_600, 170_200, 170_500),
    Candle(170_500, 170_800, 170_400, 170_700),
    Candle(170_700, 171_000, 170_600, 170_900),  # candle de alta (prev)
    Candle(171_000, 171_035, 170_550, 170_600),  # engolfo de baixa no topo
    Candle(170_600, 170_650, 169_800, 169_900),  # cai e toca o alvo (-650)
]

res = backtest(candles, StrategyParams(lookback=6))
print(res.summary())
for t in res.trades:
    print(
        f"  {t.direction} @ {t.entry_price:.0f} -> {t.result} "
        f"@ {t.exit_price:.0f} ({t.pnl_points:+.0f} pts)"
    )
