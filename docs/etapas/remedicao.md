# Etapa `remedicao`

**Objetivo** (`ciclo.json5`): mesmas tarefas, mesmo oráculo, execuções isoladas, sistema congelado
durante a medição.

Rodada: repete (`per_round`). Anterior: [integracao](integracao.md). Próxima: [decisao](decisao.md).

## Por que existe

- **L04** — "Não altere o sistema enquanto ele está sendo medido." Regra: "sistema congelado na
  remedição; custo sempre ao lado da qualidade."
- **L05** — isolamento por execução.
- **L07** — "Retome execuções interrompidas pelo disco; não reinicie do zero" (SKILL.md).
- **L12** — "quando o sistema tem modos, a remedição inclui o modo barato."

## Sub-etapas

| ID | ctx | O que fazer | Check | Recusa quando |
|---|---|---|---|---|
| `remedicao.1` | sub | execuções da rodada (retomar pelo disco se caírem) | `runs --min 1` | v0.3: nenhuma execução com `at` posterior a `correcao.1` e `decision` não vazia (a recusa cita `correcao.1`) |
| `remedicao.2` | main | corrigir e registrar tempo/tokens | `runs --graded` | alguma execução da rodada atual sem `quality.total` |

Os checks olham a rodada **atual** (sem `--round`). Por isso a recomendação de abrir a rodada 1 depois de
`base`: se `remedicao` acontecesse na rodada 0, as execuções de `base` já satisfariam o check.

## Comandos

```bash
ac load remedicao
# executores (prompt executor_rodada), um diretório por execução; oráculo congelado em cada saída
ac run record --config sistema --alvo <nome> --dir <dir> --grading <grading.json> --minutes M --tokens N [--decision GO --simulated]
ac run record --config <modo-barato> --alvo <nome> ...       # se o sistema tem modos (L12)
ac done remedicao
```

`--round` é opcional aqui (padrão: rodada atual).

## Exemplo real

```
$ ac done remedicao
NÃO: etapa 'remedicao' não fecha:
  remedicao.1: rodada 1: 0 execução(ões) registradas, mínimo 1 (ac.py run record ...)
  remedicao.2: rodada 1: 0 execução(ões) registradas, mínimo 1 (ac.py run record ...)
[exit 1]

$ ac run record --config sistema --alvo py-billing --dir $T/runs/r1-sis --grading $T/g-r1.json --minutes 21 --tokens 150000 --decision GO --simulated
execução registrada: rodada 1 py-billing/sistema

$ ac done remedicao
etapa 'remedicao' fechada
```

## Erros comuns

- Corrigir "só mais uma coisinha" no sistema enquanto as execuções rodam — invalida a medição (L04).
- Mudar as tarefas ou o oráculo entre rodadas — o Δ deixa de significar algo.
- Reiniciar do zero uma execução que caiu, em vez de retomá-la pelo disco (`handoff.md` do executor).
- Rodar as execuções de avaliação em paralelo quando o orçamento de uso é apertado (a campanha planejada
  em [06-exemplo-campanha.md](../06-exemplo-campanha.md) pede uma por vez).
- Registrar sem `--grading` (a linha fica sem nota para sempre — ver [base](base.md#erros-comuns)).
