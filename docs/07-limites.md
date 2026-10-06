> **Atualização v0.2 (2026-10-03):** corrigidos, com teste de regressão em `scripts/tests/test_ac.py`
> (`LockBypassTest`), os itens desta lista que furavam travas: `set` não altera mais estado protegido
> (`gates`, `done`, `round`, `stage`, `waivers`, `oracle`, `target`, `preauth`); `check`/`done` exigem as etapas
> anteriores fechadas; `round new` na rodada 0 exige intake/oráculo/base fechados e zera os portões da rodada
> (mantém `stop`); o registro mais recente de cada (alvo, config) prevalece em `runs`; `run waive` exige `--why`;
> `oracle change` exige `freeze` prévio; arquivo inexistente sai com exit 2; `status` mostra portões e marca
> `(SIMULADO)`; handoff passou a ser por rodada; sem DeprecationWarning. Continuam abertos: orçamento só aplica
> `max_rounds`; `--reported` só confere o arquivo; `plan check` não confere classe dos defeitos nem o contrato;
> `results compare` faz média de todas as configs não-baseline juntas; portão simulado ainda conta como aprovado
> (visível no status).

> **Atualização v0.4 (frase-senha):** tty + desafio era forjável (um agente com `pty.fork` lê o desafio e o
> redigita). `gate`/`preauth` agora pedem a frase do founder (`ac.py frase definir`, uma vez) e gravam uma tag
> HMAC por aprovação. `ac.py frase conferir` recalcula todas as tags (ledger × auditoria × state), e
> `done decisao` exige `frase-conferida` posterior à última aprovação. Limite que permanece: o `frase.json` é
> legível. Um agente pode apagá-lo, definir outra frase e aprovar ou conferir com ela. Isso só é pego quando o
> founder digita a frase **verdadeira** no `frase conferir`. A força depende da entropia da frase. Campanhas
> v0.3 com aprovações sem tag (anteriores ao `criada_em` da frase e ao 1º evento tagueado) são assinadas uma
> vez com `frase conferir --assinar-legado`. Limite: antes do 1º evento tagueado, um agente pode forjar uma
> aprovação sem tag com `ts` antigo. O founder confere a lista impressa antes de assinar.

> **Atualização v0.3:** `gate`/`preauth` exigem tty + desafio; hook `scripts/hook_aprovacao.py`; auditoria em
> `$AC_AUDIT_LOG`; `remedicao.1` exige execução posterior a `correcao.1` com `decision`; `run record` recusa
> `quality.total` ≠ base (L02); `stage` chega a `concluida`; `PLANO.decisoes` = `{id, produto, texto}`;
> subcomando `overlap`. Portão simulado não satisfaz `gate:X`. Limite que permanece: o desafio não prova
> identidade (quem controla o terminal ou o hook ainda aprova).

# 07 — Limites da v0.1 (honesto)

O que a skill ainda não faz, o que depende só da disciplina do modelo e onde o código diverge do texto.
Cada item foi conferido no código (`scripts/ac.py`) e, quando indicado, reproduzido na campanha de
demonstração.

## Estado de validação

- **Ainda não validada numa campanha real.** As 14 lições vêm do laboratório que refinou a
  codebase-specialists *antes* desta skill existir; a primeira campanha real com o `ac.py` é a planejada
  em [06-exemplo-campanha.md](06-exemplo-campanha.md), ainda não executada.
- Há 14 testes unitários do `ac.py` (`scripts/tests/test_ac.py`, todos passando) e 4 casos de avaliação
  da skill em `evals/evals.json`; nenhum resultado dessas avaliações está registrado no repositório.

## O que o script não faz (o modelo faz)

- **Sem execução automática de subagentes.** O `ac.py` não despacha executores, verificadores nem frentes;
  o modelo despacha (prompts em `references/prompts.json5`) e registra os resultados.
- **Não roda o oráculo nem as suítes.** `oracle.calibration`, `integration.tests_green`, `decision` e
  `report` são **declarados** com `ac.py set`; o script confere presença e coerência, não verdade.
- **Não decide parar/continuar/escalar.** `results compare` imprime números e o texto do critério; não os
  compara.
- **Não roda git.** O portão `commit` registra autorização; não impede um commit feito fora dele.
- **Não confere isolamento** das execuções (L05) nem que uma frente escreveu só dentro do seu `escreve`
  (o `plan check` valida o plano, não o diff).

## Limites mecânicos

- **`globs_overlap` é aproximação conservadora.** Compara `fnmatch` nos dois sentidos e prefixos
  literais (tudo antes do primeiro `* ? [ {`); não expande globs contra o disco. Glob sem prefixo
  literal (`**`, `*.py`, `**/*.md`) colide com qualquer outro; chaves (`src/{a,b}/**`) cortam o prefixo e
  geram falso positivo (colide com `src/c/**`). `fnmatch` trata `*` como casando `/` também.
  Ver [03-frentes-paralelas.md](03-frentes-paralelas.md).
- **Orçamento parcial.** Só `max_rounds` é aplicado (em `round new`). `max_hours` e `max_parallel` são
  gravados e mostrados pelo `load`, mas nada os confere. Em `ciclo.json5`, `limits.max_parallel_default`
  e `limits.escalate_after_rounds_without_progress` **não são lidos** pelo código; só
  `limits.handoff_max_chars` é.
- **Ordem só no `load`.** `check` e `done` não conferem se a etapa anterior fechou. Na demonstração, com
  `base` aberta, `done diagnostico`…`done decisao` da rodada 1 fecharam; só os `load` recusavam.
- **`round new` na rodada 0 não exige nada** — nem `base` fechada. Na demonstração a rodada 1 abriu com
  `base` em 2/3; depois todo `load` recusou com "etapa 'base' não fechou".
- **`set` é uma porta lateral.** Só bloqueia chaves que começam com `oracle.files`/`oracle.hash`.
  `set gates.stop '{"decision":"approve"}'` fez `check intake.3` passar sem `ac.py gate` (reproduzido);
  `set oracle '{...}'` substitui o objeto inteiro do oráculo (inclusive `files` e `hash`), `set done '{...}'`
  marca sub-etapas como feitas (depois disso o `load` da etapa seguinte aceitou) e `set round 5` muda a
  rodada — os três reproduzidos. As travas
  supõem que o orquestrador não usa `set` para contorná-las; o ledger registra o `set` com a chave.
- **Portões persistem entre rodadas.** `round new` não limpa `gates`: o `commit` aprovado na rodada 1
  satisfaz `integracao.3` na rodada 2, e `plan:DEC-1` continua aprovado se o id for reutilizado.
- **Aprovação simulada conta como aprovação.** `gate --simulated` grava `simulated: true`, mas os checks
  não distinguem e o `status` não mostra. Só `results compare` (para execuções `run --simulated`) exibe
  "(simulado)".
- **Pisos fixos.** `diagnostico.1` exige ≥1 defeito e `plano.1` exige ≥1 frente — uma rodada só com
  defeitos de oráculo, ou sem defeitos, não fecha essas etapas.
- **Checks que não leem o conteúdo.** `fronts --reported` só confere que `fronts/<nome>.md` existe (a flag
  `--reported` nem é lida); `require oracle.split` só confere presença; `defects` não confere
  `reproduzido` nem `frente`; `plan check` não confere `contrato` nem que só defeitos `sistema` viraram
  frente.
- **`results compare` junta configurações.** A média da rodada inclui todas as configs não-baseline
  (ex.: `sistema` e um modo barato juntos) e todos os alvos.
- **Handoff por etapa, não por rodada.** `handoff-<etapa>.txt` é sobrescrito a cada rodada; o `load` de
  `diagnostico` na rodada 2 mostra `handoff-base.txt` (da rodada 0), não o de `decisao` da rodada 1.
  O pacote do `load` é truncado em 6000 caracteres sem aviso.
- **`rounds/<n>/` é criado sob demanda**; logo após `round new` a pasta pode não existir.

## Armadilhas reproduzidas na demonstração

- **Execução sem nota é permanente.** `run record` só acrescenta em `runs.jsonl` e não há comando para
  remover ou substituir. Uma execução registrada sem `--grading` faz `runs --graded` falhar para sempre
  naquela rodada; na demonstração, `base` nunca mais fechou ("execuções sem nota de qualidade:
  ['py-billing/sistema']"), mesmo depois de a execução ser registrada de novo com nota.
- **`run waive` sem `--why` é silenciosamente inútil.** Imprime "dispensa registrada", grava `""`, e o
  check `--or-waived` não aceita valor vazio.
- **`oracle change` sem `freeze` prévio** "recongela" um conjunto vazio de arquivos (hash `e3b0c44298fc…`);
  `oracle verify` depois diz "oráculo não congelado".
- **Arquivo inexistente vira traceback.** `front report --file`, `run record --grading` e
  `oracle change --file` com caminho inexistente saem com traceback do Python e código 1 — o mesmo código
  de "check não satisfeito".
- **`DeprecationWarning` em Python 3.13.** `plan check` (e `done plano`) imprimem no stderr um aviso sobre
  `re.split(..., 1)` com `maxsplit` posicional. Inofensivo hoje.

## Divergências entre o texto da skill e o código

| # | Onde | Texto diz | Código faz |
|---|---|---|---|
| 1 | SKILL.md | "as cinco últimas repetem por rodada" | `per_round` tem **seis** etapas (diagnostico…decisao) |
| 2 | SKILL.md | não diz quando abrir a rodada 1 | `round new` na rodada 0 é incondicional; `test_ac.py` grava DEFEITOS em `rounds/0/`; a rodada 0 inteira (com `remedicao`) torna o check de remedição trivial — ver [01](01-maquina-de-estado.md#round-new-exige-rodada-terminada-e-respeita-orçamento) |
| 3 | SKILL.md | "`ac.py load <etapa>` ... → `ac.py done <etapa>` (roda os checks; falha não avança)" | `done` não verifica a ordem das etapas; só `load` |
| 4 | SKILL.md | "sem progresso em 2 rodadas ... → escalar" | `escalate_after_rounds_without_progress` não é lido; nada mecânico |
| 5 | SKILL.md / intake.2 | orçamento de "horas de parede, execuções paralelas" | `max_hours` e `max_parallel` não são aplicados |
| 6 | SKILL.md | "pacote ≤2k tokens" | limite é `handoff_max_chars: 6000` caracteres, truncamento sem aviso |
| 7 | formatos.json5 `run` | campo `notes: "abs/notes.md"` | `run record` não tem flag para `notes`; o campo nunca é gravado |
| 8 | formatos.json5 `plano` | `decisoes[].gate: "plan:DEC-1"` | ignorado; o portão é sempre `plan:<id>` |
| 9 | ciclo.json5 | check `fronts --reported` | `--reported` não é lido; só presença do arquivo |
| 10 | licoes.json5 L03 | "todo check novo nasce com um teste em que o subcomando passa e o efeito não acontece" | disciplina; não há verificação disso |
| 11 | licoes.json5 L08 | "só defeito de classe sistema vira frente" | `plan check` não cruza `frentes[].defeitos` com a classe |
| 12 | licoes.json5 L13 / SKILL.md trava 3 | aprovação simulada aparece no veredito | portões simulados contam como aprovados e não aparecem no `status` |
| 13 | SKILL.md trava 2 | oráculo só muda por `oracle change` | `set oracle '{...}'` sobrescreve o objeto inteiro (só `oracle.files`/`oracle.hash` com ponto são barrados) |
| 14 | docstring do ac.py | "Exit: 0 ok · 1 check não satisfeito · 2 entrada inválida" | arquivo inexistente gera traceback com exit 1 |
