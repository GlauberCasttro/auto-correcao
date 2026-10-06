# Etapa `decisao`

**Objetivo** (`ciclo.json5`): parar | continuar | escalar, decidido contra o critério de parada.

Rodada: repete (`per_round`). Anterior: [remedicao](remedicao.md). Próxima: `ac.py round new`
(continuar) ou fim da campanha (parar/escalar).

## Por que existe

- **L14** — sem critério fixado antes, o laço vira "mais uma rodada".
- **L11** — "O mesmo estado tem de dar o mesmo veredito em qualquer alvo." Regra: "regra de decisão
  escrita e testada com o caso de borda."
- **L13** — "veredito traz 'GO (simulado)' quando aplicável."
- **L02/L04** — relatório em duas colunas (qualidade × estrutura) e custo ao lado.

## Sub-etapas

| ID | ctx | O que fazer | Check | Recusa quando |
|---|---|---|---|---|
| `decisao.1` | main | comparar com a rodada anterior e o critério | `require decision` | chave `decision` ausente |
| `decisao.2` | main | relatório curto ao usuário | `require report` | chave `report` ausente |

`decision` e `report` são texto livre gravado com `set`; o script não valida o valor. `round new` apaga os
dois.

**v0.4:** `done decisao` também exige um `frase-conferida` no ledger posterior a toda aprovação não
simulada. Antes de fechar, peça ao founder que rode no terminal dele `ac.py --work <campanha> frase conferir`.
O comando recalcula a tag de cada aprovação e lista as forjas. Você nunca roda esse comando nem pede a frase.

## As três saídas

```
                       results compare + critério de parada
                                     │
          ┌──────────────────────────┼───────────────────────────┐
          ▼                          ▼                           ▼
       PARAR                    CONTINUAR                    ESCALAR
  critério cumprido      orçamento permite E          sem progresso em 2 rodadas
                         houve progresso medido       OU orçamento esgotado
          │                          │                           │
  congelar, tag,            ac.py round new             documentar os limites,
  relatório                 (recusa se a rodada         devolver a decisão
  (commit/tag = portão)     não terminou ou se          ao usuário
                            max_rounds estourou)
```

"Nunca rode 'mais uma' às cegas." O "2 rodadas sem progresso" vem do SKILL.md e de
`limits.escalate_after_rounds_without_progress: 2`, mas o script **não** o aplica: é você que compara os
Δ do `results compare`. O único bloqueio mecânico é `max_rounds` no `round new`.

## Relatório ao usuário (SKILL.md)

A cada rodada, curto:
- decisão numa linha;
- tabela qualidade × estrutura × custo, com baseline ao lado;
- o que o oráculo pode estar favorecendo (diga, mesmo que contra o sistema);
- defeitos da próxima rodada por prioridade;
- o que precisa de decisão dele.

Números, não adjetivos. Diga quando uma aprovação foi simulada.

## Comandos

```bash
ac load decisao
ac results compare
ac set decision "<parar|continuar|escalar — motivo>"
ac set report "<relatório curto ou caminho dele>"
ac done decisao
ac round new          # só se continuar
```

## Exemplo real

```
$ ac load decisao
# etapa decisao · rodada 1
objetivo: parar | continuar | escalar, decidido contra o critério de parada
parada: qualidade >= 12/13 nos 3 alvos; zero contornos manuais
orçamento: {'max_hours': 5.0, 'max_parallel': 3, 'max_rounds': 2}
[ ] decisao.1 (main) comparar com a rodada anterior e o critério
[ ] decisao.2 (main) relatório curto ao usuário

$ ac results compare
| rodada | alvo | config | qualidade | estrutura | decisão | tokens | min |
|---|---|---|---|---|---|---|---|
| 0 | py-billing | sistema | 9/13 | 22/40 | GO (simulado) | 269008 | 33.0 |
| 0 | py-billing | baseline | 10/13 | 0/40 | — | 60000 | 7.0 |
| 1 | py-billing | sistema | 11/13 | 29/40 | GO (simulado) | 150000 | 21.0 |
quality: rodada 1 = 0.85 (anterior 0.69, Δ +0.15)
structure: rodada 1 = 0.72 (anterior 0.55, Δ +0.17)
parada: qualidade >= 12/13 nos 3 alvos; zero contornos manuais

$ ac done decisao
NÃO: etapa 'decisao' não fecha:
  decisao.1: faltando: decision
  decisao.2: faltando: report
[exit 1]

$ ac set decision continuar
ok: decision
$ ac set report "ver tabela"
ok: report
$ ac done decisao
etapa 'decisao' fechada

$ ac round new
rodada 2 aberta — comece por `ac.py load diagnostico`
```

E na rodada 2, com `--max-rounds 2`, depois de fechar `decisao`:

```
$ ac round new
NÃO: orçamento: máximo de 2 rodadas atingido — escale ao usuário
[exit 1]
```

Leitura desse exemplo: na rodada 1 a qualidade passou de 9/13 (0.69) para 11/13 (0.85) — progresso
medido, critério (≥12/13) não cumprido, orçamento permite → **continuar**. Mas a qualidade do sistema na
rodada 0 (9/13) estava **abaixo** do baseline (10/13): é isso que o relatório deve dizer, mesmo contra o
sistema.

## Erros comuns

- Decidir pelo agregado em vez da coluna de qualidade (L02).
- Ignorar o baseline ao lado ("o sistema melhorou" — mas ainda perde para o modelo sozinho?).
- Ler `GO (simulado)` como aprovado (L13).
- "Mais uma rodada" sem progresso medido — escale.
- Esquecer que `results compare` faz a média de todas as configs não-baseline juntas (ex.: `sistema` e
  um modo barato); para decidir, olhe as linhas da tabela, não só a média.
