"""Exemplo: dois pregões, âncora automática no fechamento anterior.

Reproduz o cenário da imagem: o pregão anterior define a linha de 0%
(fechamento), o dia seguinte sobe até a região de +1%, forma o engolfo de
baixa no topo e a venda busca 650 pontos com stop de 360.

    python3 exemplo.py
"""

from robo import Candle, StrategyParams, backtest

D1, D2 = "2026-08-19", "2026-08-20"

candles = [
    # --- pregão 19/08: última barra fecha em 169341 (linha de 0% do dia 20)
    Candle(169_600, 169_800, 169_200, 169_341, session=D1),
    # --- pregão 20/08: sobe até a região de +1% (169341*1.01 ~= 171035)
    Candle(169_400, 169_700, 169_300, 169_600, session=D2),
    Candle(169_600, 170_000, 169_500, 169_900, session=D2),
    Candle(169_900, 170_400, 169_800, 170_300, session=D2),
    Candle(170_300, 170_800, 170_200, 170_700, session=D2),
    Candle(170_700, 171_035, 170_600, 170_950, session=D2),  # topo em +1% (prev)
    Candle(171_000, 171_030, 170_550, 170_600, session=D2),  # engolfo de baixa
    Candle(170_600, 170_650, 169_800, 169_900, session=D2),  # cai e toca o alvo
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


# Padrão do operacional: BOTH (swing + linhas de %), âncora automática no
# fechamento do pregão anterior — nenhum ref_price manual necessário.
rodar("Modo BOTH (padrão, âncora = fech. anterior):", StrategyParams(lookback=6))

# Comparações:
rodar("\nModo SWING (só extremo recente):", StrategyParams(lookback=6, region_mode="swing"))
rodar(
    "\nModo PERCENT (só linhas de %, banda 1%):",
    StrategyParams(lookback=6, region_mode="percent", percent_entrada=1.0),
)
