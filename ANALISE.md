# Análise profunda — Reversão 15m (Engolfo em topo/fundo)

Documento de análise do setup: engenharia reversa do gráfico, decomposição das
regras em código, matemática da gestão e limitações do modelo. Complementa o
`README.md` (que descreve o operacional) com o *porquê* de cada decisão.

---

## 1. Sumário executivo

- O setup é **contra-tendência** (reversão): vende topo, compra fundo. O gatilho
  é o **engolfo**, mas o que autoriza é a **localização** (topo/fundo).
- Implementei **dois critérios de região**, combináveis: **(A) swing** — extremo
  recente das últimas *N* barras; **(B) percent** — as linhas de porcentagem do
  gráfico. Modos: `swing`, `percent`, `both` (os dois) e `either` (qualquer um).
- Gestão fixa **SL 360 / TP 650** dá **R:R ≈ 1,81:1** e exige **win-rate ≥ 35,6%**
  para empatar (antes de custos). Esse é o número-chave do setup.
- Há uma **tensão de projeto** entre o stop fixo (360) e o tamanho da região de
  topo/fundo — detalhada na seção 7. Vale a pena olhar antes de operar.

---

## 2. Engenharia reversa das linhas de % (imagem)

Lendo a linha de **0% em 171.035** e aplicando as bandas, os valores batem
**exatamente** com os rótulos do eixo direito da sua imagem:

| Banda | Cálculo | Valor | Confere na imagem |
|------:|---------|------:|:-----------------:|
| +1,0% | 171035 × 1,010 | **172.745** | ✅ |
| +0,5% | 171035 × 1,005 | **171.890** | ✅ |
|  0,0% | referência     | **171.035** | ✅ |
| −0,5% | 171035 × 0,995 | **170.180** | ✅ |
| −1,0% | 171035 × 0,990 | **169.325** | ✅ |

**Conclusão:** as "Linhas Milionárias" do gráfico são bandas de ±0,5% e ±1% sobre
uma **referência de 0%** (171.035 no pregão de 20/ago). No exemplo, o topo se
formou **na região de +1%** — é isso que o critério (B) captura. Como a referência
muda a cada pregão, ela é um **parâmetro** (`ref_price`), não uma constante.

> Observação: a imagem não revela **qual** é a âncora do 0% (fechamento anterior,
> preço de ajuste, abertura do dia ou preço manual). Isso não muda a lógica —
> muda apenas de onde você lê o número para alimentar `ref_price`.

---

## 3. Decomposição: regra → código

| Regra do operacional | Onde está | Como |
|---|---|---|
| Engolfo de baixa/alta | `is_bearish_engulfing` / `is_bullish_engulfing` | corpo engolfando o corpo anterior |
| Região por swing (A) | `is_swing_top` / `is_swing_bottom` | extremo **recente** das últimas `lookback` barras |
| Região por % (B) | `in_top_zone_percent` / `in_bottom_zone_percent` | máxima/mínima alcançou a linha ±`percent_entrada`% |
| Combinar A e B | `_combine` + `region_mode` | `swing` / `percent` / `both` / `either` |
| Veto "no meio do caminho" | consequência de (A) | se o extremo não é recente, não há setup |
| Não entrar se andou ~500 pts | filtro `dist_max_regiao` em `generate_signal` | `região − entrada ≤ 500` |
| Segunda oportunidade | `max_entradas_regiao` + controle de região no backtester | até 2 entradas por região |
| SL 360 / TP 650, a mercado no fechamento | `robo/backtest.py` | saída avaliada candle a candle |

---

## 4. Definição de engolfo — a escolha e os casos-limite

Usei **engolfo de corpo** (o corpo do candle atual engolfa o corpo do anterior),
não o engolfo de *sombras* (high/low). Definição para **baixa** no candle `i`:

```
prev de alta  e  cur de baixa
open[i]  >= close[i-1]      (abre no topo do corpo anterior ou acima)
close[i] <= open[i-1]       (fecha na base do corpo anterior ou abaixo)
```

**Por que corpo e não sombras?** O operacional fala em "candle de baixa que
engolfa" — o corpo é o que o trader enxerga como força vendedora. Exigir engolfo
de sombras é mais raro e atrasa/reduz sinais. É uma escolha; dá para trocar.

**Casos-limite tratados:**
- *Doji anterior* (`close[1] == open[1]`): não é "de alta" nem "de baixa" →
  não forma engolfo. Correto (não há corpo para engolfar).
- *Empates de fronteira* (`open[i] == close[i-1]`): considerados válidos (`>=`/`<=`),
  como é comum na literatura de candles.
- *Gap*: se `cur` abre com gap acima e fecha abaixo do corpo anterior, ainda conta
  como engolfo — o gap reforça a reversão.

**Limitação conhecida:** a definição não olha o **tamanho** do corpo. Um engolfo
"técnico" porém minúsculo conta igual a um engolfo dominante. Se quiser, dá para
exigir corpo mínimo (em pontos ou em % do ATR).

---

## 5. Região: swing *recente* vs. linhas de %

### Por que "recente" e não "o engolfo é o extremo"

A primeira versão exigia que **o próprio candle de engolfo** fosse a maior máxima
da janela. Isso está **errado na prática**: no engolfo de reversão o topo costuma
ficar **na barra anterior** e o candle de engolfo fecha logo abaixo (foi o que
aconteceu no seu candle 14). A regra corrigida é:

> O extremo das últimas `lookback` barras precisa ter ocorrido nos últimos
> `recencia` candles (padrão 3). Ou seja, **o topo acabou de se formar**.

No NTSL isso vira uma expressão elegante: `Highest(High, Recencia) >= Highest(High, Lookback)`.

### Como isso implementa o veto

No exemplo de veto (cai de um topo antigo, faz fundo, **repica** e aparece engolfo
de baixa no meio da subida): a maior máxima da janela é o **topo antigo**, muitas
barras atrás → **não é recente** → sem setup. É exatamente o comportamento pedido,
e está coberto por teste (`test_veto_engolfo_no_meio_do_caminho`).

### Critério (B) — linhas de %

Topo por % = a máxima recente alcançou a linha de +`percent_entrada`%
(fundo = a mínima alcançou −`percent_entrada`%). No `both`, exige-se **swing E %**
(mais seletivo, menos sinais); no `either`, **basta um**. Sem `ref_price`, os
modos que dependem de % caem para swing (degradação segura).

---

## 6. Filtro de distância e segunda oportunidade

- **Distância (`dist_max_regiao`, 500 pts):** não entra se o preço de entrada já
  está a mais de ~500 pontos do extremo da região. Traduz "se já andou ~500
  pontos ou mais a partir da região, não entra". *Efeito colateral útil:* também
  barra engolfos gigantes cujo fechamento ficou longe demais do topo.
- **Segunda oportunidade (`max_entradas_regiao`, 2):** o backtester agrupa sinais
  por região (com tolerância `tol_regiao`) e permite até 2 entradas na mesma
  região; ao surgir um novo extremo, o contador zera. Assim o "segundo engolfo na
  mesma região" é aceito, mas não vira uma metralhadora de entradas.

---

## 7. Matemática da gestão (360 / 650) — a parte que decide o resultado

| Métrica | Valor |
|---|---|
| Risco : Retorno | **650 / 360 = 1,806 : 1** |
| Win-rate de break-even | **35,64%** |
| Expectativa @ 40% de acerto | **+44 pts/trade** |
| Expectativa @ 45% de acerto | **+94,5 pts/trade** |
| Expectativa @ 50% de acerto | **+145 pts/trade** |

Fórmula: `expectativa = p·650 − (1−p)·360`. Break-even quando `p = 360/(650+360)`.

**Leitura prática:** por ser um alvo maior que o stop, o setup **não precisa
acertar a maioria** — basta passar de ~35,6% para ficar positivo (antes de
custos). Com custos/derrapagem no WIN (corretagem + spread + emolumentos), suba
esse piso para a casa dos **~38–40%** por segurança.

### A tensão stop fixo × tamanho da região (importante)

Numa reversão de topo, a entrada é no **fechamento do engolfo**, e o **topo real**
está um pouco **acima**. O stop de 360 fica em `entrada + 360`. Se o topo estiver a,
digamos, 450 pontos acima da entrada, o **stop dispara ANTES** de o preço sequer
retestar o topo — você é estopado dentro do ruído da própria região. Dois efeitos:

1. Em topos "largos" (região de +1% após uma pernada), 360 pontos pode ser **apertado**.
2. O filtro de distância (500) e o stop (360) interagem: entradas onde
   `topo − entrada` fica entre 360 e 500 já **nascem** com o topo acima do stop.

**Sugestão de estudo:** comparar o stop fixo (360) com um stop **estrutural**
(acima do topo/abaixo do fundo + folga), mantendo o alvo em 650 ou usando alvo por
múltiplo de risco. O código facilita isso: `stop_loss`/`take_profit` são
parâmetros de `backtest()`.

---

## 8. Limitações do modelo e do backtest (honestidade)

- **Stop vs. alvo no mesmo candle:** quando um candle toca os dois, assumo **stop**
  (conservador). Sem dados de tick não dá para saber o que veio primeiro — isso
  **subestima** ligeiramente o resultado real.
- **Sem custos:** o backtest é bruto (sem corretagem, emolumentos, derrapagem).
  No WIN isso não é desprezível em alta frequência de trades.
- **Execução a mercado idealizada:** entra no `close` exato do engolfo; na prática
  há derrapagem, sobretudo em candles de reversão volumosos.
- **`ref_price` por pregão:** o critério (B) usa uma referência única; para uma
  série multi-dia é preciso alimentar a referência de cada dia (hoje é um
  parâmetro global). Estrutura pronta para estender.
- **Gap e leilão:** aberturas em leilão/gap podem furar stop/alvo além do preço
  teórico — não modelado.
- **NTSL não compilado aqui:** a lógica está validada em Python (17 testes); os
  nomes de ordem/posição do `.src` seguem a API padrão do NTSL e devem ser
  conferidos na sua versão do Profit.
- **Amostra:** os números da seção 7 são *cenários*, não um backtest histórico —
  rode com dados reais para estimar o win-rate verdadeiro do setup.

---

## 9. Recomendações e próximos passos

1. **Escolher o modo de região.** O seu exemplo topou na linha de +1%, o que
   sugere `percent` ou `both`. Comece com `both` (mais seletivo) e compare a
   frequência/qualidade de sinais com `swing`.
2. **Definir a âncora do 0%** (fechamento anterior? ajuste? abertura?) para
   alimentar `ref_price` de forma consistente, dia a dia.
3. **Rodar com dados históricos reais** de 15m do WIN e medir win-rate,
   expectativa e drawdown — comparando `swing` × `percent` × `both`.
4. **Testar stop estrutural** vs. 360 fixo (seção 7).
5. **(Opcional) corpo mínimo do engolfo** para filtrar gatilhos fracos.

Todos esses pontos são parâmetros/estruturas já presentes — não exigem reescrever
a lógica, apenas configurar e medir.
