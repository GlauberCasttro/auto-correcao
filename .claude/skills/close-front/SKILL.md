---
name: close-front
description: Fecha uma frente de desenvolvimento da skill auto-correcao — portão verde em cópia limpa, portar para a skill viva, conferir commit × portão, commit só dos arquivos da frente, fechar a campanha pelo ac.py estável (conferência feita pelo founder) e arquivar no WORKFLOW. Use quando a correção da frente estiver pronta, ou o usuário disser "fecha a frente", "close front", "entrega", "integra e commita".
---

# close-front — entregar

Arquivos da frente sempre EXPLÍCITOS, um por um (zsh não faz word-split de `$VAR`). ac.py ESTÁVEL por caminho
literal: `python3 local/ac-estavel/scripts/ac.py --work campanhas/<frente> ...`.

1. Portão: `bash .claude/tools/portao.sh <frente> --oraculo <campanha>/oraculo:<modulo> -- <arq1> <arq2>`.
   Leia `local/portao-<frente>/portao.out` até `FIM`. VERMELHO ⇒ volte à
   correção (achado que reabre correção = rodada nova no ac.py). Conte os testes a partir do portao.out, não de memória.
2. `bash .claude/tools/portar.sh <frente> --dry-run -- <arqs>`, depois sem `--dry-run`. Merge de 3 vias ⇒ portão de
   novo com `--src .` (o projeto). Conflito ⇒ resolva na cópia de trabalho.
3. `bash .claude/tools/conferir-commit.sh <frente> -- <arqs>` tem de dizer "conferido".
4. Commit (precisa do `preauth commit` do founder na campanha): mensagem em arquivo
   (`local/commit-<frente>.msg`), `git add <arqs pelo nome>`,
   `git commit -F <msg> -- <arqs>`. Push nunca.
5. Campanha (ac.py estável): `front report`, `done integracao`, remedição real (`run record --decision ...`; AC-09:
   se recusar no mesmo segundo do `done correcao`, registre de novo), `done remedicao`, decisão/relatório.
6. Conferência: o founder roda `frase conferir` (no fim do aprovar-<frente>.sh, ou gere um com
   `python3 .claude/tools/script-aprovacao.py <frente> --so-conferir`). Depois `done decisao`.
7. `python3 .claude/tools/frente.py close <frente> --commit <sha>`; atualize BACKLOG (item resolvido → Resolvidos,
   com commit) e rode a skill save-session.
8. Se a frente mudou ac.py/frase.py/references: proponha ao founder trocar o juiz
   (`bash .claude/tools/ac-estavel.sh --refresh --dry-run`), só sem campanha aberta.
