# auto-correcao — o que falta (atualizado em 2026-10-05)

Versão publicada: **v0.4.1** (`797dc3d`). Aprovação humana por senha do founder (PBKDF2), hook global instalado.
A lista completa dos defeitos achados em uso (registro `auto-correcao-v03-defeitos.md`, que ficou nas campanhas da
máquina de origem) está consolidada no BACKLOG do harness de desenvolvimento (`.claude/state/BACKLOG.md`).

## v0.5 — defeitos abertos (achados usando a skill)
| Id | Defeito | Correção esperada |
|---|---|---|
| AC-08 | `oracle change` re-hasheia todos os arquivos como estão no disco e absorve em silêncio uma edição indevida | mostrar o diff por arquivo desde o último freeze e recusar arquivo alterado que não foi declarado |
| AC-09 | `remedicao.1` recusa a execução registrada no mesmo segundo de `done correcao.1` | ordenar pelo ledger, não pelo timestamp |
| AC-10 (grave) | `round new` abriu a rodada seguinte com remedicao/decisao da anterior abertas | exigir todas as substages `per_round` concluídas |
| AC-11 | rollout v0.4: campanhas v0.3 sem tag | já resolvido com `frase conferir --assinar-legado`; falta documentar o processo de migração |
| AC-12 | `ac set scope` muda o escopo depois do portão aprovado, sem why nem evento | proteger `scope` depois do intake; mudar só com `--why` + evento e reabrindo o plano |
| AC-13 | o hook nega comandos legítimos com `$AC` (variável) + a palavra frase; `$(...)` citando `hook_aprovacao.py` | resolver variáveis atribuídas no próprio comando; não tratar nome de arquivo como código |
| — | trocar o critério de parada não invalida o portão `stop` | o portão volta a pendente quando `stop` muda |
| — | `results compare` não separa base de remedição | coluna base × remedição por rodada |
| — | `done decisao` exige `frase conferir` também quando não houve aprovação nova | conferir só se houver aprovação depois da última conferência (verificar o comportamento atual) |

## Lições novas a gravar em `references/licoes.json5`
- **L19:** reforçar o oráculo contra os mutantes já vistos sobreajusta. Meça com um agente novo e mutantes novos, e mostre só metade dos sobreviventes ao autor do oráculo.
- **L20:** passar 100% dos testes não mede a força dos testes. Verificador cego com reprodução executada e mutação independente são obrigatórios antes do GO.
- **L21:** testes de exemplo escritos por LLM estacionam em ~72%. Testes gerados a partir do contrato (tabela V/F por item) generalizam melhor.
- **L22 (proposta):** o oráculo antigo pode segurar o produto num nível fraco. Testes que exigem "passa sem evidência" precisam ser revistos a cada rodada.
- **L23 (proposta):** campanhas paralelas na mesma skill contaminam a medição. O portão roda em cópia limpa (HEAD + só os arquivos da frente).

## Como seguir
1. Abrir a campanha `campanha-ac-v05` com `ac.py init` (um `--scope` por glob).
2. Oráculo: um agente separado escreve um teste por defeito. Os que falham hoje provam o defeito.
3. Aprovações com a senha do founder, no terminal dele.
4. Uma frente só (`scripts/ac.py`, `scripts/hook_aprovacao.py`, `references/`, `docs/`).
