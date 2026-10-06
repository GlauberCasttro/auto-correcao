# auto-correcao — documentação

> Skill global (`~/.claude/skills/auto-correcao`), versão 0.1. Conduz um **laço de refinamento medido**
> sobre qualquer sistema de agentes, harness, skill ou pipeline até ele cumprir um critério numérico
> escrito antes. O modelo interpreta e decide; o script `scripts/ac.py` guarda o estado, confere e recusa.

Esta documentação é para humanos: o dono da skill e quem for usá-la para refinar um sistema próprio.
Tudo aqui foi conferido contra `SKILL.md`, `references/*.json5` e `scripts/ac.py`; os exemplos são saídas
reais de uma campanha de demonstração rodada num diretório temporário (caminhos abreviados como `$T`).
Onde o código e o texto da skill divergem, a doc diz isso explicitamente (veja [07-limites.md](07-limites.md)).

## Índice

| Arquivo | Conteúdo |
|---|---|
| [01-maquina-de-estado.md](01-maquina-de-estado.md) | Etapas, sub-etapas, regras de transição, saídas da decisão, arquivos de estado |
| [etapas/](etapas/) | Um arquivo por etapa: [intake](etapas/intake.md) · [oraculo](etapas/oraculo.md) · [base](etapas/base.md) · [diagnostico](etapas/diagnostico.md) · [plano](etapas/plano.md) · [correcao](etapas/correcao.md) · [integracao](etapas/integracao.md) · [remedicao](etapas/remedicao.md) · [decisao](etapas/decisao.md) |
| [02-oraculo.md](02-oraculo.md) | Achar/construir o oráculo, calibração, qualidade × estrutura, congelamento, `oracle change` |
| [03-frentes-paralelas.md](03-frentes-paralelas.md) | Contrato de nomes, escrita disjunta, prompt da frente, teste que falha antes/passa depois |
| [04-referencia-cli.md](04-referencia-cli.md) | Todos os comandos do `ac.py`, flags, exit codes, exemplos |
| [05-licoes.md](05-licoes.md) | As 14 lições (L01–L14) com evidência e a regra/check em que viraram |
| [06-exemplo-campanha.md](06-exemplo-campanha.md) | A campanha real planejada (codebase-specialists, iteração 5) explicada decisão por decisão |
| [07-limites.md](07-limites.md) | O que a v0.1 ainda não faz, e divergências código × texto |

## O que é

Um protocolo em etapas, apoiado por um script de estado, para corrigir um sistema **de ponta a ponta**
sem pedir licença a cada passo: validar (ou construir) um oráculo confiável, medir o estado atual com e sem
o sistema, diagnosticar defeitos com evidência literal, planejar frentes de correção paralelas em arquivos
disjuntos, corrigir com teste de regressão por defeito, integrar, medir de novo e decidir **parar,
continuar ou escalar**.

Componentes:

```
~/.claude/skills/auto-correcao/
├── SKILL.md                 o protocolo que o modelo lê
├── references/
│   ├── ciclo.json5          etapas, sub-etapas e checks (fonte única, lida pelo ac.py)
│   ├── licoes.json5         14 lições com evidência (L01–L14)
│   ├── formatos.json5       schemas de DEFEITOS, PLANO, run e notes.md
│   └── prompts.json5        prompts: executor de rodada, frente de correção, verificador do oráculo
├── scripts/
│   ├── ac.py                estado mecânico (stdlib, Python 3.9+)
│   └── tests/test_ac.py     14 testes, cada um prova uma trava
├── evals/evals.json         4 casos de avaliação da própria skill
└── docs/                    esta documentação
```

## Quando usar

- "Corrige até funcionar", "refina", "auto corrige", "itera até passar", "roda os evals e corrige".
- Melhorar uma skill, harness, time de agentes ou pipeline **com base em testes ou evals**.
- Um problema num sistema de agentes que precisa ser resolvido de ponta a ponta, com várias rodadas.

## Quando NÃO usar

- **Bug pontual com teste já falhando** — corrija direto; o laço é caro demais para isso.
- **Ensinar um agente a não repetir um erro** — isso é memória de lições do próprio sistema, não esta skill.
- **Não há como medir e o usuário não quer construir uma medida** — sem oráculo não há laço (trava 1).
- **Não há critério de parada aceito** — a skill manda perguntar antes de começar (lição L14).

## As três travas

Valem acima de qualquer pressa (SKILL.md):

1. **Sem oráculo confiável, não há laço.** Autonomia otimiza o que se mede; se a medida mente, o sistema
   "melhora" no placar e piora na realidade. A etapa `oraculo` prova que a medida diz a verdade: saída
   vazia ≈ 0, saída sabidamente boa passa, ≥2 asserções conferidas à mão por configuração, qualidade
   separada de estrutura. Mecânica: check `calibration` (sub-etapa `oraculo.2`).
2. **Quem corrige o sistema não corrige o oráculo.** O oráculo é congelado por hash (`ac.py oracle freeze`);
   mudá-lo é um evento à parte (`ac.py oracle change --why --evidence`), justificado com conferência manual,
   nunca para fazer o sistema passar. `ac.py plan check` recusa frente cujo escopo de escrita toca o oráculo.
3. **Portões humanos.** Critério de parada, decisões de produto, commit/push e qualquer ação irreversível
   passam pelo usuário (`ac.py gate`). O resto do laço roda sozinho.

## O laço completo

```
                     ┌──────────────────────────── rodada 0 ─────────────────────────────┐
                     │                                                                   │
  usuário ──► intake ──► oraculo ──► base ──────────────────────────────┐                │
     ▲        │ gate stop   │ calibra     │ mede sistema + baseline     │                │
     │        │ (portão)    │ congela     │ (runs da rodada 0)          │                │
     │        ▼             ▼ hash        ▼                             │                │
     │                                                       ac.py round new             │
     │                                                                  │                │
     │  ┌──────────────────────────── rodada n ≥ 1 ─────────────────────▼──────────────┐ │
     │  │                                                                              │ │
     │  │  diagnostico ─► plano ─► correcao ─► integracao ─► remedicao ─► decisao      │ │
     │  │  DEFEITOS       PLANO     frentes     todas as      mesmas       results     │ │
     │  │  .json5         .json5    paralelas   suítes;       tarefas,     compare     │ │
     │  │  (classe,       (disjun-  (teste      oracle        oráculo         │        │ │
     │  │   evidência)    tas;      falha→      verify;       congelado       │        │ │
     │  │                 gate      passa)      gate commit                   │        │ │
     │  │                 plan:ID)                                            │        │ │
     │  └─────────────────────────────────────────────────────────────────────┼────────┘ │
     │                                                                        │          │
     │            ┌──────────────── parar ◄── critério cumprido ──────────────┤          │
     │            │                                                           │          │
     │            │       continuar ◄── orçamento permite + progresso medido ─┤          │
     │            │           │                                               │          │
     │            │           └──► ac.py round new ──► (próxima rodada)       │          │
     │            │                                                           │          │
     └────────────┴─── escalar ◄── 2 rodadas sem progresso ou orçamento esgotado
```

Cada etapa segue o mesmo micro-ciclo:

```
  ac.py load <etapa>  ──►  sub-etapas na ordem  ──►  ac.py done <etapa>
  (pacote do disco,        (main / sub / user)       (roda TODOS os checks;
   recusa se a etapa                                  falha = exit 1, não avança)
   anterior está aberta)
```

Sessão caiu? `ac.py status` e `ac.py load <etapa>` retomam do disco.

## Como começar (receita mínima)

```bash
AC=~/.claude/skills/auto-correcao
# em zsh, use uma função (variável com comando não divide palavras):
ac() { python3 $AC/scripts/ac.py --work <campanha> "$@"; }

ac init --target <alvo> --scope 'src/**' --problem "..." \
        --stop "critério em números" --max-rounds 2 --max-hours 5 --max-parallel 3
ac load intake
ac gate stop --by <humano> --decision approve
ac done intake
# ... siga docs/etapas/ na ordem
```

A campanha vive em `<campanha>/.auto-correcao/` — **nunca dentro do alvo medido**. Leia uma vez
`references/licoes.json5` (resumida em [05-licoes.md](05-licoes.md)) antes da primeira etapa.

## Glossário

| Termo | Significado |
|---|---|
| **Campanha** | Um esforço completo de refinamento sobre um alvo, do `init` à decisão final. Vive em `<work>/.auto-correcao/` (`state.json`, `ledger.jsonl`, `rounds/`). O `--work` é o diretório da campanha, fora do alvo. |
| **Rodada** | Um número inteiro em `state.json` (`round`). A rodada 0 mede o estado inicial (`base`); cada rodada seguinte, aberta por `ac.py round new`, repete `diagnostico → … → decisao`. Artefatos ficam em `rounds/<n>/`. |
| **Alvo** | O sistema que está sendo refinado (`--target`). Os globs das frentes são relativos a ele. |
| **Oráculo** | A medida: testes, evals com gabarito oculto, gates, checklist. Tem um comando (`oracle.command`), arquivos congelados por hash (`oracle.files`, `oracle.hash`), uma calibração (`oracle.calibration`) e a separação qualidade × estrutura (`oracle.split`). |
| **Qualidade** | Parte do placar neutra de formato, comparável com o baseline (`quality: {passed, total}`). |
| **Estrutura** | Parte do placar que mede artefatos próprios do sistema (`structure: {passed, total}`); não comparável com o baseline. |
| **Baseline** | A mesma tarefa feita sem o sistema (modelo sozinho), `--config baseline`. Mostra se o sistema vale o custo (L04). |
| **Execução (run)** | Uma aplicação do sistema (ou do baseline) a uma tarefa, em diretório isolado, registrada com `ac.py run record` em `rounds/<n>/runs.jsonl`. |
| **Defeito** | Item de `DEFEITOS.json5` com evidência, prioridade P0–P3 e classe `sistema | oraculo | ambiente | executor`. Só classe `sistema` vira frente. |
| **Frente** | Uma unidade de correção paralela, com conjunto de escrita (`escreve`, globs) disjunto das outras, despachada a um subagente. Relatório em `rounds/<n>/fronts/<nome>.md`. |
| **Contrato de nomes** | Mapa `contrato` no `PLANO.json5` que fixa comandos/campos novos antes do despacho, para as frentes não divergirem (L09). |
| **Contorno** | Desvio manual que o executor precisou fazer para a execução andar. É **defeito mesmo que tenha dado certo** (`formatos.json5` → `notes_md`, prompt `executor_rodada`). |
| **Portão (gate)** | Decisão humana registrada com `ac.py gate <nome> --by --decision approve|reject`, só em tty com a frase do founder (v0.4: tag HMAC por aprovação, conferida por `ac.py frase conferir`; hook `scripts/hook_aprovacao.py`). Nomes usados pelos checks: `stop`, `plan:<id>`, `commit`. `--simulated` marca aprovação simulada. |
| **Pré-autorização** | Chave `preauth.<nome>` gravada com `ac.py preauth` (terminal + frase do founder); satisfaz `gate-ok <nome>` sem portão (usada para commit autorizado de antemão). |
| **Check** | Expressão em `ciclo.json5` que prova o **efeito** de uma sub-etapa (L03), executada por `ac.py check` e `ac.py done`. |
| **Handoff** | Texto curto gravado por `done --handoff` em `handoff-<etapa>.txt` e mostrado pelo `load` da etapa seguinte. |
| **Ledger** | `ledger.jsonl`, um registro por mutação (`init`, `set`, `gate`, `oracle-change`, `run-record`…). |
