"""Robô de Reversão 15m — Engolfo em região de topo/fundo.

Pacote com a lógica do setup (detecção de engolfo, contexto de topo/fundo,
veto e segunda oportunidade) e um backtester simples para validar as regras.
"""

from .strategy import (
    Candle,
    Signal,
    StrategyParams,
    is_bullish,
    is_bearish,
    is_bearish_engulfing,
    is_bullish_engulfing,
    is_swing_top,
    is_swing_bottom,
    in_top_zone_percent,
    in_bottom_zone_percent,
    top_line,
    bottom_line,
    generate_signal,
)
from .backtest import Trade, BacktestResult, backtest

__all__ = [
    "Candle",
    "Signal",
    "StrategyParams",
    "is_bullish",
    "is_bearish",
    "is_bearish_engulfing",
    "is_bullish_engulfing",
    "is_swing_top",
    "is_swing_bottom",
    "in_top_zone_percent",
    "in_bottom_zone_percent",
    "top_line",
    "bottom_line",
    "generate_signal",
    "Trade",
    "BacktestResult",
    "backtest",
]
