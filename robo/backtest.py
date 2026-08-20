"""Backtester simples para o setup de Reversão 15m.

Aplica a gestão fixa (Stop Loss 360 pontos / Take Profit 650 pontos), mantém
apenas uma posição por vez e respeita as regras de região:

* entrada a mercado no fechamento do candle de engolfo válido;
* no máximo ``max_entradas_regiao`` entradas na mesma região de topo/fundo
  (a "segunda oportunidade");
* nada de entrar se o preço já se afastou mais que ``dist_max_regiao`` pontos
  do extremo da região.

A saída é avaliada candle a candle a partir do candle seguinte ao da entrada.
Quando um mesmo candle toca stop e alvo, assume-se o stop (conservador).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence

from .strategy import Candle, Signal, StrategyParams, generate_signal


# Gestão fixa do operacional (em pontos).
STOP_LOSS_PONTOS = 360.0
TAKE_PROFIT_PONTOS = 650.0


@dataclass
class Trade:
    direction: str
    entry_index: int
    entry_price: float
    stop_price: float
    target_price: float
    exit_index: Optional[int] = None
    exit_price: Optional[float] = None
    result: Optional[str] = None      # "take", "stop" ou "open"
    pnl_points: float = 0.0


@dataclass
class BacktestResult:
    trades: List[Trade] = field(default_factory=list)

    @property
    def total_points(self) -> float:
        return sum(t.pnl_points for t in self.trades)

    @property
    def wins(self) -> int:
        return sum(1 for t in self.trades if t.result == "take")

    @property
    def losses(self) -> int:
        return sum(1 for t in self.trades if t.result == "stop")

    @property
    def win_rate(self) -> float:
        closed = self.wins + self.losses
        return (self.wins / closed) if closed else 0.0

    def summary(self) -> str:
        return (
            f"Trades: {len(self.trades)} | Wins: {self.wins} | "
            f"Losses: {self.losses} | Win rate: {self.win_rate:.1%} | "
            f"Resultado: {self.total_points:+.0f} pontos"
        )


def _same_region(ref_a: float, ref_b: float, tol: float) -> bool:
    return abs(ref_a - ref_b) <= tol


def backtest(
    candles: Sequence[Candle],
    params: Optional[StrategyParams] = None,
    stop_loss: float = STOP_LOSS_PONTOS,
    take_profit: float = TAKE_PROFIT_PONTOS,
) -> BacktestResult:
    """Roda o backtest sobre a série de candles."""
    if params is None:
        params = StrategyParams()

    result = BacktestResult()
    open_trade: Optional[Trade] = None

    # Controle de região (para "segunda oportunidade").
    region_dir: Optional[str] = None
    region_ref: Optional[float] = None
    region_entries = 0

    for i in range(len(candles)):
        cur = candles[i]

        # 1) Se há posição aberta, verifica saída neste candle.
        if open_trade is not None:
            if open_trade.direction == "sell":
                hit_stop = cur.high >= open_trade.stop_price
                hit_target = cur.low <= open_trade.target_price
            else:  # buy
                hit_stop = cur.low <= open_trade.stop_price
                hit_target = cur.high >= open_trade.target_price

            if hit_stop or hit_target:
                # stop tem prioridade quando ambos ocorrem no mesmo candle
                if hit_stop:
                    open_trade.result = "stop"
                    open_trade.exit_price = open_trade.stop_price
                else:
                    open_trade.result = "take"
                    open_trade.exit_price = open_trade.target_price
                open_trade.exit_index = i
                if open_trade.direction == "sell":
                    open_trade.pnl_points = open_trade.entry_price - open_trade.exit_price
                else:
                    open_trade.pnl_points = open_trade.exit_price - open_trade.entry_price
                open_trade = None
            # enquanto posicionado, não busca novo sinal
            continue

        # 2) Sem posição: procura sinal no candle fechado.
        signal = generate_signal(candles, i, params)
        if signal is None:
            continue

        # Controle de região / segunda oportunidade.
        if region_dir == signal.direction and region_ref is not None and _same_region(
            region_ref, signal.region_ref, params.tol_regiao
        ):
            if region_entries >= params.max_entradas_regiao:
                continue
        else:
            # nova região
            region_dir = signal.direction
            region_ref = signal.region_ref
            region_entries = 0

        region_entries += 1

        # 3) Abre a posição a mercado (fechamento do candle de engolfo).
        if signal.direction == "sell":
            trade = Trade(
                direction="sell",
                entry_index=i,
                entry_price=signal.entry_price,
                stop_price=signal.entry_price + stop_loss,
                target_price=signal.entry_price - take_profit,
            )
        else:
            trade = Trade(
                direction="buy",
                entry_index=i,
                entry_price=signal.entry_price,
                stop_price=signal.entry_price - stop_loss,
                target_price=signal.entry_price + take_profit,
            )
        result.trades.append(trade)
        open_trade = trade

    # Marca posição que ficou aberta ao fim da série.
    if open_trade is not None:
        open_trade.result = "open"

    return result
