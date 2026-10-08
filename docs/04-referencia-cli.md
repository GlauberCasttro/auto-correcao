# 04 — Referência da CLI (`scripts/ac.py`)

```
python3 ~/.claude/skills/auto-correcao/scripts/ac.py --work <campanha> <comando> [...]
```

- Python 3.9+, só stdlib.
- Windows nativo: troque `python3` por `python` (ou `py -3`) em todos os exemplos. `gate`, `preauth` e `frase`
  leem a frase só pelo console (PowerShell ou Windows Terminal); no Git Bash use `winpty python .../ac.py ...` —
  sem console, saem com exit 2.
- `--work` é **obrigatório** em todo comando: o diretório da campanha (fora do alvo medido). O estado vai
  para `<work>/.auto-correcao/`. O caminho é resolvido com `realpath`.
- Em zsh, não guarde o comando numa variável (não divide palavras). Use uma função:
  `ac() { python3 $AC/scripts/ac.py --work <campanha> "$@"; }` — é o `ac` dos exemplos abaixo.

## Exit codes

| Código | Significado | Prefixo da mensagem (stderr) |
|---|---|---|
| `0` | ok | — (saída em stdout) |
| `1` | check não satisfeito (`Fail`) | `NÃO: ...` |
| `2` | entrada inválida (`Bad`), erro de argumento do argparse, ou nenhum comando | `erro: ...` / uso do argparse |

> Exceções não tratadas (ex.: arquivo de `--file`/`--grading` inexistente) saem com o traceback do Python
> e código **1**, que se confunde com "check não satisfeito". Ver [07-limites.md](07-limites.md).

## Ajuda

```
$ python3 scripts/ac.py --work /tmp/x --help
usage: ac.py [-h] --work WORK
             {init,set,status,load,check,done,gate,preauth,oracle,run,front,round,results,plan,defects,overlap} ...

estado mecânico da auto-correcao

positional arguments:
  {init,set,status,load,check,done,gate,preauth,oracle,run,front,round,results,plan,defects,overlap}

options:
  -h, --help            show this help message and exit
  --work WORK           diretório da campanha (fora do alvo medido)
```

Cada subcomando aceita `--help`.

## Resumo

| Comando | Para quê | Etapa típica |
|---|---|---|
| `init` | cria/atualiza a campanha (alvo, escopo, problema, parada, orçamento) | intake |
| `set <chave> <valor>` | grava uma chave no estado | qualquer |
| `status` | mostra rodada, etapa, parada e progresso por etapa | qualquer |
| `load <etapa>` | imprime o pacote da etapa; recusa se a anterior está aberta | início de cada etapa |
| `check <sub-etapa>` | roda o check de uma sub-etapa e a marca feita | qualquer |
| `done <etapa>` | roda todos os checks da etapa; fecha ou recusa | fim de cada etapa |
| `gate <nome>` | registra decisão humana (só em tty, com a frase do founder) | intake, plano, integracao |
| `preauth <nome>` | pré-autoriza portão (só em tty, com a frase do founder) | integracao |
| `frase definir|conferir` | define a frase do founder / confere todas as aprovações (v0.4, só em tty) | antes do intake / antes de `done decisao` |
| `overlap --other B` | detecta colisão de escopo entre campanhas (v0.3) | antes de sobrepor campanhas |
| `oracle freeze|verify|change` | congela, confere ou muda o oráculo | oraculo, integracao |
| `run record|waive` | registra uma execução ou dispensa uma configuração | base, remedicao |
| `front report <nome>` | registra o relatório de uma frente | correcao |
| `round new` | abre a próxima rodada | após base / após decisao |
| `results compare` | tabela de execuções e Δ entre rodadas | decisao |
| `plan check|gates` | valida o PLANO / os portões de decisões de produto | plano |
| `defects check` | valida DEFEITOS (evidência + classe/prioridade) | diagnostico |

---

## `init`

```
ac.py init [--target TARGET] [--scope SCOPE]... [--problem PROBLEM] [--stop STOP]
           [--max-rounds N] [--max-hours H] [--max-parallel N]
```

| Flag | Tipo | Grava em |
|---|---|---|
| `--target` | caminho (vira `realpath`) | `target` |
| `--scope` | repetível | `scope` (lista) |
| `--problem` | texto | `problem` |
| `--stop` | texto (critério em números) | `stop` |
| `--max-rounds` | int | `budget.max_rounds` |
| `--max-hours` | float | `budget.max_hours` |
| `--max-parallel` | int | `budget.max_parallel` |

Pode ser rodado de novo: só sobrescreve o que for passado. Estado inicial: `round 0`, `stage intake`.
Só `max_rounds` é aplicado mecanicamente (em `round new`).

```
$ ac init --target $T/alvo --scope 'src/**' --scope 'docs/**' --problem "metade dos evals falha" \
    --stop "qualidade >= 12/13 nos 3 alvos; zero contornos manuais" --max-rounds 2 --max-hours 5 --max-parallel 3
campanha em $T/campanha/.auto-correcao (rodada 0, etapa intake)
```

## `set`

```
ac.py set <chave> <valor>
```

- `<chave>` em notação com ponto (`oracle.calibration`, `integration.tests_green`, `preauth.commit`).
- `<valor>` é interpretado como JSON se possível (`true`, `0.5`, `{...}`); senão, como texto.
- Recusa (exit 2) chaves que começam com `oracle.files` ou `oracle.hash`.

Chaves que os checks leem e que só se gravam por `set`: `oracle.command`, `oracle.calibration`,
`oracle.split`, `integration.tests_green`, `decision`, `report`, `preauth.<nome>`.

```
$ ac set oracle.command "python3 evals/grader.py <saida> --out grading.json"
ok: oracle.command
$ ac set oracle.hash abc
erro: use `oracle freeze` / `oracle change` para o oráculo
[exit 2]
```

## `status`

```
$ ac status
alvo: $T/alvo
rodada: 0 · etapa: intake
parada: qualidade >= 12/13 nos 3 alvos; zero contornos manuais
   intake       0/3
   oraculo      0/4
   base         0/3
   diagnostico  0/2
   plano        0/2
   correcao     0/1
   integracao   0/3
   remedicao    0/2
   decisao      0/2
```

Sem campanha: `erro: campanha não iniciada em <work> — rode \`ac.py --work <work> init ...\`` (exit 2).

## `load`

```
ac.py load <etapa>
```

Recusa (exit 1) se alguma etapa anterior em `order` não fechou; etapa desconhecida → exit 2. Imprime até
6000 caracteres (`limits.handoff_max_chars`) e grava `stage`.

```
$ ac load diagnostico
# etapa diagnostico · rodada 1
objetivo: DEFEITOS.json5 com evidência exata, prioridade e classe
parada: qualidade >= 12/13 nos 3 alvos; zero contornos manuais
orçamento: {'max_hours': 5.0, 'max_parallel': 3, 'max_rounds': 2}
[ ] diagnostico.1 (main) ler notes.md e asserções falhas; reproduzir os P0
[ ] diagnostico.2 (main) classificar: sistema | oraculo | ambiente | executor
handoff anterior:
rodada 0: Q 9/13 sistema, 10/13 baseline
```

## `check`

```
ac.py check <sub-etapa>
```

Roda o check da sub-etapa (ex.: `oraculo.2`) e, se passar, marca-a feita. Sub-etapa desconhecida → exit 2.

```
$ ac check intake.1
ok: intake.1
$ ac check intake.3
NÃO: faltando: portão 'stop' aprovado (ac.py gate stop --by <humano> --decision approve)
[exit 1]
```

## `done`

```
ac.py done <etapa> [--handoff TEXTO]
```

Roda todos os checks; lista todas as falhas (exit 1) ou fecha. `--handoff` grava `handoff-<etapa>.txt`
(só quando fecha).

```
$ ac done base
NÃO: etapa 'base' não fecha:
  base.2: rodada 0: 0 execução(ões) 'baseline' registradas, mínimo 1 (ac.py run record ...)
  base.3: execuções sem nota de qualidade: ['py-billing/sistema']
[exit 1]
```

## `gate`

```
ac.py gate <nome> --by QUEM --decision approve|reject [--note TEXTO] [--simulated]
```

**v0.4:** nesta ordem: (a) argumentos e `AC_AUDIT_LOG` fora do `--work`, senão exit 2 antes de qualquer
prompt; (b) stdin tty e `/dev/tty`, senão exit 2; (c) frase definida e `frase.json` válido (`kdf`
`pbkdf2-sha256`, `iter` int ≥ 600000), senão exit 2 sem prompt; (d) um prompt `FRASE ...:` com eco desligado,
uma tentativa, frase errada → exit 1, nada gravado; (e) grava. A aprovação leva `seq` (linha do evento no
`ledger.jsonl`), `estado_hash` (sha256 do `state.json` antes) e `tag = HMAC-SHA256(K, canonical(work, nome,
decisão, seq, estado_hash))`, com `K = PBKDF2(frase, salt_chave)`. Nenhum argumento (`--frase` → erro), nenhuma
variável de ambiente e nenhuma stdin em pipe fornece a frase. `--simulated` nunca satisfaz `gate:X` em `require`.
Cada aprovação bem-sucedida acrescenta uma linha de auditoria em `$AC_AUDIT_LOG` (ver abaixo). O agente não
roda isto: o hook `scripts/hook_aprovacao.py` nega; o founder roda no terminal (ou via `aprovar-*.sh`, no
terminal, nunca pelo `!` do Claude Code).

Grava `gates.<nome> = {by, decision, note, at, simulated, seq, tag}` (simulado: sem `seq`/`tag`; `frase conferir` o ignora). `--decision` fora de `approve|reject` → exit 2.
Nomes que os checks conhecem: `stop` (intake.3), `plan:<id>` (plano.2), `commit` (integracao.3).
Uma decisão posterior com o mesmo nome sobrescreve a anterior.

```
$ ac gate stop --by founder --decision approve --note "critério aceito"
portão stop: approve por founder
$ ac gate commit --by founder --decision approve --simulated --note "eval: aprovação simulada"
portão commit: approve por founder (simulado)
```

## `preauth`

```
ac.py preauth <nome> --by QUEM --requires SUBETAPA [SUBETAPA ...] [--note TEXTO] [--simulated]
```

Pré-autoriza um portão condicionado a sub-etapas concluídas. Mesmas regras do `gate` na v0.4: tty + frase,
exit 2 sem tty, auditoria em `$AC_AUDIT_LOG`. A decisão assinada é `"preauth:" + ",".join(requires)`.

## `frase` (v0.4)

```
ac.py --work W frase definir     # 2 prompts (frase, confirmação); se já existe: antiga, nova, nova de novo
ac.py --work W frase conferir    # 1 prompt; recalcula a tag de toda aprovação da campanha
```

`definir` não exige campanha nem `--work` (`ac.py frase definir`; `conferir`, `gate` e `preauth` exigem
`--work`). Aceita senha ou frase: ≥12 caracteres, ≥6 distintos (espaço conta), e ≥3 palavras OU ≥3 classes
entre minúscula, maiúscula, dígito e símbolo. Recusa senha ou frase fraca, confirmação divergente e
frase antiga errada (o arquivo fica byte-idêntico). Grava `$AC_FRASE_FILE` atômico, modo 0600.

`conferir` sai **1** e lista cada problema: evento do ledger (gate não simulado, preauth, frase-conferida) sem
tag, com tag errada ou com `seq` ≠ posição; evento sem linha de auditoria (`work`, `seq` e `tag`); linha de
auditoria desta campanha ausente do ledger; entrada de `state.gates`/`state.preauth` que não seja a aprovação
válida **mais recente** daquele nome. Para portões por rodada (todos menos `stop`), essa aprovação também tem
de vir depois do último `round-new`. Tudo ok → grava `frase-conferida` (ledger e auditoria) e sai 0.

**Rollout v0.3 → v0.4 (`frase conferir --assinar-legado`).** `frase definir` grava `criada_em` (UTC). Uma
aprovação é **legada** se reúne três condições: não tem tag, tem `ts` < `criada_em` e está no ledger antes do 1º
evento com tag. Qualquer outra aprovação sem tag é forja, inclusive uma retroativa acrescentada depois de um
evento tagueado. O `conferir` sem a flag e com legado pendente sai 1, lista cada legada e cita
`--assinar-legado`. Com a flag, pede a frase uma vez. Se houver qualquer outro problema, não assina nada. Senão,
grava um evento humano `legado-assinado` (ledger e auditoria) com `itens: [{linha, nome, decisao, ts, tag}]`, em
que a tag de cada item é `tag(K, work, nome, decisao, linha, "legado:" + ts)`. Daí em diante o `conferir` aceita
essas legadas e a entrada v0.3 correspondente no state. Limite: numa campanha ainda sem nenhum evento tagueado,
um agente pode forjar uma aprovação sem tag com `ts` antigo. Por isso o founder lê a lista antes de assinar.

`done decisao` exige um `frase-conferida` posterior a toda aprovação não simulada. Senão sai com exit 1 e cita
`frase conferir`. O `done` só confere a ordem. A autenticidade vem do `conferir` do founder, que também
reconfere os `frase-conferida` anteriores.

Fluxo do founder: definir a frase uma vez, digitá-la em cada aprovação e rodar `frase conferir` no fim. Limite
honesto: o agente pode apagar o `frase.json` e definir outra frase. Isso só é pego quando o founder digita a
frase verdadeira no `conferir`.

## Auditoria de aprovações (v0.3)

`AC_AUDIT_LOG` (só o CAMINHO; sugerido `~/.claude/auto-correcao/audit.jsonl`). Cada `gate`/`preauth`
bem-sucedido acrescenta 1 linha JSON: `cmd` (`gate|preauth|frase-conferida`), `name`, `decision` (gate), `by`,
`work` (realpath da campanha), `user` (usuário do SO), `tty` (ttyname), `ts` e, na v0.4, `seq`,
`estado_hash` e `tag`. Se o caminho resolver para dentro
do `--work` → recusa (exit ≠0, nada gravado).

## `overlap` (v0.3)

```
ac.py --work A overlap --other B [--other C ...]
```

Compara o `scope` de A com o de cada B como caminhos absolutos (`target` + glob) e o `scope` de A com os
arquivos de oráculo congelados de B. Colisão → exit 1 citando o glob; disjunto → 0. Mesmos globs em alvos
diferentes não colidem (L17).

## Hook `scripts/hook_aprovacao.py` (v0.3)

Hook PreToolUse (JSON do payload na stdin). Bloqueia (exit 2) `Bash` que invoque `ac.py … gate|preauth` ou
`co.py … approve`, com ou sem `agent_id`, inclusive por caminho absoluto/`~`, `python3 -m ac`, aspas, `sh -c`,
`;`/`&&`/`|`, `$AC` não resolvido e `runpy`. Permite `status|check|done|run record`, comandos alheios e
ferramentas não-Bash. `--selftest` → exit 0. Instalação em `settings.json` (o matcher inclui `PowerShell` porque,
no Windows, o Claude Code tem essa ferramenta além da `Bash`):

```json
{"hooks": {"PreToolUse": [{"matcher": "Bash|PowerShell",
  "hooks": [{"type": "command", "command": "python3 ~/.claude/skills/auto-correcao/scripts/hook_aprovacao.py"}]}]}}
```

No Windows nativo use `python` (ou `py -3`), não `python3`:
`python "%USERPROFILE%\.claude\skills\auto-correcao\scripts\hook_aprovacao.py"` no `command`.
O hook é filtro, não sandbox: a trava real é a frase.

Limite honesto: quem controla o terminal do founder ou desativa o hook ainda aprova; é custo e rastro, não
prova de identidade (L18).

## `oracle`

```
ac.py oracle freeze --file ARQ [--file ARQ ...]
ac.py oracle verify
ac.py oracle change --why TEXTO --evidence TEXTO [--file ARQ ...]
```

| Ação | Efeito | Recusa |
|---|---|---|
| `freeze` | grava `oracle.files`, `oracle.hash`, `oracle.frozen_at` | já congelado (exit 2); sem `--file` ou arquivo inexistente (exit 2) |
| `verify` | confere o hash | não congelado; arquivo sumiu; hash diferente (exit 1) |
| `change` | recalcula o hash (sobre `--file` ou os arquivos já congelados) e acrescenta em `oracle.changes` | sem `--why` ou sem `--evidence` (exit 2) |

```
$ ac oracle freeze --file $T/alvo/evals/grader.py
oráculo congelado: 811352ff8338
$ ac oracle verify
NÃO: oráculo mudou fora de `oracle change` (hash 80b3009a55d7 ≠ congelado 811352ff8338)
[exit 1]
$ ac oracle change --why "negação lida como afirmação" --evidence "conferido à mão: run1/report.md:40 diz 'não usa X' e o grader contou X"
oráculo recongelado: 80b3009a55d7 (mudança registrada; toda medição anterior deve ser recorrigida)
```

Detalhes em [02-oraculo.md](02-oraculo.md).

## `run`

```
ac.py run record --config CONFIG [--round N] [--alvo NOME] [--dir DIR] [--grading GRADING.json]
                 [--tokens N] [--minutes M] [--decision TEXTO] [--simulated]
ac.py run waive  --config CONFIG [--round N] [--why TEXTO]
```

`--config` é obrigatório nas duas ações. `--round` padrão: rodada atual. `--alvo` padrão: `default`.

**v0.3 (L02):** `record` com `quality.total` diferente do da base (1ª execução com nota da rodada) é
recusado (exit ≠0, mensagem cita `L02`, nada gravado), salvo `oracle change` com timestamp posterior ao da base.

**record** acrescenta uma linha em `rounds/<round>/runs.jsonl` com `round, config, alvo, dir, tokens,
minutes, decision, simulated, at` e, se `--grading` foi passado, `quality` e `structure` (lidos de
`summary.quality` e `summary.structure` do JSON) e `grading` (caminho absoluto). Sem `--grading`, a
execução fica **sem nota** e o check `--graded` falha para essa rodada.

**waive** grava `waivers.<round>.<config> = <why>` — dispensa registrada para o check `--or-waived`
(usado em `base.2` para o baseline). Só conta se `--why` não estiver vazio.

```
$ ac run record --round 0 --config sistema --alvo py-billing --dir $T/runs/r0-sis --grading $T/g-sis.json \
    --minutes 33 --tokens 269008 --decision GO --simulated
execução registrada: rodada 0 py-billing/sistema
$ ac run waive --round 0 --config baseline --why "baseline de iteration-1 reaproveitado"
dispensa registrada
```

Formato do `--grading`:

```json
{"summary": {"quality": {"passed": 9, "total": 13}, "structure": {"passed": 22, "total": 40}}}
```

> `run record` só acrescenta; não há comando para apagar ou substituir uma execução. Registre com
> `--grading` desde a primeira vez. Ver [07-limites.md](07-limites.md).

## `front`

```
ac.py front report <nome> --file RELATORIO.md
```

Copia o arquivo para `rounds/<rodada atual>/fronts/<nome>.md` (sobrescreve se existir).

```
$ ac front report frente-scan --file $T/rel-scan.md
relatório da frente frente-scan registrado
```

## `round`

```
ac.py round new
```

Na rodada > 0, exige todas as sub-etapas de `per_round` feitas; respeita `budget.max_rounds`. Detalhes
em [01-maquina-de-estado.md](01-maquina-de-estado.md#round-new-exige-rodada-terminada-e-respeita-orçamento).

```
$ ac round new
rodada 1 aberta — comece por `ac.py load diagnostico`
$ ac round new
NÃO: orçamento: máximo de 2 rodadas atingido — escale ao usuário
[exit 1]
```

## `results`

```
ac.py results compare
```

Imprime uma tabela Markdown com todas as execuções de todas as rodadas (até a atual), depois a média de
qualidade e de estrutura da rodada atual (todas as configs exceto `baseline`) com Δ contra a rodada
anterior, e o critério de parada. Sem nenhuma execução → exit 1. Execuções com `--simulated` aparecem
como `GO (simulado)` (L13).

```
$ ac results compare
| rodada | alvo | config | qualidade | estrutura | decisão | tokens | min |
|---|---|---|---|---|---|---|---|
| 0 | py-billing | sistema | 9/13 | 22/40 | GO (simulado) | 269008 | 33.0 |
| 0 | py-billing | baseline | 10/13 | 0/40 | — | 60000 | 7.0 |
| 1 | py-billing | sistema | 11/13 | 29/40 | GO (simulado) | 150000 | 21.0 |
| 2 | py-billing | sistema | 12/13 | 30/40 | GO (simulado) | 150000 | 21.0 |
quality: rodada 2 = 0.92 (anterior 0.85, Δ +0.08)
structure: rodada 2 = 0.75 (anterior 0.72, Δ +0.03)
parada: qualidade >= 12/13 nos 3 alvos; zero contornos manuais
```

O comando **não** avalia o critério de parada; só o imprime ao lado dos números.

## `plan`

```
ac.py plan check     # = check de plano.1
ac.py plan gates     # = check de plano.2
```

Saída `plano ok` (exit 0) ou `NÃO: ...` (exit 1). Detalhes em
[03-frentes-paralelas.md](03-frentes-paralelas.md).

```
$ ac plan gates
NÃO: decisões de produto sem portão aprovado: ['DEC-1'] (ac.py gate plan:<id> ...)
[exit 1]
```

## `defects`

```
ac.py defects check
```

Equivale a `defects --min 1 --evidence --classified` sobre `rounds/<rodada atual>/DEFEITOS.json5`.

```
$ ac defects check
NÃO: defeitos sem evidência: ['D-1-01']
[exit 1]
$ ac defects check
defeitos ok
```

## Testes do próprio script

```
cd ~/.claude/skills/auto-correcao/scripts && python3 -m unittest discover -s tests
...
Ran 14 tests in 0.102s
OK
```
