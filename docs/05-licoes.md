# 05 — Lições (L01–L18)

Fonte: `references/licoes.json5`. Origem declarada no arquivo: laboratório de 4 iterações refinando a
skill **codebase-specialists** (2026-10-01..03), 3 repos-fixture com gabarito oculto, ~25 execuções
avaliadas. A codebase-specialists é só o caso de origem; as lições valem para qualquer sistema.

O SKILL.md manda ler as lições uma vez, antes da primeira etapa, e consultá-las antes de planejar uma
rodada. Abaixo, organizadas por tema, com a evidência literal e **como cada uma virou regra ou check** —
distinguindo o que o `ac.py` aplica mecanicamente do que fica como instrução para o modelo.

Legenda da coluna "Aplicação": **mecânica** = um check ou comando recusa; **parcial** = parte é
mecânica; **texto** = só instrução (SKILL.md, prompts) — depende do modelo cumprir.

## Resumo

| ID | Tema | Lição (curta) | Aplicação |
|---|---|---|---|
| L01 | oraculo | O corretor mente; confira amostra à mão e rode saída vazia | mecânica (`oraculo.2`) |
| L02 | oraculo | Separe qualidade de estrutura | parcial (`oraculo.3`, `results compare`) |
| L03 | checks | Check prova o EFEITO, não que o subcomando rodou | texto + testes do `ac.py` |
| L04 | medicao | Não altere o sistema medido; meça baseline | parcial (`base.2`) |
| L05 | isolamento | Execuções paralelas não compartilham rascunho | texto (prompt) |
| L06 | concorrencia | Lotes ≤3, espere o lote, cada um grava o seu | texto (prompt) |
| L07 | janelas | Checkpoint em disco, retomada sem repetir | mecânica (estado em disco, `load`/`status`) |
| L08 | diagnostico | Classifique antes de corrigir | parcial (`diagnostico.2`) |
| L09 | plano | Escrita disjunta + contrato de nomes | parcial (`plan check`) |
| L10 | correcao | Teste falha antes/passa depois; integrador roda tudo | texto + flag declarada (`integracao.1`) |
| L11 | decisao | Mesmo estado → mesmo veredito | texto |
| L12 | custo | Rode a versão barata ao lado da completa | texto |
| L13 | autonomia | Aprovação simulada aparece no veredito | parcial (`--simulated`) |
| L14 | parada | Critério de parada fixado antes | mecânica (`intake.3`) |
| L17 | paralelismo | Campanhas com escrita disjunta podem se sobrepor; colisão detectada por `overlap` | mecânica (`ac.py overlap`) |
| L18 | autonomia | `--by` não prova ator: frase do founder + tag por aprovação + `frase conferir` + hook + auditoria, com limite honesto | mecânica parcial (`gate`/`preauth`/`frase`, `hook_aprovacao.py`) |

---

## Tema 1 — A medida (oráculo, baseline, custo)

### L01 · oraculo — o corretor mente

- **Lição:** "O corretor mente com frequência. Antes de confiar num número, confira à mão uma amostra e
  rode uma saída vazia."
- **Evidência:** "baseline dava 1/44 porque o corretor só lia arquivos do próprio sistema; G4 'não medido'
  por nome de campo divergente; orçamento de cartão medido de dois jeitos; falsos positivos de negação
  ('driver' não se usa)."
- **Regra:** "calibração obrigatória (oraculo.2) e revalidação quando o sistema muda formato de saída."
- **Como virou check:** `oraculo.2` → `calibration` (vazio ≤0.10, bom ≥0.90, ≥2 conferências por
  configuração, todas corretas e com evidência). A revalidação após mudança de formato **não** é
  automática. Ver [02-oraculo.md](02-oraculo.md).

### L02 · oraculo — qualidade × estrutura

- **Lição:** "Separe qualidade (neutra de formato, comparável com baseline) de estrutura (artefatos do
  sistema). Misturar infla o ganho."
- **Evidência:** "agregado misturado deu +0,56; qualidade real era +0,23 a +0,31."
- **Regra:** "resumo sempre em duas colunas."
- **Como virou check:** `oraculo.3` → `require oracle.split` (exige que a separação esteja registrada);
  `run record` guarda `quality` e `structure` separados; `results compare` imprime colunas e médias
  separadas. O conteúdo de `oracle.split` não é validado.

### L04 · medicao — sistema congelado e baseline

- **Lição:** "Não altere o sistema enquanto ele está sendo medido; e baseline sem o sistema é o único
  jeito de saber se ele vale o custo."
- **Evidência:** "o baseline sem skill entregava times bons em 7 min; a skill custava 4–8× e ganhava 3–4
  itens de 13."
- **Regra:** "sistema congelado na remedição; custo sempre ao lado da qualidade."
- **Como virou check:** `base.2` → `runs --round 0 --config baseline --min 1 --or-waived` (baseline ou
  dispensa justificada). `results compare` mostra tokens e minutos ao lado. "Sistema congelado" é
  instrução (objetivo de `remedicao`); o script não confere hash do sistema.

### L12 · custo — artefato ou processo?

- **Lição:** "Meça se o valor está no artefato ou no processo: rode a versão barata do sistema ao lado da
  completa."
- **Evidência:** "modo rápido entregou a mesma qualidade (13/13) em menos da metade do tempo; o processo
  longo só mudava a certificação."
- **Regra:** "quando o sistema tem modos, a remedição inclui o modo barato."
- **Como virou check:** nenhum. `--config` aceita qualquer nome (`formatos.json5`:
  `config: "sistema|baseline|<modo>"`), então o modo barato é registrado como outra config. Note que
  `results compare` faz a média de **todas** as configs não-baseline juntas.

## Tema 2 — O mecanismo (checks, decisão, parada, autonomia)

### L03 · checks — prove o efeito

- **Lição:** "Um check que testa 'o subcomando rodou' passa sem a etapa acontecer. Check prova o EFEITO."
- **Evidência:** "etapa fechava com nada promovido ao núcleo; approve inalcançável por check que ignorava
  não-especialista aceito."
- **Regra:** "todo check novo nasce com um teste em que o subcomando passa e o efeito não acontece."
- **Como virou regra:** cabeçalho de `ciclo.json5` ("check: comando ac.py (sem prefixo) que prova o
  EFEITO da sub-etapa, não que um subcomando rodou"); `scripts/tests/test_ac.py` ("cada um prova uma
  trava da skill (efeito, não só 'o comando rodou')"). A regra "todo check novo nasce com um teste" é
  disciplina de quem mantém a skill — nada a força. Vale também para checks que você escrever no
  sistema-alvo.

### L11 · decisao — mesmo estado, mesmo veredito

- **Lição:** "O mesmo estado tem de dar o mesmo veredito em qualquer alvo; regra de decisão ambígua
  produz GO num lugar e NO-GO noutro."
- **Evidência:** "não-especialista aceito virou GO num alvo e NO-GO noutro."
- **Regra:** "regra de decisão escrita e testada com o caso de borda."
- **Como virou regra:** texto. Aplica-se principalmente ao **sistema-alvo** (a regra de GO/NO-GO dele) e à
  decisão parar/continuar/escalar da campanha, que o `ac.py` não calcula.

### L13 · autonomia — simulado é simulado

- **Lição:** "Aprovação simulada precisa aparecer no veredito, não numa nota de rodapé."
- **Evidência:** "GO com todas as aprovações 'eval-sim' lido como aprovado."
- **Regra:** "veredito traz 'GO (simulado)' quando aplicável."
- **Como virou check:** `gate --simulated` grava `simulated: true` e imprime "(simulado)";
  `run record --simulated` faz `results compare` mostrar `GO (simulado)`; o prompt `executor_rodada`
  exige "Aprovação simulada deve aparecer como simulada no relatório"; o SKILL.md: "Diga quando uma
  aprovação foi simulada". Porém um portão simulado **conta como aprovado** nos checks e `status` não o
  destaca.

### L14 · parada — critério antes

- **Lição:** "Sem critério de parada fixado antes, o laço vira 'mais uma rodada' indefinidamente."
- **Evidência:** "o founder perguntou se seria a última; o critério foi escrito só na iteração 4."
- **Regra:** "intake.3 exige critério numérico aceito pelo usuário."
- **Como virou check:** `intake.3` → `require stop gate:stop` (texto do critério + portão `stop`
  aprovado). Que o critério seja **numérico** não é verificado; `plan check` também exige `parada` no PLANO.

## Tema 3 — A execução (isolamento, concorrência, janelas)

### L05 · isolamento

- **Lição:** "Execuções paralelas que compartilham rascunho contaminam umas às outras."
- **Evidência:** "~10 comandos de uma execução rodaram contra o alvo de outra via script num scratchpad
  comum."
- **Regra:** "cada execução tem diretório próprio; temporários dentro dele."
- **Como virou regra:** `base.1` ("execuções isoladas do sistema (diretório próprio, temporários dentro
  dele)"); prompt `executor_rodada` ("cópia isolada só sua; temporários SÓ dentro de {alvo_dir} ou
  {out_dir}"). `run record --dir` registra o diretório, mas nada confere o isolamento.

### L06 · concorrência

- **Lição:** "Muitos subagentes ao mesmo tempo batem no limite da sessão e da API; redespachar antes do
  lote terminar cria duplicatas que sobrescrevem trabalho."
- **Evidência:** "8 redatores simultâneos → 429; redator duplicado sobrescreveu cartão já gravado; revisor
  reescreveu arquivos de outros."
- **Regra:** "lotes ≤3; espere o lote; cada subagente grava só o próprio arquivo; o orquestrador grava o
  estado em série."
- **Como virou regra:** `limits.max_parallel_default: 3` em `ciclo.json5`; `--max-parallel` no `init`;
  prompts ("no máximo {max_paralelo} subagentes por lote, em PRIMEIRO PLANO; espere o lote"; "cada
  subagente grava SÓ os arquivos do seu escopo"). Nenhum desses limites é aplicado pelo script.
  O estado é gravado só pelo orquestrador, via `ac.py`.

### L07 · janelas

- **Lição:** "Execução longa não cabe numa janela; precisa de checkpoint no disco e retomada sem repetir
  trabalho. Lotes em segundo plano fazem o executor devolver o controle a cada lote."
- **Evidência:** "execuções paravam no meio; com handoff.md + estado em disco retomaram sem perda; lote em
  primeiro plano eliminou devoluções."
- **Regra:** "estado em arquivo; lote curto em primeiro plano; retomar com 'continue' uma única vez
  (mensagens enfileiradas viram novos checkpoints)."
- **Como virou check:** é a razão de existir do `ac.py`: `state.json` + `ledger.jsonl`; `load` entrega um
  pacote limitado (6000 caracteres) com o handoff da etapa anterior; `status` retoma; o prompt do executor
  manda gravar `{out_dir}/handoff.md` com o próximo comando quando o contexto pesar. A `remedicao` manda
  "retomar pelo disco se caírem".

## Tema 4 — A correção (diagnóstico, plano, testes)

### L08 · diagnostico — classifique antes

- **Lição:** "Classifique o defeito antes de corrigir: sistema, oráculo, ambiente ou executor. Metade dos
  NO-GO vinha do oráculo ou do gerador de provas, não do sistema."
- **Evidência:** "5 agentes 'reprovados' só por perguntas de sha sem .git no exame; 13 respostas certas
  reprovadas por regex de 'nenhum'."
- **Regra:** "só defeito de classe sistema vira frente de correção."
- **Como virou check:** `diagnostico.2` → `defects --classified` (classe ∈ `sistema|oraculo|ambiente|executor`,
  prioridade ∈ `P0..P3`). "Só classe sistema vira frente" **não** é conferido (o `plan check` não cruza
  `frentes[].defeitos` com a classe).

### L09 · plano — disjunção e contrato

- **Lição:** "Frentes paralelas precisam de arquivos disjuntos E de um contrato de nomes fixado antes;
  senão o código, a doc e o corretor divergem."
- **Evidência:** "docs citavam flags que a CLI não tinha; teste de documentação com lista de pendentes
  resolveu a transição."
- **Regra:** "PLANO tem `contrato`; um teste confere que todo comando citado na doc existe."
- **Como virou check:** `plano.1` → `plan check` (disjunção por `globs_overlap`, ninguém escreve no
  oráculo). O campo `contrato` faz parte do schema mas não é exigido pelo check. Ver
  [03-frentes-paralelas.md](03-frentes-paralelas.md).

### L10 · correcao — teste antes/depois, todos os runtimes

- **Lição:** "Cada defeito ganha teste que falha antes e passa depois; o integrador roda tudo nos runtimes
  suportados."
- **Evidência:** "regressões apareceram só em Python 3.9 (doctest) e foram pegas na integração."
- **Regra:** "integração roda todas as suítes em todas as versões."
- **Como virou check:** prompt `frente_correcao` ("escreva um teste de regressão que FALHA antes;
  corrija; o teste passa ... rode todas as suítes do seu escopo em {runtimes}"); `integracao.1` →
  `require integration.tests_green`, que o orquestrador declara com `set` depois de rodar as suítes.

---

## v0.3 — L17 e L18

(L15 e L16 estão em `references/licoes.json5`.)

### L17 · paralelismo — campanhas que se sobrepõem

- **Lição:** campanhas com áreas de escrita disjuntas podem se sobrepor (oráculo da próxima preparado
  enquanto a atual integra).
- **Evidência:** campanhas iter8 e ac-v03 em sequência, oráculo parado à espera da integração.
- **Regra / check:** `ac.py --work A overlap --other B` (exit 1 em colisão, citando o glob).

### L18 · autonomia — aprovação humana

- **Lição:** texto `--by` não prova ator. Terminal + desafio também não (v0.4: um agente com `pty.fork` lê e
  redigita o desafio). Só um segredo do founder separa os dois.
- **Evidência:** iter8 e ac-v03: gate/preauth aceitos com `--by` livre; `--simulated` contava como aprovado.
- **Regra / check:** tty + frase (`FRASE ...:`, sem eco) em `gate`/`preauth`, com tag HMAC por aprovação;
  `ac.py frase conferir` antes de `done decisao`; `scripts/hook_aprovacao.py`; `$AC_AUDIT_LOG`.
  Limite honesto: um agente que troca o `frase.json` só é pego quando o founder digita a frase verdadeira
  no `frase conferir`.
