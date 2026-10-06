# 06 — Exemplo: a campanha planejada (codebase-specialists, iteração 5)

Este é um exemplo completo de uso sobre um caso real: a próxima rodada de refinamento da skill
**codebase-specialists**, planejada em
`campanhas/PROXIMA-RODADA.md` (nas campanhas da codebase-specialists). A codebase-specialists é só o
alvo do exemplo — e o caso de origem das 14 lições; a auto-correcao não depende dela.

> Status: **planejada, não executada.** O diretório da campanha (`campanha-iter5`) ainda não existe.
> Os comandos abaixo são a tradução do prompt planejado para o ciclo do `ac.py`; todos parseiam, mas
> nenhum resultado aqui é medido. Onde o prompt não fixa um valor (ex.: escopo de escrita), o texto diz
> que é uma escolha deste exemplo.

## O ponto de partida

Do `iteration-4/RESULTADOS-E-DEFEITOS.json5`:

- Só `ts-shop` concluiu: "GO (simulado), --fast, 10/10 especialistas, G1–G16 verdes — após contorno
  manual"; qualidade "12/13 no corretor = 13/13 real (STALE: falso positivo — 'playwright' citado para
  dizer que NÃO existe)"; baseline 10/13; 33 min; 269 008 tokens do orquestrador; 79 subagentes;
  **5 contornos manuais**.
- `py-billing` pausou em `validate.3`; `go-polyglot` em `validate.2`.
- Critério de parada anterior: "NÃO CUMPRIDO — 5 contornos manuais".
- Defeitos abertos: 2× P0, 2× P1, 1× P2 (listados no diagnóstico abaixo).

## Visão geral da campanha

```
 Passo 0 (rodada 0)                        rodada 1                       rodada 2 (se continuar)
 ───────────────────                       ────────                       ───────────────────────
 intake ── gate stop                       diagnostico (5 defeitos)       idem, com os defeitos
 oraculo ─ calibra check_run.py,           plano ── frentes ≤3,           restantes
           congela                                  gate plan:<id>
 base ──── retoma py-billing e             correcao
           go-polyglot (1 por vez);        integracao ── 3.13 + 3.9.6,
           registra ts-shop                              gate commit
           baseline: iteration-1           remedicao (3 alvos, 1 por vez)
 round new ───────────────────────────►    decisao ─── parar/continuar/escalar ──► round new
                                                                                   (máx. 2)
```

## intake

O prompt fixa alvo, critério, orçamento e portões. Tradução:

```bash
AC=~/.claude/skills/auto-correcao
ac() { python3 $AC/scripts/ac.py --work campanhas/campanha-iter5 "$@"; }

ac init --target ~/.claude/skills/codebase-specialists \
  --scope 'SKILL.md' --scope 'scripts/**' --scope 'references/**' --scope 'docs/**' \
  --problem "iteração 4: 5 contornos manuais no ts-shop; py-billing e go-polyglot pausados; 2 P0, 2 P1, 1 P2 abertos" \
  --stop "rodada --fast nos 3 alvos: >=2/3 GO; zero contornos manuais; [Q] >= baseline nos 3; todas as suítes verdes em python3 3.13 e /usr/bin/python3 3.9.6" \
  --max-rounds 2 --max-hours 5 --max-parallel 3
ac load intake
ac gate stop --by founder --decision approve       # o usuário aprova o critério
ac done intake
```

Decisões e por quê:

- **`--work` fora do alvo.** O prompt usa `campanhas/campanha-iter5`, que fica fora de
  `codebase-specialists/` (o repositório versionado). SKILL.md: a campanha "nunca dentro do alvo medido".
- **Escopo (escolha deste exemplo).** O prompt só diz "versione SÓ a pasta codebase-specialists/". Os
  globs acima deixam `evals/` de fora de propósito: é onde mora o oráculo.
- **`--max-rounds 2`.** "Máx. 2 rodadas." Com o passo 0 como rodada 0, as rodadas 1 e 2 são de correção.
- **`--max-parallel 3`.** O prompt tem dois limites: "Execuções de avaliação UMA POR VEZ" e "frentes de
  correção ≤3". O `ac.py` guarda um número só e não o aplica; o "uma por vez" das avaliações vai como
  instrução no despacho.
- **`--max-hours 5`.** O prompt fala em "limite de uso de 5 h" e "ao passar de ~50% da janela de uso, pare
  num checkpoint (handoff em disco) e pergunte se continua". O script não mede horas: isso é disciplina
  do orquestrador (`done --handoff` + pergunta ao usuário).
- **Critério.** Copiado do prompt; inclui a parte "Sem progresso em 2 rodadas → escalar", que é regra de
  decisão (vale igual à do SKILL.md).

## oraculo

"Oráculo (já existe — calibre, não reconstrua)."

- Corretor: `evals/check_run.py <alvo> <GROUND_TRUTH> --mode setup --out grading.json`, que grava
  `summary.quality` e `summary.structure` — exatamente o formato que `ac.py run record --grading` lê.
- Gabaritos: `evals/fixtures/<py-billing|ts-shop|go-polyglot>/GROUND_TRUTH.json`.
- Resumo Q×S: `evals/summarize.py`. "[Q] é a métrica comparável com o baseline; [S] é da skill" — é a
  separação de L02 já existente.

```bash
ac load oraculo
ac set oracle.command "python3 evals/check_run.py <alvo> evals/fixtures/<fixture>/GROUND_TRUTH.json --mode setup --out grading.json"
# oraculo.2: subagente com o prompt verificador_oraculo → JSON → set oracle.calibration
ac set oracle.calibration '{"vazio":..., "bom":..., "configs":2, "conferencias":[...]}'
ac set oracle.split '{"quality":"[Q] — comparável com baseline","structure":"[S] — artefatos da skill"}'
ac oracle freeze \
  --file ~/.claude/skills/codebase-specialists/evals/check_run.py \
  --file ~/.claude/skills/codebase-specialists/evals/summarize.py \
  --file ~/.claude/skills/codebase-specialists/evals/fixtures/py-billing/GROUND_TRUTH.json \
  --file ~/.claude/skills/codebase-specialists/evals/fixtures/ts-shop/GROUND_TRUTH.json \
  --file ~/.claude/skills/codebase-specialists/evals/fixtures/go-polyglot/GROUND_TRUTH.json
ac done oraculo
```

Decisões e por quê:

- **Calibrar mesmo sabendo que o corretor "funciona".** O prompt avisa: "já se sabe que o corretor erra
  em negação ('X não existe' lido como afirmação) — conferir à mão ≥2 asserções por configuração antes
  de confiar". O ts-shop da iteração 4 é a prova: 12/13 no corretor, 13/13 real. Esperado: alguma
  conferência dê `correto: false` → `oraculo.2` recusa → o conserto do corretor vai por
  `oracle change --why --evidence` (L01, L08), **não** por uma frente. Depois disso, as medições
  anteriores devem ser recorrigidas.
- **Congelar os gabaritos junto.** Só o que está em `--file` é protegido pelo hash e pelo `plan check`.
- `configs: 2` (com skill e baseline) → mínimo 4 conferências.

## base — "Passo 0"

"Fechar a medição pendente da iteração 4 (barato, ANTES de corrigir)."

- Retomar `iteration-4/py-billing-setup-vague/with_skill/target` e
  `iteration-4/go-polyglot-setup-vague/with_skill/target`, **uma por vez**, cada uma num subagente:
  "No repositório <target>, rode `/codebase-specialists retomar`; sem humano: aprovações com
  `--by eval-sim --simulated`; liste TODO contorno manual em <outputs>/notes.md sob 'CONTORNOS MANUAIS'."
- Registrar as duas como rodada 0, junto com o ts-shop já concluído.
- Baselines: "iteration-1/<eval>/without_skill → [Q] 9/13, 10/13, 10/13 (não rode de novo)".

```bash
ac load base
# para cada alvo, depois de rodar check_run.py e gerar grading.json:
ac run record --round 0 --config sistema --alvo ts-shop    --dir <dir> --grading <grading.json> --minutes 33 --tokens 269008 --decision GO --simulated
ac run record --round 0 --config sistema --alvo py-billing --dir <dir> --grading <grading.json> --minutes <m> --tokens <n> --decision <...> --simulated
ac run record --round 0 --config sistema --alvo go-polyglot --dir <dir> --grading <grading.json> --minutes <m> --tokens <n> --decision <...> --simulated
# baselines já medidos na iteração 1 (sem rodar de novo): registre com o grading existente, se houver,
# ou dispense com motivo:
ac run record --round 0 --config baseline --alvo <alvo> --dir <iteration-1/.../without_skill> --grading <grading.json>
#   ou
ac run waive --round 0 --config baseline --why "baselines da iteration-1 ([Q] 9/13, 10/13, 10/13), não re-executados por orçamento"
ac done base --handoff "rodada 0: [Q] e contornos por alvo; baseline 9/10/10 de 13"
ac round new
```

Decisões e por quê:

- **Medir antes de corrigir** (L04): sem fechar a iteração 4, não há rodada 0 contra a qual medir o Δ.
- **Retomar, nunca do zero** (L07): "Execuções interrompidas: retome pelo disco".
- **Uma por vez** (L06 + orçamento de uso): avaliação é cara (~25–35 min cada, nas notas do plano).
- **`--simulated`** (L13): todas as aprovações do executor são "eval-sim"; o veredito sai `GO (simulado)`.
- **Baseline reaproveitado.** Se for só dispensado (`waive`), o `results compare` não terá as linhas de
  baseline; registrá-lo com o grading mantém "baseline ao lado" na tabela (L04). Se o grading da
  iteração 1 foi feito com uma versão anterior do corretor, ele precisa ser recorrigido com o oráculo
  congelado antes de registrar.
- **Atenção ao registrar:** `run record` sem `--grading` deixa uma linha sem nota que bloqueia `base.3`
  para sempre (ver [07-limites.md](07-limites.md)).

## diagnostico (rodada 1)

Os defeitos já estão diagnosticados ("não refaça o diagnóstico; leia"). Tradução para `DEFEITOS.json5`
(classe e evidência vêm do arquivo da iteração 4; `evidencia` deve apontar para os `notes.md` exatos):

| ID | Prioridade | Classe | Defeito (resumo literal) |
|---|---|---|---|
| D-1-01 | P0 | sistema | `--fast` pula rt.2/rt.4, a única checagem de existência antes do verify → G2 falha no verify |
| D-1-02 | P0 | sistema | verify aceita G4 com cartões alterados depois do exame (exame deve ficar ligado ao hash do cartão) |
| D-1-03 | P1 | sistema | sem comando que monta os pacotes de spot-check, core e juízes POR-QUÊ (executor escreveu scripts) |
| D-1-04 | P1 | sistema | `probes exam-pack` grava `answer_file` em conflito com o caminho de respostas de `prompts.json5` |
| D-1-05 | P2 | **oraculo** | corretor [Q][STALE]: negação ainda não reconhecida |

Decisão: **D-1-05 é classe `oraculo`** (L08). Não vira frente; vira `oracle change` com a conferência
manual do ts-shop ('playwright' citado para dizer que NÃO existe) como evidência, e as medições da
rodada 0 são recorrigidas.

## plano

```json5
{parada: "<copiado do intake>",
 decisoes: [ /* decisões de produto novas, se houver → gate plan:<id> */ ],
 contrato: {
   "spotcheck-pack": "facts spotcheck pack",
   "core-pack": "team core pack",
   "why-pack": "panel why pack",
   "why-tally": "panel why tally",
 },
 frentes: [ /* ≤3, globs disjuntos dentro do escopo, nenhuma em evals/ */ ]}
```

Decisões e por quê:

- **Contrato de nomes.** O P1 D-1-03 propõe quatro comandos novos (`facts spotcheck pack`,
  `team core pack`, `panel why pack`, `panel why tally`). Se duas frentes os citam (código e doc), o nome
  tem de estar no `contrato` antes do despacho (L09: "docs citavam flags que a CLI não tinha").
  D-1-04 é literalmente um conflito de nome entre dois arquivos — "um só caminho" tem de virar contrato.
- **Decisões já tomadas não reabrem.** O `PLANO-ITER4.json5` já fixou: "--fast é o padrão; GO exige todos
  especialistas; rascunhos em .specialists/tmp/; lotes ≤3 em primeiro plano". Decisão de produto nova
  passa por `ac gate plan:<id>`.
- **Frentes disjuntas.** A divisão concreta depende de quais arquivos cada defeito toca — o `plan check`
  recusa sobreposição e qualquer glob que pegue `evals/` (onde está o oráculo congelado).

## correcao e integracao

- Frentes ≤3 em paralelo, prompt `frente_correcao`, `{runtimes}` = `python3` (3.13) e `/usr/bin/python3`
  (3.9.6) — os dois do critério de parada.
- Integração: o orquestrador roda todas as suítes nos dois runtimes (L10: "regressões apareceram só em
  Python 3.9") antes de `ac set integration.tests_green true`; `ac oracle verify`.
- **Commit:** portão humano, "só a pasta codebase-specialists/ do repo ~/.claude/skills; nunca o workspace,
  que tem repositórios git aninhados". `ac gate commit --by founder --decision approve`.

## remedicao

Mesmas três tarefas (`--fast`, "setup vague"), mesmo oráculo congelado, uma execução por vez, sistema
congelado durante a medição; cada execução com `notes.md` e a seção "CONTORNOS MANUAIS".

```bash
ac load remedicao
ac run record --config sistema --alvo py-billing  --dir <dir> --grading <grading.json> --minutes <m> --tokens <n> --decision <...> --simulated
ac run record --config sistema --alvo ts-shop     ...
ac run record --config sistema --alvo go-polyglot ...
ac done remedicao
```

## decisao

```bash
ac load decisao
ac results compare
ac set decision "<parar|continuar|escalar — motivo>"
ac set report "<relatório>"
ac done decisao
```

Contra o critério, item a item:

| Item do critério | De onde vem o número |
|---|---|
| ≥2/3 GO | coluna "decisão" do `results compare` (lembrando que `GO (simulado)`) |
| zero contornos manuais | seção "CONTORNOS MANUAIS" dos `notes.md` — **não** está no `ac.py` |
| [Q] ≥ baseline nos 3 | coluna "qualidade" de cada alvo × linha baseline do mesmo alvo |
| suítes verdes em 3.13 e 3.9.6 | `integration.tests_green` (declarado após rodar) |

- **parar** se tudo cumprido;
- **continuar** (`round new` → rodada 2) se houve progresso e sobra orçamento;
- **escalar** se sem progresso em 2 rodadas ou se a rodada 2 terminar sem cumprir — o `round new`
  recusará a rodada 3 ("orçamento: máximo de 2 rodadas atingido — escale ao usuário").

## Entrega pedida pelo prompt

Relatório curto: decisão; tabela [Q]×[S]×custo com baseline; contornos manuais restantes; o que o oráculo
pode estar favorecendo; e uma seção **"lições para a auto-correcao"** — o que no ciclo dela ajudou ou
atrapalhou nesta primeira campanha real. Essa seção é a forma prevista de validar a própria skill (ver
[07-limites.md](07-limites.md)).
