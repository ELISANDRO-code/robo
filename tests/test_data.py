"""Testes do leitor de CSV (formato Profit Pro)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from robo.data import parse_csv  # noqa: E402


class TestParseCsv(unittest.TestCase):
    def test_formato_profit_ponto_e_virgula(self):
        content = (
            "Data;Hora;Abertura;Máxima;Mínima;Fechamento;Volume\n"
            "19/08/2026;09:00;170200;170450;170050;170300;123\n"
            "19/08/2026;09:15;170300;170500;170250;170480;456\n"
            "20/08/2026;09:00;170480;170700;170400;170650;789\n"
        )
        candles = parse_csv(content)
        self.assertEqual(len(candles), 3)
        self.assertEqual(candles[0].open, 170200)
        self.assertEqual(candles[0].session, "19/08/2026")
        self.assertEqual(candles[2].session, "20/08/2026")

    def test_decimal_com_virgula(self):
        content = (
            "Data;Hora;Abertura;Maxima;Minima;Fechamento\n"
            "19/08/2026;09:00;170200,5;170450,0;170050,5;170300,0\n"
        )
        candles = parse_csv(content)
        self.assertEqual(candles[0].open, 170200.5)

    def test_ordena_quando_invertido(self):
        content = (
            "Data;Hora;Abertura;Maxima;Minima;Fechamento\n"
            "20/08/2026;09:15;2;3;1;2\n"
            "20/08/2026;09:00;1;2;1;2\n"
            "19/08/2026;17:45;1;2;1;1\n"
        )
        candles = parse_csv(content)
        self.assertEqual(candles[0].session, "19/08/2026")
        self.assertEqual(candles[-1].time, "20/08/2026 09:15")

    def test_ignora_linha_suja(self):
        content = (
            "Data;Hora;Abertura;Maxima;Minima;Fechamento\n"
            "19/08/2026;09:00;100;110;90;105\n"
            "Total;;;;;\n"
        )
        candles = parse_csv(content)
        self.assertEqual(len(candles), 1)

    def test_cabecalho_ingles_virgula(self):
        content = (
            "Date,Time,Open,High,Low,Close\n"
            "2026-08-19,09:00,100,110,90,105\n"
        )
        candles = parse_csv(content)
        self.assertEqual(len(candles), 1)
        self.assertEqual(candles[0].high, 110)

    def test_colunas_faltando(self):
        with self.assertRaises(ValueError):
            parse_csv("Data;Hora;Abertura\n19/08/2026;09:00;100\n")


if __name__ == "__main__":
    unittest.main()
