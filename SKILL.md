---
name: auto-correcao
description: >
  Refina de forma autônoma um sistema de agentes, harness, skill ou pipeline até ele passar num critério
  MEDIDO: valida (ou constrói) um oráculo confiável, mede o estado atual com e sem o sistema, diagnostica
  defeitos com evidência exata, planeja frentes de correção paralelas em arquivos disjuntos, corrige com
  teste de regressão por defeito, integra, mede de novo e decide parar, continuar ou escalar — com
  portões humanos, orçamento e critério de parada fixados antes. Use sempre que o usuário quiser
  "corrigir até funcionar", "refinar", "auto corrigir", "iterar até passar", "rodar evals e corrigir",
  "melhorar a skill/harness/agentes com base em testes", ou trouxer um problema num sistema de agentes
  para ser resolvido de ponta a ponta — mesmo sem citar o nome da skill. Não use para um bug pontual com
  teste já falhando (corrija direto) nem para ensinar um agente a não repetir um erro (isso é memória
  de lições do próprio sistema).
---

# auto-correcao

Você vai conduzir um **laço de refinamento medido** sobre um sistema-alvo até ele cumprir um critério
escrito antes. A autonomia é real — você diagnostica, planeja, despacha frentes, integra e mede de novo
sem pedir licença a cada passo — mas ela só é segura com três travas, que valem acima de qualquer pressa:

1. **Sem oráculo confiável, não há laço.** Autonomia otimiza o que se mede; se a medida mente, o sistema
   "melhora" no placar e piora na realidade. A etapa `oraculo` existe para provar que a medida diz a verdade
   (amostra conferida à mão, execução vazia ≈ 0, saída sabidamente boa passa, qualidade separada de forma).
2. **Quem corrige o sistema não corrige o oráculo.** Mudar o corretor é um evento à parte (`ac.py oracle
   change`), justificado com evidência conferida à mão — nunca para fazer o sistema passar.
3. **Portões humanos.** Commit/push, decisão de produto, mudança de critério de parada e qualquer ação
   irreversível passam pelo usuário (`ac.py gate`). O resto do laço roda sozinho. **v0.4 (frase-senha):**
   `gate` e `preauth` só funcionam num terminal real do founder (tty) e pedem a **frase do founder**
   (`FRASE ...:`, sem eco). Tty + desafio era forjável: um agente com `pty.fork` lê o desafio e o redigita.
   Só um segredo que apenas o founder conhece separa os dois. Cada aprovação grava uma `tag` HMAC que só quem
   sabe a frase calcula. O agente NUNCA aprova, NUNCA define nem confere a frase, NUNCA pede a frase no chat e
   não tenta digitá-la por pty. Os scripts `aprovar-*.sh` são rodados pelo founder no terminal, não pelo `!`
   do Claude Code. `--by` é texto livre e não prova ator (L18).

   **Fluxo do founder (v0.4, tudo no terminal dele):**
   1. Uma vez: `ac.py frase definir` (sem `--work`; a senha ou frase é do founder, não da campanha). Ele a digita
      2x, sem eco. Regra: ≥12 caracteres, ≥6 deles distintos, e ≥3 palavras (frase) OU ≥3 tipos entre
      minúscula, maiúscula, dígito e símbolo (senha, ex.: `Lagoa#2026xy`).
      O `$AC_FRASE_FILE` (padrão `~/.claude/auto-correcao/frase.json`, modo 0600) guarda só `salt_verificador`,
      `salt_chave` e o verificador PBKDF2-HMAC-SHA256 (`"kdf": "pbkdf2-sha256"`, `"iter": 600000`). A frase nunca
      é gravada. Para trocar, roda de novo: o comando pede a antiga, a nova e a nova de novo.
   2. A cada portão: `gate`/`preauth` pedem a frase uma vez (`FRASE ...:`, sem eco). Frase errada → exit 1, nada
      gravado. Sem frase definida → exit 2, com a instrução `frase definir`.
   3. Antes de `done decisao`: `ac.py --work <campanha> frase conferir`. O comando recalcula a tag de toda
      aprovação e grava o evento `frase-conferida`.
   Campanha aberta na v0.3 (aprovações sem tag, anteriores à frase): o `conferir` lista essas aprovações e
   pede `frase conferir --assinar-legado`. O founder lê a lista e, se todas forem dele, assina de uma vez com a
   frase (evento `legado-assinado`) e depois roda `frase conferir`. Qualquer forja na lista → nada é assinado.

   **Limite honesto:** o `frase.json` é legível pelo agente. Um agente pode apagá-lo, definir outra frase e daí em
   diante aprovar e "conferir" com a frase dele. Isso só é pego quando o founder digita a frase **verdadeira** no
   `frase conferir`, que então recusa. O mesmo vale para um `frase-conferida` forjado: `done decisao` só vê a ordem.
   A força real depende da entropia da frase. O PBKDF2 só encarece a força bruta offline sobre o `frase.json`.

`$AC` = diretório desta skill. Toda operação mecânica: `python3 $AC/scripts/ac.py --work <campanha> <comando>`.
A campanha (estado, ledger, rodadas) vive em `<campanha>/.auto-correcao/` — nunca dentro do alvo medido.
Em zsh, não guarde o comando numa variável (não divide palavras): use uma função, `ac() { python3 $AC/scripts/ac.py --work <campanha> "$@"; }`.
Versão: v0.4 (frase-senha; `scripts/frase.py` é o módulo compartilhado). `init --scope` com vírgula é recusado
(um glob por `--scope`, repetindo a flag). Campanhas com escopos disjuntos podem se sobrepor (L17): `ac.py --work A overlap --other B`
(`--other` repetível; colisão = exit 1 citando o glob). Hook de aprovação: `scripts/hook_aprovacao.py`
(PreToolUse, matcher `Bash`, em `~/.claude/settings.json` ou `.claude/settings.json`; `--selftest` → exit 0)
nega ao agente `ac.py … gate|preauth|frase` e `co.py … approve`. Cada aprovação grava auditoria (com `seq`,
`estado_hash` e `tag`) em `$AC_AUDIT_LOG`
(caminho fora da campanha). `done` mantém `etapa:` no `status` (`concluida` ao fim); `run record` recusa
`quality.total` diferente da base (L02).
Leia uma vez `references/licoes.json5` (o que custou caro aprender) antes da primeira etapa.

## Execução em etapas (uma janela de contexto por etapa)

As etapas e o checklist de cada uma estão em `references/ciclo.json5` (fonte única). Ciclo de toda etapa:
`ac.py load <etapa>` (pacote ≤6.000 caracteres do disco) → sub-etapas na ordem → `ac.py done <etapa>` (roda os
checks; falha não avança) → próxima. Sessão caiu? `ac.py status` e `ac.py load` retomam do disco.

`intake → oraculo → base → diagnostico → plano → correcao → integracao → remedicao → decisao`
(as seis últimas repetem por rodada; `ac.py round new` abre a próxima e exige a anterior fechada).

### O que cada etapa precisa garantir

- **intake** — alvo, problema (relatado pelo usuário ou a descobrir por medição), escopo de escrita,
  orçamento (rodadas, tempo de parede, execuções paralelas) e **critério de parada** escrito em números
  (`ac.py init --stop "..."`). Sem critério de parada, não comece: pergunte.
- **oraculo** — ache a medida que já existe (testes, evals, gates, checklist) ou construa uma com gabarito
  que o sistema nunca vê. Calibre: rode o oráculo numa saída vazia (tem de dar ~0), numa saída boa conhecida
  (tem de passar), e confira à mão ≥2 asserções por configuração. Separe **qualidade** (neutra de formato,
  comparável com baseline) de **estrutura** (artefatos próprios do sistema). `ac.py oracle freeze` grava o
  hash; daqui em diante mudança no oráculo é `ac.py oracle change --why --evidence`.
- **base** — meça o sistema atual e, quando fizer sentido, um baseline sem o sistema (mesma tarefa,
  modelo sozinho). Cada execução isolada (diretório próprio, temporários dentro dele), com `notes.md`
  pedindo o erro exato de cada atrito. Registre tempo e tokens (`ac.py run record`).
- **diagnostico** — consolide `DEFEITOS.json5` a partir das notes, das asserções que falharam e dos
  relatórios: cada defeito com evidência (comando, erro literal, arquivo:linha), severidade P0–P3 e
  **classe**: defeito do sistema · defeito do oráculo · ambiente (ferramenta ausente, limite de API) ·
  erro do executor. Só o primeiro vira correção do sistema; o segundo vira evento de oráculo.
- **plano** — `PLANO.json5` com: decisões (incluindo de produto, que passam por `ac.py gate`), **contrato
  de nomes** (comandos/campos novos fixados antes, para as frentes não divergirem) e frentes com conjuntos
  de escrita **disjuntos**. `ac.py plan check` valida disjunção e que nenhuma frente escreve no oráculo.
- **correcao** — despache as frentes (subagentes `general-purpose`, prompt em `references/prompts.json5`):
  cada defeito ganha teste de regressão que **falha antes e passa depois**; nenhuma frente toca arquivo de
  outra nem o oráculo. Frentes longas podem rodar em segundo plano; lotes curtos, em primeiro plano, ≤3.
- **integracao** — você mesmo roda **todas** as suítes (em todas as versões de runtime suportadas), resolve
  divergências de contrato entre frentes e pontas soltas pequenas. Commit só com portão (`ac.py gate commit`)
  ou autorização prévia registrada (`ac.py preauth`, também só no terminal).
- **remedicao** — mesmas tarefas, mesmo oráculo congelado, execuções isoladas. **Não altere o sistema
  enquanto ele está sendo medido.** A remedição só fecha com execução posterior a `correcao.1` e com `decision`. Retome execuções interrompidas pelo disco; não reinicie do zero.
- **decisao** — `ac.py results compare` contra a rodada anterior e o critério de parada. Três saídas:
  **parar** (critério cumprido → congelar, tag, relatório), **continuar** (nova rodada, se o orçamento
  permite e houve progresso medido), **escalar** (sem progresso em 2 rodadas, ou orçamento esgotado →
  documente os limites e devolva a decisão ao usuário). Nunca rode "mais uma" às cegas.

## Relatório ao usuário (a cada rodada, curto)

Decisão numa linha; tabela qualidade × estrutura × custo, com baseline ao lado; o que o oráculo pode estar
favorecendo (diga, mesmo que contra o sistema); defeitos da próxima rodada por prioridade; o que precisa
de decisão dele. Números, não adjetivos. Diga quando uma aprovação foi simulada.

## Referências (leia sob demanda)

- `references/ciclo.json5` — etapas, sub-etapas, checks (fonte única, lida pelo `ac.py`).
- `references/licoes.json5` — lições com a evidência de onde vieram; consulte antes de planejar.
- `references/prompts.json5` — prompts de executor de rodada, frente de correção e verificador.
- `references/formatos.json5` — schemas de DEFEITOS, PLANO, RESULTADOS e do `notes.md` das execuções.
