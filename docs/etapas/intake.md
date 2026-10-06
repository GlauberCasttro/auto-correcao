# Etapa `intake`

**Objetivo** (`ciclo.json5`): alvo, problema, escopo de escrita, orçamento e critério de parada numérico
registrados.

Rodada: 0 (não repete). Anterior: nenhuma. Próxima: [oraculo](oraculo.md).

## Por que existe

- **L14** — "Sem critério de parada fixado antes, o laço vira 'mais uma rodada' indefinidamente."
  Evidência: "o founder perguntou se seria a última; o critério foi escrito só na iteração 4."
- O SKILL.md: "Sem critério de parada, não comece: pergunte." Mesmo que o usuário diga "pode rodar
  quantas rodadas quiser", fixe orçamento e critério com ele (eval 4 da skill, `escalar-sem-progresso`).

## Sub-etapas

| ID | ctx | O que fazer | Check | Recusa quando |
|---|---|---|---|---|
| `intake.1` | main | registrar alvo, problema (relatado ou a medir) e escopo de escrita | `require target scope` | falta `target` ou `scope` |
| `intake.2` | main | orçamento: rodadas máx., horas de parede, execuções paralelas máx. | `require budget` | nenhuma das três flags de orçamento foi passada |
| `intake.3` | user | critério de parada em números, aceito pelo usuário | `require stop gate:stop` | falta `stop` ou o portão `stop` não está aprovado |

`problem` é gravado mas não verificado. `require budget` passa com **qualquer** uma das três chaves.

## Comandos

```bash
ac init --target <alvo> --scope '<glob>' [--scope ...] --problem "<texto>" \
        --stop "<critério em números>" --max-rounds N --max-hours H --max-parallel N
ac load intake
ac gate stop --by <humano> --decision approve [--note "..."]
ac done intake --handoff "<resumo para a próxima etapa>"
```

## Artefatos

`state.json`: `target`, `scope`, `problem`, `stop`, `budget`, `gates.stop`. Com `--handoff`:
`handoff-intake.txt`.

## Exemplo real

```
$ ac init --target $T/alvo --scope 'src/**' --scope 'docs/**' --problem "metade dos evals falha" --stop "qualidade >= 12/13 nos 3 alvos; zero contornos manuais" --max-rounds 2 --max-hours 5 --max-parallel 3
campanha em $T/campanha/.auto-correcao (rodada 0, etapa intake)

$ ac load intake
# etapa intake · rodada 0
objetivo: alvo, problema, escopo de escrita, orçamento e critério de parada numérico registrados
parada: qualidade >= 12/13 nos 3 alvos; zero contornos manuais
orçamento: {'max_hours': 5.0, 'max_parallel': 3, 'max_rounds': 2}
[ ] intake.1 (main) registrar alvo, problema (relatado ou a medir) e escopo de escrita
[ ] intake.2 (main) orçamento: rodadas máx., horas de parede, execuções paralelas máx.
[ ] intake.3 (user) critério de parada em números, aceito pelo usuário

$ ac done intake
NÃO: etapa 'intake' não fecha:
  intake.3: faltando: portão 'stop' aprovado (ac.py gate stop --by <humano> --decision approve)
[exit 1]

$ ac gate stop --by founder --decision approve --note "critério aceito"
portão stop: approve por founder

$ ac done intake --handoff "alvo e critério fixados; oráculo = evals/grader.py"
etapa 'intake' fechada
```

## Como escrever um bom critério de parada

Números, não adjetivos (SKILL.md, relatório). Inclua a métrica de qualidade, a comparação com o baseline
e o que mais for inegociável. Exemplo da campanha planejada ([06-exemplo-campanha.md](../06-exemplo-campanha.md)):
"Rodada --fast nos 3 alvos: ≥2/3 GO; ZERO contornos manuais; [Q] ≥ baseline nos 3; todas as suítes verdes
em python3 (3.13) e /usr/bin/python3 (3.9.6). Sem progresso em 2 rodadas → escalar ao usuário."

## Erros comuns

- Começar sem critério ("melhora ele sozinho") — pergunte e proponha como medir (eval 2 da skill).
- Aprovar o portão `stop` em nome do usuário sem dizer — se for simulado, use `--simulated` e diga.
- Colocar a campanha (`--work`) dentro do alvo — ela deve ficar fora do alvo medido.
- Escopo largo demais (`--scope '**'`): o escopo é a fronteira de escrita das frentes.
- Esquecer que `--max-rounds` não conta a rodada 0 (com 2, as rodadas 1 e 2 são de correção).
