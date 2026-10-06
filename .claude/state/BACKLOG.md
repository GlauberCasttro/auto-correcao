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
| AC-13 | hook nega comandos legítimos com `$AC` (variável atribuída no próprio comando) + subcomando; `$(...)` citando `hook_aprovacao.py` | 2026-10-05 | resolver variável atribuída no mesmo comando; nome de arquivo citado não é código |
| — | trocar o critério de parada (`stop`) não invalida o portão `stop` | PENDENTE v0.5 | portão `stop` volta a pendente quando `stop` muda |
| L19–L23 | lições novas a gravar em `references/licoes.json5` (L19 sobreajuste a mutantes vistos; L20 100% dos testes ≠ força; L21 testes gerados do contrato; L22 oráculo antigo segura o produto; L23 portão em cópia limpa) | PENDENTE v0.5 | entradas no licoes.json5 com fonte; testes que validam o json5 verdes |

## P2
| Id | Item | Origem | Critério de pronto |
|---|---|---|---|
| AC-16 | `done decisao` exige `frase conferir` mesmo quando a conferência já foi feita junto das aprovações? **Verificado por leitura** (`chk_frase_conferida`, ac.py:756): exige um `frase-conferida` POSTERIOR à última aprovação não simulada — se o script de aprovação termina com a conferência, passa. Exige também quando não há nenhuma aprovação (sem `frase-conferida` algum). Não executado | uso 2026-10-05/06 | teste: aprovações + conferir no mesmo script ⇒ `done decisao` passa; campanha sem aprovação ⇒ decidir (founder) se exige |
| — | `results compare` não separa base × remedição por rodada | PENDENTE v0.5 | coluna base × remedição |
| AC-11 | documentar a migração v0.3→v0.4 (`frase conferir --assinar-legado`) | rollout v0.4 | seção em docs/ |
| — | regra de processo: cada achado de verificador/mutação que reabre correção = rodada nova no ac.py | onda1 | escrito em docs + checado (se der) |

## Harness de desenvolvimento
| Prio | Item | Critério de pronto |
|---|---|---|
| P0 | revisão do founder do projeto público; depois o orquestrador cria o link `~/.claude/skills/auto-correcao` → projeto, o remoto e faz o push | `readlink ~/.claude/skills/auto-correcao` aponta para o projeto; hook global `--selftest` verde pelo caminho do link |
| P1 | `guard-privacidade.sh --install-hooks` em cada clone (o hook do git não é versionado) | `.git/hooks/pre-commit` e `commit-msg` presentes |
| P2 | `portar.sh` confere campanhas só com `status`; não reconfere tags (`frase conferir` exige a senha) | decidir se vale um modo de conferência sem senha só de formato |

## Resolvidos (referência)
AC-01..AC-07 tratados na v0.3/v0.4 (`5800ed2`, `6e5dc67`; AC-02 e AC-05 citados no código), AC-04 virou o hook global.
