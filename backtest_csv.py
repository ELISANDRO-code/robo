"""Backtest com dados reais: responde se o setup tem edge ou não.

Uso:
    python3 backtest_csv.py caminho/para/dados_15m.csv [--modo both|swing|percent|either]
                            [--lookback 20] [--banda 0.5] [--dist 500]

O CSV é a exportação do Profit Pro (Data;Hora;Abertura;Máxima;Mínima;Fechamento...),
separador e decimal detectados automaticamente. Sem --modo, roda os três
principais (both, swing, percent) e imprime o comparativo.

O veredito usa o número-chave da gestão 360/650: win-rate de break-even =
360/(650+360) = 35,64% (antes de custos). Edge = win-rate acima disso com
amostra minimamente decente.
"""

import argparse
import sys

from robo import StrategyParams, backtest
from robo.data import load_csv

BREAK_EVEN = 360 / (650 + 360)  # 35,64%


def relatorio(nome, res):
    closed = res.wins + res.losses
    print(f"\n--- {nome} ---")
    print(f"  Trades fechados : {closed} (wins {res.wins} / losses {res.losses}"
          + (f" / abertos {len(res.trades) - closed}" if len(res.trades) != closed else "") + ")")
    if not closed:
        print("  Sem trades — nada a concluir neste modo.")
        return
    print(f"  Win-rate        : {res.win_rate:.1%}  (break-even: {BREAK_EVEN:.1%})")
    print(f"  Expectativa     : {res.expectancy:+.1f} pts/trade")
    print(f"  Resultado total : {res.total_points:+.0f} pts")
    print(f"  Profit factor   : {res.profit_factor:.2f}")
    print(f"  Máx. drawdown   : {res.max_drawdown:.0f} pts | Perdas seguidas: {res.max_consecutive_losses}")

    # veredito honesto
    if closed < 30:
        print(f"  Veredito        : AMOSTRA PEQUENA ({closed} trades) — sem conclusão estatística.")
    elif res.win_rate > BREAK_EVEN and res.expectancy > 0:
        margem = (res.win_rate - BREAK_EVEN) * 100
        print(f"  Veredito        : EDGE BRUTO POSITIVO (+{margem:.1f} p.p. acima do break-even; validar custos/derrapagem).")
    else:
        print("  Veredito        : SEM EDGE nesta amostra (win-rate abaixo/na linha do break-even).")


def main():
    ap = argparse.ArgumentParser(description="Backtest do setup Reversão 15m em CSV real")
    ap.add_argument("csv", help="arquivo CSV exportado do Profit (15 minutos)")
    ap.add_argument("--modo", choices=["both", "swing", "percent", "either"], default=None)
    ap.add_argument("--lookback", type=int, default=20)
    ap.add_argument("--recencia", type=int, default=3)
    ap.add_argument("--banda", type=float, default=0.5, help="banda mínima em %% (padrão 0.5)")
    ap.add_argument("--dist", type=float, default=500.0, help="distância máxima da região em pontos")
    args = ap.parse_args()

    candles = load_csv(args.csv)
    if len(candles) < 50:
        print(f"Apenas {len(candles)} candles no arquivo — dados insuficientes.", file=sys.stderr)
        sys.exit(1)

    sessoes = len({c.session for c in candles if c.session})
    print(f"Candles: {len(candles)} | Pregões: {sessoes} | "
          f"Período: {candles[0].time} -> {candles[-1].time}")
    print("Gestão fixa: SL 360 / TP 650 | Âncora 0%: fechamento do pregão anterior")

    modos = [args.modo] if args.modo else ["both", "swing", "percent"]
    for modo in modos:
        params = StrategyParams(
            lookback=args.lookback,
            recencia_regiao=args.recencia,
            region_mode=modo,
            percent_entrada=args.banda,
            dist_max_regiao=args.dist,
        )
        relatorio(f"modo {modo}", backtest(candles, params))


if __name__ == "__main__":
    main()
