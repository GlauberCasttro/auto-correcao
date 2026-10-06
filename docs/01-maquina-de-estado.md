# 01 — Máquina de estado

A fonte única das etapas é `references/ciclo.json5`; o `ac.py` lê esse arquivo a cada comando
(`load`, `check`, `done`, `status`, `round new`). Mudar uma etapa ou um check é mudar esse arquivo.

## Etapas e sub-etapas

`order` (9 etapas) e `per_round` (as 6 que repetem a cada rodada):

```
order:      intake → oraculo → base → diagnostico → plano → correcao → integracao → remedicao → decisao
per_round:                            └──────────────────────── repetem por rodada ───────────────────┘
```

As **seis** últimas etapas (`per_round` em `ciclo.json5`, de `diagnostico` a `decisao`) repetem a cada rodada.

Cada sub-etapa tem `id`, `do` (o que fazer), `ctx` (quem faz) e `check` (o que prova o efeito):

| `ctx` | Quem executa |
|---|---|
| `main` | o orquestrador (a sessão principal) |
| `sub` | um subagente — protege a janela de contexto do orquestrador |
| `user` | portão humano |

```
intake ─────────── intake.1 (main)   require target scope
                   intake.2 (main)   require budget
                   intake.3 (user)   require stop gate:stop
oraculo ────────── oraculo.1 (main)  require oracle.command
                   oraculo.2 (sub)   calibration
                   oraculo.3 (main)  require oracle.split
                   oraculo.4 (main)  oracle verify
base ───────────── base.1 (sub)      runs --round 0 --min 1
                   base.2 (sub)      runs --round 0 --config baseline --min 1 --or-waived
                   base.3 (main)     runs --round 0 --graded
diagnostico ────── diagnostico.1 (main)  defects --min 1 --evidence
                   diagnostico.2 (main)  defects --classified
plano ──────────── plano.1 (main)    plan check
                   plano.2 (user)    plan gates
correcao ───────── correcao.1 (sub)  fronts --reported
integracao ─────── integracao.1 (main)  require integration.tests_green
                   integracao.2 (main)  oracle verify
                   integracao.3 (user)  gate-ok commit
remedicao ──────── remedicao.1 (sub) runs --min 1
                   remedicao.2 (main) runs --graded
decisao ────────── decisao.1 (main)  require decision
                   decisao.2 (main)  require report
```

Detalhe de cada uma em [etapas/](etapas/).

## Os checks (o que cada um recusa)

| Check | Função | Recusa quando |
|---|---|---|
| `require <chave> ...` | `chk_require` | qualquer chave (notação com ponto, ex.: `oracle.split`) ausente ou vazia (`None`, `""`, `[]`, `{}`) em `state.json` |
| `require gate:<nome>` | `chk_require` | não existe `gates.<nome>` com `decision: "approve"` (v0.3: portão simulado não satisfaz) |
| `calibration` | `chk_calibration` | ver [02-oraculo.md](02-oraculo.md#o-que-chk_calibration-exige-exatamente) |
| `oracle verify` | `chk_oracle_verify` | oráculo não congelado; algum arquivo sumiu; hash atual ≠ hash congelado |
| `runs [--round N] [--config C] [--min M] [--graded] [--or-waived]` | `chk_runs` | menos de `M` execuções (padrão 1) da rodada `N` (padrão: a atual), filtradas por `C`; com `--graded`, alguma execução sem `quality.total`; v0.3: em `remedicao.1`, exige execução com `at` posterior a `done["correcao.1"]` e `decision` não vazia (sem isso a recusa cita `correcao.1`); `--or-waived` aceita se existe `waivers.<N>.<C>` não vazio |
| `defects [--min M] [--evidence] [--classified]` | `chk_defects` | sem `rounds/<n>/DEFEITOS.json5`; menos de `M` defeitos; algum sem `evidencia`; classe fora de `sistema|oraculo|ambiente|executor` ou prioridade fora de `P0..P3` |
| `plan check` | `chk_plan` | sem `PLANO.json5`; sem frentes; frente sem `escreve`; frente que escreve no oráculo; duas frentes com globs sobrepostos; sem `parada` |
| `plan gates` | `chk_plan_gates` | decisão com `produto: true` sem portão `plan:<id>` aprovado |
| `fronts --reported` | `chk_fronts` | alguma frente do PLANO sem `rounds/<n>/fronts/<nome>.md` (a flag `--reported` não é lida; o check é só presença do arquivo) |
| `gate-ok <nome>` | `chk_gate_ok` | portão `<nome>` não aprovado **e** nenhuma chave `preauth.<nome>` |

## Regras de transição

### `load` recusa etapa anterior aberta

`ac.py load <etapa>` percorre todas as etapas anteriores em `order`; se alguma sub-etapa delas não está
em `done`, sai com exit 1. Saída real:

```
$ ac load base
NÃO: etapa 'oraculo' não fechou — conclua-a antes (ac.py load oraculo)
[exit 1]
```

Ao carregar, imprime o pacote (objetivo, parada, orçamento, sub-etapas com `[x]`/`[ ]`, handoff da
etapa anterior), truncado em `limits.handoff_max_chars` (6000 caracteres), e grava `stage` no estado.

> Atenção: **só o `load`** confere a ordem. `check` e `done` não conferem se a etapa anterior fechou.
> Na demonstração, com `base` aberta, `done diagnostico`, `done plano` etc. fecharam normalmente — só o
> `load` recusava. Ver [07-limites.md](07-limites.md).

### `done` roda todos os checks

`ac.py done <etapa>` roda o check de **todas** as sub-etapas, coleta todas as falhas e só fecha se nenhuma
falhou. As sub-etapas que passaram ficam marcadas mesmo quando a etapa não fecha (o estado é salvo com o
evento `done-fail`). Saída real:

```
$ ac done oraculo
NÃO: etapa 'oraculo' não fecha:
  oraculo.2: oracle.calibration ausente: ac.py set oracle.calibration '{"vazio":0.0,"bom":1.0,"conferencias":[{"assercao":"...","correto":true,"evidencia":"arq:linha"}],"configs":2}'
  oraculo.3: faltando: oracle.split
  oraculo.4: oráculo não congelado (ac.py oracle freeze --file ...)
[exit 1]
```

`--handoff "<texto>"` grava `handoff-<etapa>.txt`, que o `load` da etapa seguinte mostra.

`ac.py check <sub-etapa>` faz o mesmo para uma única sub-etapa (útil para iterar num check só).

### `round new` exige rodada terminada e respeita orçamento

1. Se a rodada atual é **> 0** e alguma sub-etapa de `per_round` não está feita → exit 1
   (`rodada N não terminou (<id> pendente)`).
2. Se `budget.max_rounds` existe e `round + 1 > max_rounds` → exit 1
   (`orçamento: máximo de N rodadas atingido — escale ao usuário`).
3. Senão: `round += 1`; limpa as marcas das sub-etapas de `per_round`; apaga `decision`, `report` e
   `integration.tests_green`; `stage = "diagnostico"`.

Saídas reais:

```
$ ac round new
NÃO: rodada 2 não terminou (diagnostico.1 pendente)
[exit 1]

$ ac round new
NÃO: orçamento: máximo de 2 rodadas atingido — escale ao usuário
[exit 1]
```

Com `--max-rounds 2`, as rodadas válidas são 0, 1 e 2: a rodada 0 (medição inicial) não conta como
rodada de correção.

> **Quando abrir a rodada 1.** O código não exige nada de `round new` quando `round == 0` (nem que `base`
> tenha fechado). Há dois fluxos possíveis; recomendamos o primeiro, pelo motivo abaixo:
>
> - **Recomendado:** rodada 0 = `intake`, `oraculo`, `base`; feche `base`; `round new`; a rodada 1 começa
>   em `diagnostico`. Assim `remedicao` (check `runs --min 1` na rodada atual) só passa com execuções
>   novas, e `results compare` mostra o Δ contra a rodada 0.
> - Possível, mas fraco: fazer `diagnostico → decisao` dentro da rodada 0. Aí o check de `remedicao` é
>   satisfeito pelas próprias execuções de `base` e o `results compare` não tem rodada anterior para
>   comparar. (O teste `test_ac.py` grava `DEFEITOS.json5` em `rounds/0/`, então o código não proíbe.)
>
> Essa recomendação é derivada do código; o SKILL.md não diz quando abrir a rodada 1.

## Estado da máquina

```
                        init
                          │
                          ▼
               ┌────── round 0 ──────┐
               │ intake → oraculo →  │
               │ base                │
               └──────────┬──────────┘
                          │ round new  (sem condições na rodada 0)
                          ▼
     ┌──────────────── round n ─────────────────┐
     │ diagnostico → plano → correcao →         │
     │ integracao → remedicao → decisao         │◄──────┐
     └─────────────────────┬────────────────────┘       │
                           │ ac.py set decision <...>   │
          ┌────────────────┼──────────────────┐         │
          ▼                ▼                  ▼         │
       parar           continuar           escalar      │
   (congelar, tag,   round new (exige    (documentar    │
    relatório)       rodada completa e   limites,       │
                     orçamento) ─────────devolver ao ───┘
                                         usuário)
```

## As três saídas da decisão

O `ac.py` **não decide**: `decisao.1` só exige que a chave `decision` exista (`ac.py set decision ...`), e
`results compare` imprime a tabela, as médias com Δ e o texto do critério de parada. Quem decide é o
modelo, pelas regras do SKILL.md:

| Saída | Quando (SKILL.md) | O que fazer |
|---|---|---|
| **parar** | critério cumprido | congelar, tag, relatório (commit/tag passam por portão) |
| **continuar** | orçamento permite **e** houve progresso medido | `ac.py round new` |
| **escalar** | sem progresso em 2 rodadas (`limits.escalate_after_rounds_without_progress: 2`), ou orçamento esgotado | documentar os limites e devolver a decisão ao usuário |

"Nunca rode 'mais uma' às cegas." O único bloqueio mecânico é o de `max_rounds` no `round new`; os
2 sem progresso e `max_hours` não são aplicados pelo script (ver [07-limites.md](07-limites.md)).

## Arquivos de estado

```
<work>/.auto-correcao/
├── state.json              estado atual (gravado de forma atômica: .tmp + os.replace)
├── ledger.jsonl            uma linha por mutação: {ts, event, ...}
├── handoff-<etapa>.txt     texto do `done --handoff` (um por nome de etapa, não por rodada)
└── rounds/
    ├── 0/
    │   └── runs.jsonl      execuções da rodada 0 (base)
    └── <n>/
        ├── DEFEITOS.json5  escrito pelo modelo (diagnostico)
        ├── PLANO.json5     escrito pelo modelo (plano)
        ├── fronts/<nome>.md  relatórios das frentes (ac.py front report)
        └── runs.jsonl      execuções da rodada n (remedicao)
```

A pasta `rounds/<n>/` é criada sob demanda (por qualquer comando que leia ou grave nela); logo após o
`round new` ela pode ainda não existir — crie-a antes de gravar `DEFEITOS.json5`.

### `state.json` (exemplo real, abreviado)

```json
{
 "budget": {"max_hours": 5.0, "max_parallel": 3, "max_rounds": 2},
 "created": "2026-10-03T20:43:38Z",
 "done": {"intake.1": "2026-10-03T20:43:38Z", "...": "..."},
 "gates": {
  "commit": {"at": "...", "by": "founder", "decision": "approve", "note": "eval: aprovação simulada", "simulated": true},
  "plan:DEC-1": {"at": "...", "by": "founder", "decision": "approve", "note": "", "simulated": false},
  "stop": {"at": "...", "by": "founder", "decision": "approve", "note": "critério aceito", "simulated": false}
 },
 "integration": {},
 "oracle": {
  "calibration": {"vazio": 0.0, "bom": 1.0, "configs": 2, "conferencias": [{"assercao": "q1 sistema", "correto": true, "evidencia": "run1/report.md:12"}, "..."]},
  "changes": [{"at": "...", "why": "negação lida como afirmação",
               "evidence": "conferido à mão: run1/report.md:40 diz 'não usa X' e o grader contou X",
               "from": "811352ff8338...", "to": "80b3009a55d7...", "round": 0}],
  "command": "python3 evals/grader.py <saida> --out grading.json",
  "files": ["$T/alvo/evals/grader.py"],
  "frozen_at": "2026-10-03T20:43:39Z",
  "hash": "80b3009a55d70b01a777c57e5d5e8d0a89818b08530c534a6c7059915c0745b3",
  "split": {"quality": "13 asserções neutras de formato", "structure": "40 asserções de artefatos do sistema"}
 },
 "problem": "metade dos evals falha",
 "round": 2,
 "scope": ["src/**", "docs/**"],
 "stage": "diagnostico",
 "stop": "qualidade >= 12/13 nos 3 alvos; zero contornos manuais",
 "target": "$T/alvo",
 "waivers": {"0": {"baseline": "baseline de iteration-1 reaproveitado"}}
}
```

`stage` (v0.3): `done <etapa>` bem-sucedido grava a primeira etapa de `order` ainda não concluída; ao fim, `concluida`; `done` que falha não o muda; `status` imprime `etapa: <stage>`.

Chaves que o código lê: `round`, `stage`, `done`, `gates`, `target`, `scope`, `problem`, `stop`,
`budget.{max_rounds,max_hours,max_parallel}`, `oracle.{command,calibration,split,files,hash,frozen_at,changes}`,
`waivers.<rodada>.<config>`, `preauth.<nome>`, `integration.tests_green`, `decision`, `report`.

Edite o estado só pelos comandos do `ac.py`; mesmo o `set` permite contornar travas (ver
[07-limites.md](07-limites.md#limites-mecânicos)).

`stage` é só a última etapa carregada (`load`) ou `diagnostico` após `round new`; não indica que ela está
em andamento.

### `ledger.jsonl` (primeiras linhas reais)

```json
{"event": "init", "target": "$T/alvo", "ts": "2026-10-03T20:43:38Z"}
{"event": "load", "stage": "intake", "ts": "2026-10-03T20:43:38Z"}
{"event": "done-fail", "stage": "intake", "ts": "2026-10-03T20:43:38Z"}
{"by": "founder", "decision": "approve", "event": "gate", "name": "stop", "simulated": false, "ts": "2026-10-03T20:43:38Z"}
{"event": "done", "stage": "intake", "ts": "2026-10-03T20:43:38Z"}
```

Eventos gravados: `init`, `set` (com `key`), `load`, `check`, `done`, `done-fail`, `gate`,
`oracle-freeze`, `oracle-change` (com `why`, `evidence`, `frm`, `to`), `run-record`, `run-waive`,
`front-report`, `round-new`.

### `rounds/<n>/runs.jsonl` (linha real)

```json
{"alvo": "py-billing", "at": "2026-10-03T20:43:41Z", "config": "sistema", "decision": "GO", "dir": "$T/runs/r1-sis", "grading": "$T/g-r1.json", "minutes": 21.0, "quality": {"passed": 12, "total": 13}, "round": 1, "simulated": true, "structure": {"passed": 31, "total": 40}, "tokens": 150000}
```

### `status`

```
$ ac status
alvo: $T/alvo
rodada: 2 · etapa: diagnostico
parada: qualidade >= 12/13 nos 3 alvos; zero contornos manuais
 ✓ intake       3/3
 ✓ oraculo      4/4
 ✓ base         3/3
 ✓ diagnostico  2/2
 ...
```

`✓` etapa completa · `…` parcial · espaço = nada feito.
