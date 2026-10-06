# Etapa `base`

**Objetivo** (`ciclo.json5`): estado atual medido (e baseline sem o sistema, quando aplicável), com
`notes.md` por execução.

Rodada: 0 (não repete). Anterior: [oraculo](oraculo.md). Próxima: `ac.py round new`, depois
[diagnostico](diagnostico.md) (ver [01-maquina-de-estado.md](../01-maquina-de-estado.md#round-new-exige-rodada-terminada-e-respeita-orçamento)).

## Por que existe

- **L04** — "Não altere o sistema enquanto ele está sendo medido; e baseline sem o sistema é o único jeito
  de saber se ele vale o custo." Evidência: "o baseline sem skill entregava times bons em 7 min; a skill
  custava 4–8× e ganhava 3–4 itens de 13."
- **L05** — "Execuções paralelas que compartilham rascunho contaminam umas às outras." Regra: "cada
  execução tem diretório próprio; temporários dentro dele."
- **L12** — se o sistema tem modos, meça o modo barato também.

## Sub-etapas

| ID | ctx | O que fazer | Check | Recusa quando |
|---|---|---|---|---|
| `base.1` | sub | execuções isoladas do sistema (diretório próprio, temporários dentro dele) | `runs --round 0 --min 1` | nenhuma execução na rodada 0 |
| `base.2` | sub | baseline sem o sistema, mesma tarefa (ou motivo registrado para não ter) | `runs --round 0 --config baseline --min 1 --or-waived` | nenhuma execução `baseline` na rodada 0 e nenhuma dispensa `waivers.0.baseline` não vazia |
| `base.3` | main | corrigir com o oráculo congelado e registrar tempo/tokens | `runs --round 0 --graded` | alguma execução da rodada 0 sem `quality.total` |

## O executor de rodada

Cada execução é um subagente com o prompt `executor_rodada` (`references/prompts.json5`): usar o sistema
"exatamente como um usuário faria", numa cópia isolada (`{alvo_dir}`), sem editar o sistema, com
aprovações simuladas declaradas, lotes de no máximo `{max_paralelo}` em primeiro plano. Ele grava em
`{out_dir}`:

- `report.md` — o relatório que o sistema pede;
- `notes.md` — o que `formatos.json5` → `notes_md` exige:
  - onde as instruções do sistema estavam ambíguas ou erradas (citação);
  - cada comando que falhou: comando exato + erro literal;
  - cada contorno manual que precisou fazer (isso é defeito, mesmo que tenha dado certo);
  - desvios do executor (o que ele fez fora do roteiro e por quê);
- `timing-notes.txt` — quantos subagentes despachou;
- `handoff.md` — só se o contexto pesar, com o próximo comando.

Depois o orquestrador roda o oráculo congelado sobre a saída e registra.

## Comandos

```bash
ac load base
# ... executores rodam; oráculo gera grading.json por execução
ac run record --round 0 --config sistema  --alvo <nome> --dir <dir> --grading <grading.json> --minutes M --tokens N [--decision GO --simulated]
ac run record --round 0 --config baseline --alvo <nome> --dir <dir> --grading <grading.json> --minutes M --tokens N
#   ou, sem baseline possível:
ac run waive  --round 0 --config baseline --why "<motivo>"
ac done base --handoff "..."
ac round new
```

## Artefatos

- `rounds/0/runs.jsonl` — uma linha por execução (schema `run` de `formatos.json5`).
- `state.json`: `waivers.0.baseline` se dispensado.
- Fora da campanha: os diretórios das execuções com `report.md`, `notes.md`, `timing-notes.txt`.

## Exemplo real

```
$ ac load base
# etapa base · rodada 0
objetivo: estado atual medido (e baseline sem o sistema, quando aplicável), com notes.md por execução
parada: qualidade >= 12/13 nos 3 alvos; zero contornos manuais
orçamento: {'max_hours': 5.0, 'max_parallel': 3, 'max_rounds': 2}
[ ] base.1 (sub) execuções isoladas do sistema (diretório próprio, temporários dentro dele)
[ ] base.2 (sub) baseline sem o sistema, mesma tarefa (ou motivo registrado para não ter)
[ ] base.3 (main) corrigir com o oráculo congelado e registrar tempo/tokens
handoff anterior:
oráculo congelado; Q=13, S=40

$ ac run record --round 0 --config sistema --alvo py-billing --dir $T/runs/r0-sis --grading $T/g-sis.json --minutes 33 --tokens 269008 --decision GO --simulated
execução registrada: rodada 0 py-billing/sistema

$ ac run record --round 0 --config baseline --alvo py-billing --dir $T/runs/r0-base --grading $T/g-base.json --minutes 7 --tokens 60000
execução registrada: rodada 0 py-billing/baseline

$ ac done base --handoff "rodada 0: Q 9/13 sistema, 10/13 baseline"
etapa 'base' fechada

$ ac round new
rodada 1 aberta — comece por `ac.py load diagnostico`
```

Recusa típica (outra campanha da demonstração):

```
$ ac done base
NÃO: etapa 'base' não fecha:
  base.2: rodada 0: 0 execução(ões) 'baseline' registradas, mínimo 1 (ac.py run record ...)
  base.3: execuções sem nota de qualidade: ['py-billing/sistema']
[exit 1]
```

## Erros comuns

- **Registrar uma execução sem `--grading`.** `run record` só acrescenta; a linha sem nota fica para
  sempre em `runs.jsonl` e `base.3` (`--graded`) nunca mais passa nessa rodada. Na demonstração, mesmo
  depois de registrar a mesma execução com nota, `base` continuou recusando. Corrija o oráculo e registre
  com `--grading` desde a primeira vez. Ver [07-limites.md](../07-limites.md).
- **`run waive` sem `--why`.** Imprime "dispensa registrada" mas grava texto vazio, que o check
  `--or-waived` não aceita.
- Executores paralelos compartilhando um scratchpad (L05).
- Rodar o baseline de novo quando já existe um medido com o mesmo oráculo — pode-se reaproveitar e
  registrar (ou dispensar com motivo).
- Chamar `round new` antes de fechar `base`: o código deixa (na rodada 0 não há condição), mas depois o
  `load` de qualquer etapa da rodada 1 recusa com "etapa 'base' não fechou".
