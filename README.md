# Robô de Reversão 15m — Engolfo em região de topo/fundo

Setup de reversão para o gráfico de **15 minutos** (ex.: WINFUT no Profit Pro),
baseado em **candle de engolfo** como gatilho, mas **sempre condicionado à
localização**: o preço precisa estar numa região clara de topo ou de fundo.

> **Regra central:** `TOPO/FUNDO PRIMEIRO; ENGOLFO DEPOIS.`
> O engolfo confirma a entrada, mas quem autoriza o setup é a localização.

## Operacional

**Contexto obrigatório.** A operação só acontece depois que o preço chega a uma
região clara de topo ou de fundo. O engolfo é apenas o gatilho — não basta
sozinho.

- **Venda no topo:** o preço sobe, alcança/formaliza uma região de topo e surge
  um **engolfo de baixa**. Quando o candle do engolfo **fecha**, entra **vendido
  a mercado** (a entrada nunca é antecipada durante a formação do candle).
- **Compra no fundo:** o preço cai, alcança/formaliza uma região de fundo e
  surge um **engolfo de alta**. No fechamento do candle, entra **comprado a
  mercado**.

**Gestão fixa.** Stop Loss de **360 pontos** e Take Profit de **650 pontos**.

**Segunda oportunidade.** Se a primeira entrada não for feita, é permitido
entrar no **segundo** candle de engolfo na **mesma região**, desde que o preço
ainda não tenha se deslocado demais — se já andou **~500 pontos ou mais** a
partir da região do sinal, **não entra**.

**Veto principal.** Não operar engolfo que apareça **no meio do caminho**.
Exemplo: o mercado cai, forma um fundo, sobe sem engolfo e, durante essa pequena
subida, aparece um engolfo de baixa — **não vende**, porque o engolfo não surgiu
num topo válido.

## Como as regras viram código

| Regra do operacional | Implementação |
| --- | --- |
| Engolfo de baixa/alta | `is_bearish_engulfing` / `is_bullish_engulfing` (corpo engolfando o corpo anterior) |
| Região de topo/fundo | `is_swing_top` / `is_swing_bottom` — o candle precisa marcar a maior máxima / menor mínima dos últimos `lookback` candles |
| Veto do "meio do caminho" | consequência direta do teste de topo/fundo: um engolfo fora do extremo do período não é sinal |
| Não entrar se andou ~500 pts | filtro de distância `dist_max_regiao` em `generate_signal` |
| Segunda oportunidade | `max_entradas_regiao` (padrão 2) e controle de região no backtester |
| SL 360 / TP 650 | `STOP_LOSS_PONTOS` / `TAKE_PROFIT_PONTOS` em `robo/backtest.py` |

### Definição de engolfo usada

Engolfo de **baixa** no candle `i`:

- `candles[i-1]` é de alta e `candles[i]` é de baixa;
- `open[i] >= close[i-1]` **e** `close[i] <= open[i-1]` (o corpo de `i` engolfa o
  corpo de `i-1`).

Engolfo de **alta** é o espelho.

### Região (topo/fundo)

O candle de engolfo só vale se marcar o extremo do período: para venda, sua
máxima tem de ser a maior das últimas `lookback` barras (topo); para compra, sua
mínima tem de ser a menor (fundo). É essa exigência que **veta o engolfo no meio
do caminho** — um engolfo numa perna intermediária não é o extremo do período.

## Estrutura do repositório

```
robo/
  strategy.py     # detecção de engolfo, topo/fundo, veto e geração de sinal
  backtest.py     # backtester com SL 360 / TP 650 e regra de região
tests/
  test_strategy.py
estrategia_ntsl/
  reversao_15m_engolfo.src   # estratégia em NTSL para o Profit Pro
exemplo.py        # exemplo mínimo de uso
```

## Uso (Python)

```python
from robo import Candle, StrategyParams, backtest

candles = [Candle(open=..., high=..., low=..., close=...), ...]
resultado = backtest(candles, StrategyParams(lookback=20))
print(resultado.summary())
```

Rodar o exemplo e os testes:

```bash
python3 exemplo.py
python3 -m unittest discover -s tests -v
```

Não há dependências externas — apenas a biblioteca padrão do Python 3.

## Parâmetros (`StrategyParams`)

| Parâmetro | Padrão | Descrição |
| --- | --- | --- |
| `lookback` | 20 | candles usados para caracterizar a região de topo/fundo |
| `dist_max_regiao` | 500 | distância máxima (pontos) do preço de entrada até o extremo da região |
| `max_entradas_regiao` | 2 | entradas permitidas na mesma região (1 = só a primeira; 2 = com segunda oportunidade) |
| `tol_regiao` | 50 | tolerância (pontos) para considerar dois extremos como a mesma região |

## Deploy no Profit Pro (NTSL)

O arquivo `estrategia_ntsl/reversao_15m_engolfo.src` traz a mesma lógica escrita
em **NTSL** (Nelogica Trading System Language), para colar em uma estratégia do
Profit Pro no tempo gráfico de 15 minutos. Os `input` permitem ajustar
contratos, stops e `Lookback`/`DistMaxRegiao`.

> Os nomes de procedimentos de ordem/posição (`BuyAtMarket`,
> `SellShortAtMarket`, `SellToCoverAtMarket`, `BuyToCoverAtMarket`, `IsBought`,
> `IsSold`, `BuyPrice`, `SellPrice`) seguem a API padrão de estratégias
> automatizadas do NTSL — confira/ajuste conforme a versão do seu Profit antes
> de operar em conta real.

## Aviso

Material de estudo. Backtest não garante resultado futuro; teste em conta
simulada antes de qualquer uso em conta real.
