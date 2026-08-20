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

def rodar(titulo, params):
    res = backtest(candles, params)
    print(titulo)
    print("  " + res.summary())
    for t in res.trades:
        print(
            f"  {t.direction} @ {t.entry_price:.0f} -> {t.result} "
            f"@ {t.exit_price:.0f} ({t.pnl_points:+.0f} pts)"
        )


# (A) Só swing (extremo das últimas N barras)
rodar("Modo SWING:", StrategyParams(lookback=6, region_mode="swing"))

# (B) Só linhas de %: como no gráfico, a linha de 0% fica ABAIXO do topo e o
# preço subiu até +1%. Aqui o topo (171035) coincide com a linha de +1%.
REF_0PCT = 169_341  # 0%; +1% = 169341*1.01 ~= 171035
rodar(
    "\nModo PERCENT (topo em +1%):",
    StrategyParams(lookback=6, region_mode="percent", ref_price=REF_0PCT, percent_entrada=1.0),
)

# (A e B) Exige os dois ao mesmo tempo
rodar(
    "\nModo BOTH (swing + %):",
    StrategyParams(lookback=6, region_mode="both", ref_price=REF_0PCT, percent_entrada=1.0),
)
