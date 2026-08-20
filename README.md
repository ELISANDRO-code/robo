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

> **Análise profunda** (engenharia reversa das linhas de %, matemática do
> 360/650, limitações do modelo): veja [`ANALISE.md`](ANALISE.md).

## Como as regras viram código

| Regra do operacional | Implementação |
| --- | --- |
| Engolfo de baixa/alta | `is_bearish_engulfing` / `is_bullish_engulfing` (corpo engolfando o corpo anterior) |
| Região de topo/fundo | **dois critérios** (ver abaixo): swing recente e/ou linhas de % |
| Veto do "meio do caminho" | consequência direta do critério de região: um engolfo fora de um topo/fundo recente não é sinal |
| Não entrar se andou ~500 pts | filtro de distância `dist_max_regiao` em `generate_signal` |
| Segunda oportunidade | `max_entradas_regiao` (padrão 2) e controle de região no backtester |
| SL 360 / TP 650 | `STOP_LOSS_PONTOS` / `TAKE_PROFIT_PONTOS` em `robo/backtest.py` |

### Os dois critérios de região (`region_mode`)

| Modo | Topo/fundo válido quando… |
| --- | --- |
| `swing` (padrão) | o **extremo recente** das últimas `lookback` barras acabou de se formar (nos últimos `recencia_regiao` candles) |
| `percent` | a máxima/mínima alcançou a **linha de ±`percent_entrada`%** sobre `ref_price` (a linha de 0% do gráfico) |
| `both` | **os dois** ao mesmo tempo (mais seletivo) |
| `either` | **qualquer um** dos dois |

As linhas de % reproduzem as "Linhas Milionárias" do Profit: `ref_price` é a linha
de 0% (ex.: 171035 no pregão da imagem), e as bandas ±0,5%/±1% saem de
`ref_price × (1 ± banda/100)`. Como a referência muda por pregão, é um parâmetro.

### Definição de engolfo usada

Engolfo de **baixa** no candle `i`:

- `candles[i-1]` é de alta e `candles[i]` é de baixa;
- `open[i] >= close[i-1]` **e** `close[i] <= open[i-1]` (o corpo de `i` engolfa o
  corpo de `i-1`).

Engolfo de **alta** é o espelho.

### Região (topo/fundo)

Pelo critério **swing**, o engolfo só vale se a região formou um **topo/fundo
recente**: o extremo das últimas `lookback` barras precisa ter ocorrido nos
últimos `recencia_regiao` candles. Não se exige que o *próprio* candle de engolfo
seja a máxima — na reversão o topo costuma ficar na barra anterior e o engolfo
fecha logo abaixo. É essa exigência de "extremo recente" que **veta o engolfo no
meio do caminho**: se o mercado caiu de um topo antigo e apenas repicou, a maior
máxima da janela ficou lá atrás (não recente) e o setup não é autorizado.

Pelo critério **percent**, a região é definida pelas linhas de porcentagem
(`ref_price` ± `percent_entrada`%). Os modos `both`/`either` combinam os dois.

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
| `lookback` | 20 | candles usados para caracterizar a região de topo/fundo (swing) |
| `recencia_regiao` | 3 | o topo/fundo precisa ter ocorrido nas últimas N barras |
| `dist_max_regiao` | 500 | distância máxima (pontos) do preço de entrada até o extremo da região |
| `max_entradas_regiao` | 2 | entradas permitidas na mesma região (1 = só a primeira; 2 = com segunda oportunidade) |
| `tol_regiao` | 50 | tolerância (pontos) para considerar dois extremos como a mesma região |
| `region_mode` | `"swing"` | `swing` / `percent` / `both` / `either` |
| `ref_price` | `None` | linha de 0% (necessária para `percent`/`both`/`either`) |
| `percent_entrada` | 0.5 | banda mínima (%) para caracterizar a região |

## Deploy no Profit Pro (NTSL)

O arquivo `estrategia_ntsl/reversao_15m_engolfo.src` traz a mesma lógica escrita
em **NTSL** (Nelogica Trading System Language), para colar em uma estratégia do
Profit Pro no tempo gráfico de 15 minutos. Os `input` permitem ajustar contratos,
stops, `Lookback`/`Recencia`/`DistMaxRegiao` e o critério de região
(`ModoRegiao`: 0=swing, 1=percent, 2=both, 3=either; com `RefPreco` e
`BandaEntrada` para as linhas de %).

> Os nomes de procedimentos de ordem/posição (`BuyAtMarket`,
> `SellShortAtMarket`, `SellToCoverAtMarket`, `BuyToCoverAtMarket`, `IsBought`,
> `IsSold`, `BuyPrice`, `SellPrice`) seguem a API padrão de estratégias
> automatizadas do NTSL — confira/ajuste conforme a versão do seu Profit antes
> de operar em conta real.

## Aviso

Material de estudo. Backtest não garante resultado futuro; teste em conta
simulada antes de qualquer uso em conta real.
