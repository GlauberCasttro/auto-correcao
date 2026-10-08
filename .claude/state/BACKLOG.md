# BACKLOG — auto-correcao

Prioridade: P0 (corrompe medição/aprovação ou já mordeu em uso) · P1 (atrito real recorrente) · P2 (melhoria).
Origens: `docs/PENDENTE.md` (v0.5), registro de defeitos v0.3 achados na campanha da codebase-specialists
(`auto-correcao-v03-defeitos.md`, ficou na máquina de origem), uso da skill em 2026-10-05/06. "Pronto" = teste de regressão no oráculo da frente que falha antes e passa depois,
portão verde nos 2 Pythons, commit conferido × portão.

## P0
| Id | Defeito | Origem | Critério de pronto |
|---|---|---|---|
| AC-10 (grave) | `round new` abriu a rodada seguinte com `remedicao`/`decisao` da anterior ABERTAS | onda1, 2026-10-05 | `round new` recusa (exit 1) enquanto qualquer substage `per_round` da rodada atual não estiver concluída |
| AC-14 | `oracle change --file X` SUBSTITUI a lista congelada por só X: os outros arquivos do oráculo deixam de ser vigiados, em silêncio. Confirmado por leitura (`cmd_oracle`: `files = a.file or o["files"]`) | uso 2026-10-05/06 | `--file` acrescenta/atualiza; remover arquivo do oráculo exige opção explícita (ex. `--remove X`) + `--why`; teste: change com um arquivo mantém os demais no hash |
| AC-08 | `oracle change` re-hasheia TODOS os arquivos como estão no disco e absorve em silêncio uma edição indevida (corretor) | campanha-iter9, 2026-10-04 | change mostra o diff por arquivo desde o último freeze e recusa arquivo alterado não declarado em `--file` |
| AC-12 | `ac set scope` muda o escopo de escrita depois dos portões aprovados, sem why nem evento. Em 2026-10-05/06 foi usado várias vezes LEGITIMAMENTE (escopo esquecido no init) — não pode virar proibição | 2026-10-05 + uso 2026-10-06 | `scope` protegido após o intake; mudança só com `--why` (evento `scope-change` no ledger, visível no status) e o portão `stop`/plano volta a pendente |

## P1
| Id | Defeito | Origem | Critério de pronto |
|---|---|---|---|
| AC-09 | `remedicao.1` recusa a execução registrada no MESMO segundo do `done correcao.1` (comparação estrita com resolução de 1 s). **Repetiu em 2026-10-05/06** | onda1 + uso | ordem pelo ledger (posição), não por timestamp; teste com os dois eventos no mesmo segundo |
| AC-15 | hook global com falsos positivos: nega `sed`/`sh -c`/heredoc/mensagem de commit que contêm "gate"/"approve"/"senha" junto de ac.py ou de nome de script de aprovação, mesmo sem executar aprovação. (Verificar "senha": não está na lista de palavras do hook atual; o gatilho provável é `aprovar-*.sh`/`frase` na mesma linha.) Continuação do AC-13 | uso 2026-10-05/06; repetiu na montagem do projeto (2026-10-06: `python3 - <<EOF` que só EDITAVA o texto de `script-aprovacao.py` foi negado) | casos reais viram SELF_ALLOW do `--selftest` + testes; nenhum SELF_DENY existente passa a permitir. Frente SEPARADA (portar o hook muda o hook global na hora) |
| AC-17 | `ac.py init` numa campanha que JÁ EXISTE re-inicializa em silêncio: sobrescreve problem/stop/scope de outra frente; um oracle freeze e aprovações gravados depois ficam presos ao estado errado | 2026-10-06: duas sessões abriram `campanhas/iter18` no mesmo projeto com minutos de diferença; a dona recuperou com cópia do estado + re-init + reaprovação | `init` em diretório com `.auto-correcao/state.json` recusa (exit≠0) citando a campanha existente; `--force` só com motivo registrado no ledger e invalidando portões já aprovados; teste |
| AC-13 | hook nega comandos legítimos com `$AC` (variável atribuída no próprio comando) + subcomando; `$(...)` citando `hook_aprovacao.py` | 2026-10-05 | resolver variável atribuída no mesmo comando; nome de arquivo citado não é código |
| — | trocar o critério de parada (`stop`) não invalida o portão `stop` | PENDENTE v0.5 | portão `stop` volta a pendente quando `stop` muda |
| AC-24 | Hook: 2 brechas PRÉ-EXISTENTES no caminho Bash (também no hook antes da win-hook): `echo "$(python3 ac.py gate stop)"` (leitor com `$(…)` entre aspas não é analisado) e `python3 ac.py --work c > /dev/null gate stop` (redirecionamento no meio quebra o segmento) são PERMITIDOS; no PowerShell os equivalentes já são negados | frente win-hook (f-hook), 2026-10-08 | os 2 casos (e variações) negados no selftest + oráculo; os 135 casos atuais com o mesmo veredito |
| AC-25 | `ac.py` save: `os.replace(state.json.tmp → state.json)` sem retentativa dá `PermissionError` intermitente no Windows/drvfs (antivírus/indexador segurando o arquivo); visto no WSL com temporários em /mnt/c (test_ac RoundTest, test_v04 R4) | integração da win-hook, 2026-10-08 | retentativa curta com backoff só para PermissionError no replace; teste com replace falhando 2x e passando na 3ª |
| AC-20 | Harness de dev (`.claude/tools`) não roda nativo no Windows: `subprocess(["python3", …])` (atalho não-.exe ⇒ FileNotFoundError) e `["bash", …]` (cai no bash do WSL) em frente.py:126,129,170; `python3`/`/usr/bin/python3` fixos em portao/verificar-harness/script-aprovacao; script de aprovação gerado em modo texto. Na win-motor o processo inteiro rodou pela WSL por isso | campanha win-motor 2026-10-08 | `frente.py open/close`, `portao.sh` e `script-aprovacao.py` rodam no Git Bash do Windows com `python`; testes do harness verdes no Windows e no WSL |
| L19–L23 | lições novas a gravar em `references/licoes.json5` (L19 sobreajuste a mutantes vistos; L20 100% dos testes ≠ força; L21 testes gerados do contrato; L22 oráculo antigo segura o produto; L23 portão em cópia limpa) | PENDENTE v0.5 | entradas no licoes.json5 com fonte; testes que validam o json5 verdes |

## P2
| Id | Item | Origem | Critério de pronto |
|---|---|---|---|
| AC-16 | `done decisao` exige `frase conferir` mesmo quando a conferência já foi feita junto das aprovações? **Verificado por leitura** (`chk_frase_conferida`, ac.py:756): exige um `frase-conferida` POSTERIOR à última aprovação não simulada — se o script de aprovação termina com a conferência, passa. Exige também quando não há nenhuma aprovação (sem `frase-conferida` algum). Não executado | uso 2026-10-05/06 | teste: aprovações + conferir no mesmo script ⇒ `done decisao` passa; campanha sem aprovação ⇒ decidir (founder) se exige |
| — | `results compare` não separa base × remedição por rodada | PENDENTE v0.5 | coluna base × remedição |
| AC-11 | documentar a migração v0.3→v0.4 (`frase conferir --assinar-legado`) | rollout v0.4 | seção em docs/ |
| — | regra de processo: cada achado de verificador/mutação que reabre correção = rodada nova no ac.py | onda1 | escrito em docs + checado (se der) |
| AC-19 | Windows: `msvcrt.getwch` devolve U+00E0 tanto para o prefixo de tecla estendida quanto para "à"; frase com "à" não confere entre posix e Windows (falha fechada). Documentar ou resolver (ex.: `kbhit` logo após o prefixo) | frente win-motor (f-frase), 2026-10-08 | SKILL.md/docs avisam; ou teste com "à" digitado verde sem quebrar o descarte de setas |
| AC-23 | `frente.py open` grava caminhos ABSOLUTOS em `frentes.json` (`campanha`, `copia`, `ac_estavel`): no clone de qualquer máquina vaza o caminho do usuário e o `commit-state.sh` recusa (guard de privacidade). Na win-motor os 3 campos foram trocados à mão por relativos à raiz | commit do estado da win-motor, 2026-10-08 | `frente.py` grava relativo à raiz e resolve na leitura; teste: open → frentes.json sem caminho absoluto |
| AC-21 | `json5_load` do ac.py recusa `\'` dentro de string (válido em JSON5): DEFEITOS.json5 escrito à mão com `'\\'` deu `Invalid \escape` | campanha win-motor 2026-10-08 | teste com `\'` e `\\` em string json5 |
| AC-22 | Restos do Windows fora do oráculo da win-motor: `human_channel` (ac.py ~424) é código morto com `os.ttyname`; `chk_plan` usa `os.path.relpath`/`os.sep`; `fnmatch` sem caixa no Windows | ESPEC win-motor, pendências 1–2 | remover o morto; chk_plan normaliza separador; teste no Windows |
| — | Processo: na win-motor o achado D-0-10 (stdin NUL) reabriu a correção DENTRO da rodada 0 (devolvido à f-frase), não numa rodada nova; registrado no DEFEITOS e no relatório | campanha win-motor 2026-10-08 | decidir se a regra "reabre ⇒ rodada nova" vira check do ac.py |

## Harness de desenvolvimento
| Prio | Item | Critério de pronto |
|---|---|---|
| P0 | revisão do founder do projeto público; depois o orquestrador cria o link `~/.claude/skills/auto-correcao` → projeto, o remoto e faz o push | `readlink ~/.claude/skills/auto-correcao` aponta para o projeto; hook global `--selftest` verde pelo caminho do link |
| P1 | `guard-privacidade.sh --install-hooks` em cada clone (o hook do git não é versionado) | `.git/hooks/pre-commit` e `commit-msg` presentes |
| P2 | `portar.sh` confere campanhas só com `status`; não reconfere tags (`frase conferir` exige a senha) | decidir se vale um modo de conferência sem senha só de formato |

## Resolvidos (referência)
AC-01..AC-07 tratados na v0.3/v0.4 (`5800ed2`, `6e5dc67`; AC-02 e AC-05 citados no código), AC-04 virou o hook global.
win-motor (2026-10-08, `3e81f49`, branch `release/version-windows`): motor roda no Windows nativo — frase pelo console
(W1, D-0-10), cp1252 (W2), hash do oráculo neutro a CRLF (W3a), `.gitattributes` (W3b), `os.ttyname` (W4), SKILL/docs
(W5), suíte importa sem pty (W6), barra invertida no overlap (W7). Oráculo 0/24 → 24/24 em Windows e WSL.
AC-18 / win-hook (2026-10-08, `30e2da6`): hook de aprovação analisa a ferramenta PowerShell (tokenizador próprio),
interpretadores do Windows, `\`, indireções (iex/-Command/cmd /c/blocos) e nega `-EncodedCommand`; selftest 83 → 135;
docs com matcher `Bash|PowerShell`. Oráculo 1/17 e 0/17 → 17/17; prova real: sessão Claude Code com gate via
PowerShell NEGADA.
