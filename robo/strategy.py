"""Lógica do setup de Reversão 15m — Engolfo em região de topo/fundo.

Regra central: TOPO/FUNDO PRIMEIRO; ENGOLFO DEPOIS.
O engolfo apenas confirma a entrada; quem autoriza o setup é a localização
(o preço precisa estar numa região clara de topo ou de fundo).

Resumo do operacional:

* Venda no topo: o preço sobe, alcança/formaliza uma região de topo e surge
  um engolfo de baixa. No fechamento do candle de engolfo, entra vendido a
  mercado.
* Compra no fundo: o preço cai, alcança/formaliza uma região de fundo e surge
  um engolfo de alta. No fechamento do candle de engolfo, entra comprado a
  mercado.
* Veto principal: não operar engolfo que apareça no meio do caminho — o
  engolfo precisa surgir num topo/fundo válido, não numa perna qualquer.
* Segunda oportunidade: permitido entrar no segundo engolfo da mesma região,
  desde que o preço ainda não tenha se deslocado demais (~500 pontos) a partir
  da região do sinal.

Este módulo trabalha apenas com a *lógica* de sinal. A gestão fixa
(Stop Loss de 360 pontos e Take Profit de 650 pontos) é aplicada no
backtester (``robo.backtest``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence


@dataclass(frozen=True)
class Candle:
    """Um candle OHLC. ``time`` é opcional e apenas informativo."""

    open: float
    high: float
    low: float
    close: float
    time: Optional[str] = None

    @property
    def body_top(self) -> float:
        return max(self.open, self.close)

    @property
    def body_bottom(self) -> float:
        return min(self.open, self.close)


@dataclass
class StrategyParams:
    """Parâmetros configuráveis do setup.

    Attributes:
        lookback: número de candles usados para caracterizar a região de
            topo/fundo. O engolfo só é válido se marcar o extremo (máxima ou
            mínima) desse período — é isso que implementa o veto de
            "engolfo no meio do caminho".
        dist_max_regiao: distância máxima, em pontos, que o preço de entrada
            pode estar do extremo da região. Se já andou ~500 pontos ou mais a
            partir da região do sinal, não entra.
        max_entradas_regiao: quantas entradas são permitidas na mesma região
            (1 = só a primeira; 2 = permite a "segunda oportunidade").
        tol_regiao: tolerância, em pontos, para considerar que dois extremos
            pertencem à mesma região (evita recontar a mesma região por causa
            de uma nova máxima/mínima marginal).
    """

    lookback: int = 20
    dist_max_regiao: float = 500.0
    max_entradas_regiao: int = 2
    tol_regiao: float = 50.0


@dataclass(frozen=True)
class Signal:
    """Sinal gerado no fechamento do candle de engolfo."""

    index: int
    direction: str          # "sell" (venda no topo) ou "buy" (compra no fundo)
    entry_price: float      # fechamento do candle de engolfo (entrada a mercado)
    region_ref: float       # extremo da região (máxima do topo / mínima do fundo)
    distance: float         # distância do preço de entrada até o extremo (pontos)


# --------------------------------------------------------------------------- #
# Primitivas de candle
# --------------------------------------------------------------------------- #
def is_bullish(c: Candle) -> bool:
    """Candle de alta (fechou acima da abertura)."""
    return c.close > c.open


def is_bearish(c: Candle) -> bool:
    """Candle de baixa (fechou abaixo da abertura)."""
    return c.close < c.open


def is_bearish_engulfing(prev: Candle, cur: Candle) -> bool:
    """Engolfo de baixa: candle de alta seguido por candle de baixa cujo corpo
    engolfa o corpo anterior.

    Condições:
      * ``prev`` é de alta e ``cur`` é de baixa;
      * a abertura de ``cur`` é >= o fechamento de ``prev`` (abre no topo do
        corpo anterior ou acima) e o fechamento de ``cur`` é <= a abertura de
        ``prev`` (fecha na base do corpo anterior ou abaixo).
    """
    if not (is_bullish(prev) and is_bearish(cur)):
        return False
    return cur.open >= prev.close and cur.close <= prev.open


def is_bullish_engulfing(prev: Candle, cur: Candle) -> bool:
    """Engolfo de alta: candle de baixa seguido por candle de alta cujo corpo
    engolfa o corpo anterior."""
    if not (is_bearish(prev) and is_bullish(cur)):
        return False
    return cur.open <= prev.close and cur.close >= prev.open


# --------------------------------------------------------------------------- #
# Contexto: região de topo / fundo
# --------------------------------------------------------------------------- #
def is_swing_top(candles: Sequence[Candle], i: int, lookback: int) -> bool:
    """True se o candle ``i`` marca o topo da região (maior máxima dos últimos
    ``lookback`` candles, incluindo ``i``).

    Esta é a condição que autoriza uma *venda*: o preço subiu até uma região
    clara de topo. Um engolfo de baixa que apareça no meio de uma perna (sem
    ser a maior máxima do período) é vetado por não satisfazer esta condição.
    """
    start = max(0, i - lookback + 1)
    janela = candles[start : i + 1]
    if len(janela) < 2:
        return False
    return candles[i].high >= max(c.high for c in janela)


def is_swing_bottom(candles: Sequence[Candle], i: int, lookback: int) -> bool:
    """True se o candle ``i`` marca o fundo da região (menor mínima dos últimos
    ``lookback`` candles, incluindo ``i``).

    Condição que autoriza uma *compra*: o preço caiu até uma região clara de
    fundo.
    """
    start = max(0, i - lookback + 1)
    janela = candles[start : i + 1]
    if len(janela) < 2:
        return False
    return candles[i].low <= min(c.low for c in janela)


# --------------------------------------------------------------------------- #
# Geração de sinal
# --------------------------------------------------------------------------- #
def generate_signal(
    candles: Sequence[Candle],
    i: int,
    params: Optional[StrategyParams] = None,
) -> Optional[Signal]:
    """Avalia o candle ``i`` (já fechado) e retorna um :class:`Signal` se o
    setup estiver válido, ou ``None`` caso contrário.

    A avaliação é feita sempre no fechamento do candle — nunca durante a
    formação. Só considera engolfo que esteja numa região de topo/fundo
    válida e que respeite a distância máxima da região.
    """
    if params is None:
        params = StrategyParams()
    if i < 1:
        return None

    prev, cur = candles[i - 1], candles[i]

    # --- Venda no topo -----------------------------------------------------
    if is_bearish_engulfing(prev, cur) and is_swing_top(candles, i, params.lookback):
        start = max(0, i - params.lookback + 1)
        region_ref = max(c.high for c in candles[start : i + 1])
        distance = region_ref - cur.close
        # veto de "já andou demais": entrada longe demais do extremo da região
        if distance <= params.dist_max_regiao:
            return Signal(
                index=i,
                direction="sell",
                entry_price=cur.close,
                region_ref=region_ref,
                distance=distance,
            )

    # --- Compra no fundo ---------------------------------------------------
    if is_bullish_engulfing(prev, cur) and is_swing_bottom(candles, i, params.lookback):
        start = max(0, i - params.lookback + 1)
        region_ref = min(c.low for c in candles[start : i + 1])
        distance = cur.close - region_ref
        if distance <= params.dist_max_regiao:
            return Signal(
                index=i,
                direction="buy",
                entry_price=cur.close,
                region_ref=region_ref,
                distance=distance,
            )

    return None
