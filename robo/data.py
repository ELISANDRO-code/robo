"""Leitura de dados históricos em CSV (exportação do Profit Pro e formatos afins).

O Profit exporta algo como:

    Data;Hora;Abertura;Máxima;Mínima;Fechamento;Volume
    19/08/2026;09:00;170200;170450;170050;170300;1234

O parser é tolerante: detecta o separador (``;``, ``,`` ou tab), aceita
decimal com vírgula, encontra as colunas pelo nome do cabeçalho (com ou sem
acento, em português ou inglês) e usa a data como ``session`` — o que ativa a
âncora automática da linha de 0% no fechamento do pregão anterior.
"""

from __future__ import annotations

import csv
import io
import unicodedata
from typing import List, Optional, Sequence

from .strategy import Candle

# nomes aceitos para cada coluna (comparados sem acento, em minúsculas)
_COL_ALIASES = {
    "date": {"data", "date", "dia"},
    "time": {"hora", "time", "horario"},
    "open": {"abertura", "open", "abe"},
    "high": {"maxima", "high", "max"},
    "low": {"minima", "low", "min"},
    "close": {"fechamento", "close", "fech", "ultimo"},
}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s.strip().lower()


def _detect_delimiter(sample: str) -> str:
    counts = {d: sample.count(d) for d in (";", ",", "\t")}
    return max(counts, key=counts.get)


def _to_float(raw: str) -> float:
    raw = raw.strip()
    if "," in raw and "." in raw:
        # 1.234.567,89 -> ponto é separador de milhar
        raw = raw.replace(".", "").replace(",", ".")
    elif "," in raw:
        raw = raw.replace(",", ".")
    return float(raw)


def load_csv(path: str, encoding: str = "utf-8-sig") -> List[Candle]:
    """Carrega um CSV de candles e retorna a lista de :class:`Candle`.

    A coluna de data vira ``session`` (pregão) e data+hora vira ``time``.
    Levanta ``ValueError`` se as colunas OHLC não forem encontradas.
    """
    with open(path, "r", encoding=encoding, errors="replace") as fh:
        content = fh.read()
    return parse_csv(content)


def parse_csv(content: str) -> List[Candle]:
    """Versão de :func:`load_csv` que recebe o conteúdo já lido."""
    lines = [ln for ln in content.splitlines() if ln.strip()]
    if not lines:
        return []

    delim = _detect_delimiter(lines[0])
    reader = csv.reader(io.StringIO("\n".join(lines)), delimiter=delim)
    rows = list(reader)

    header = [_norm(c) for c in rows[0]]
    col: dict = {}
    for key, aliases in _COL_ALIASES.items():
        for idx, name in enumerate(header):
            if name in aliases:
                col[key] = idx
                break

    missing = [k for k in ("open", "high", "low", "close") if k not in col]
    if missing:
        raise ValueError(
            f"Colunas não encontradas no CSV: {missing}. Cabeçalho lido: {rows[0]}"
        )

    candles: List[Candle] = []
    for row in rows[1:]:
        if len(row) < len(header):
            continue
        try:
            o = _to_float(row[col["open"]])
            h = _to_float(row[col["high"]])
            low = _to_float(row[col["low"]])
            c = _to_float(row[col["close"]])
        except ValueError:
            continue  # linha de rodapé/sujeira
        date = row[col["date"]].strip() if "date" in col else None
        time = row[col["time"]].strip() if "time" in col else None
        candles.append(
            Candle(
                open=o,
                high=h,
                low=low,
                close=c,
                time=f"{date} {time}" if date and time else (time or date),
                session=date,
            )
        )

    # Profit às vezes exporta do mais recente para o mais antigo; ordena se
    # der para comparar (mesmo formato de data/hora em todas as linhas).
    if len(candles) >= 2 and candles[0].time and candles[-1].time:
        if _sort_key(candles[0]) > _sort_key(candles[-1]):
            candles.reverse()
    return candles


def _sort_key(c: Candle):
    # converte "DD/MM/AAAA HH:MM" (ou ISO) numa chave ordenável
    t = c.time or ""
    parts = t.split()
    date, time = (parts + [""])[:2]
    if "/" in date:
        d = date.split("/")
        if len(d) == 3:
            date = f"{d[2]}-{d[1]}-{d[0]}"
    return (date, time)
