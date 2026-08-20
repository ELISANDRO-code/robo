"""Testes da lógica do setup de Reversão 15m."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from robo.strategy import (  # noqa: E402
    Candle,
    StrategyParams,
    is_bearish_engulfing,
    is_bullish_engulfing,
    is_swing_top,
    is_swing_bottom,
    generate_signal,
)
from robo.backtest import backtest  # noqa: E402


class TestEngolfo(unittest.TestCase):
    def test_engolfo_baixa_valido(self):
        prev = Candle(open=100, high=112, low=99, close=110)   # alta
        cur = Candle(open=111, high=113, low=98, close=99)     # baixa, engolfa
        self.assertTrue(is_bearish_engulfing(prev, cur))

    def test_engolfo_baixa_precisa_corpo_maior(self):
        prev = Candle(open=100, high=112, low=99, close=110)   # alta
        cur = Candle(open=109, high=111, low=104, close=105)   # não engolfa o corpo
        self.assertFalse(is_bearish_engulfing(prev, cur))

    def test_engolfo_baixa_exige_prev_alta(self):
        prev = Candle(open=110, high=112, low=99, close=100)   # baixa
        cur = Candle(open=111, high=113, low=98, close=99)
        self.assertFalse(is_bearish_engulfing(prev, cur))

    def test_engolfo_alta_valido(self):
        prev = Candle(open=110, high=111, low=98, close=100)   # baixa
        cur = Candle(open=99, high=113, low=97, close=112)     # alta, engolfa
        self.assertTrue(is_bullish_engulfing(prev, cur))

    def test_engolfo_alta_exige_prev_baixa(self):
        prev = Candle(open=100, high=111, low=98, close=110)   # alta
        cur = Candle(open=99, high=113, low=97, close=112)
        self.assertFalse(is_bullish_engulfing(prev, cur))


class TestRegiao(unittest.TestCase):
    def _serie_subida(self):
        # subida consistente até o índice 5 (topo)
        return [
            Candle(90, 92, 89, 91),
            Candle(91, 94, 90, 93),
            Candle(93, 96, 92, 95),
            Candle(95, 98, 94, 97),
            Candle(97, 100, 96, 99),
            Candle(99, 105, 98, 104),   # topo
        ]

    def test_swing_top(self):
        candles = self._serie_subida()
        # o índice 5 é o topo (maior máxima da janela)
        self.assertTrue(is_swing_top(candles, 5, lookback=6))
        # acrescenta uma barra que recua: ela não é o topo da janela
        candles = candles + [Candle(104, 104, 99, 100)]
        self.assertFalse(is_swing_top(candles, 6, lookback=6))

    def test_swing_bottom(self):
        candles = [Candle(h - 0, h + 1, h - 3, h - 1) for h in range(100, 90, -1)]
        # última barra tem a menor mínima
        self.assertTrue(is_swing_bottom(candles, len(candles) - 1, lookback=10))


class TestSinal(unittest.TestCase):
    def test_venda_no_topo(self):
        # sobe até a região de topo, depois engolfo de baixa marcando a máxima
        candles = [
            Candle(90, 92, 89, 91),
            Candle(91, 94, 90, 93),
            Candle(93, 96, 92, 95),
            Candle(95, 98, 94, 97),
            Candle(97, 100, 96, 99),    # candle de alta (prev do engolfo)
            Candle(100, 101, 92, 93),   # engolfo de baixa, maior máxima -> topo
        ]
        sig = generate_signal(candles, 5, StrategyParams(lookback=6))
        self.assertIsNotNone(sig)
        self.assertEqual(sig.direction, "sell")
        self.assertEqual(sig.entry_price, 93)

    def test_veto_engolfo_no_meio_do_caminho(self):
        # Cai forte (topo lá atrás), forma fundo, pequena subida e engolfo de
        # baixa NO MEIO da subida -> não é topo válido -> vetado.
        candles = [
            Candle(130, 131, 129, 130),   # topo antigo, bem acima
            Candle(129, 130, 118, 119),
            Candle(119, 120, 108, 109),
            Candle(109, 110, 100, 101),   # fundo
            Candle(101, 106, 100, 105),   # sobe (alta)
            Candle(106, 107, 101, 102),   # engolfo de baixa no meio da subida
        ]
        sig = generate_signal(candles, 5, StrategyParams(lookback=6))
        self.assertIsNone(sig)

    def test_compra_no_fundo(self):
        candles = [
            Candle(110, 111, 109, 110),
            Candle(110, 110, 106, 107),
            Candle(107, 108, 103, 104),
            Candle(104, 105, 101, 102),
            Candle(102, 103, 99, 100),    # candle de baixa (prev do engolfo)
            Candle(99, 108, 98, 107),     # engolfo de alta, menor mínima -> fundo
        ]
        sig = generate_signal(candles, 5, StrategyParams(lookback=6))
        self.assertIsNotNone(sig)
        self.assertEqual(sig.direction, "buy")
        self.assertEqual(sig.entry_price, 107)


class TestBacktest(unittest.TestCase):
    def test_venda_bate_alvo(self):
        # setup de venda; depois o preço cai 650+ pontos -> take
        candles = [
            Candle(1000, 1020, 990, 1010),
            Candle(1010, 1040, 1000, 1030),
            Candle(1030, 1060, 1020, 1050),
            Candle(1050, 1080, 1040, 1070),
            Candle(1070, 1100, 1060, 1090),   # alta (prev)
            Candle(1100, 1101, 1000, 1010),   # engolfo baixa no topo -> vende a 1010
            Candle(1010, 1010, 300, 320),     # despenca, toca alvo (1010-650=360)
        ]
        res = backtest(candles, StrategyParams(lookback=6))
        self.assertEqual(len(res.trades), 1)
        t = res.trades[0]
        self.assertEqual(t.direction, "sell")
        self.assertEqual(t.result, "take")
        self.assertEqual(t.pnl_points, 650)

    def test_venda_bate_stop(self):
        candles = [
            Candle(1000, 1020, 990, 1010),
            Candle(1010, 1040, 1000, 1030),
            Candle(1030, 1060, 1020, 1050),
            Candle(1050, 1080, 1040, 1070),
            Candle(1070, 1100, 1060, 1090),   # alta (prev)
            Candle(1100, 1101, 1000, 1010),   # engolfo baixa -> vende a 1010
            Candle(1010, 1400, 1005, 1390),   # sobe, toca stop (1010+360=1370)
        ]
        res = backtest(candles, StrategyParams(lookback=6))
        t = res.trades[0]
        self.assertEqual(t.result, "stop")
        self.assertEqual(t.pnl_points, -360)


if __name__ == "__main__":
    unittest.main()
