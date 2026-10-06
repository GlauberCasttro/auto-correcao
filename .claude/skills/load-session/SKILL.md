---
name: load-session
description: Retoma o desenvolvimento da skill auto-correcao — imprime a âncora (tools/carimbo.sh), lê RESUME e WORKFLOW do .claude/state e o status da campanha ativa pelo ac.py estável. Use ao abrir a sessão, ou quando o usuário disser "onde paramos", "retoma", "carrega a sessão", "load session".
---

# load-session — retomar

Read-only (a única escrita é o carimbo no RESUME). Não leia `scripts/`, `docs/` ou logs no caminho feliz.

1. `bash .claude/tools/carimbo.sh` — âncora real (branch, HEAD, árvore, versão, ac.py estável, frente ativa com o
   `status` da campanha pelo ac.py ESTÁVEL, arquivos sujos). Se o ac.py estável aparecer ALTERADO, pare e
   diga ao founder (não abra nem avance campanha). AUSENTE (clone novo, máquina nova): proponha
   `bash .claude/tools/ac-estavel.sh --refresh` (extrai do HEAD; só sem campanha aberta).
2. Leia `.claude/state/RESUME.md` e `.claude/state/WORKFLOW.md`. Se o carimbo do RESUME divergir da âncora
   (HEAD/árvore/frente), diga o que mudou e rode `bash .claude/tools/carimbo.sh --write-resume`.
3. `python3 .claude/tools/frente.py check` e `python3 .claude/tools/sessao.py tail -n 3`.
4. Com frente ativa: diga em que etapa a campanha está e o próximo passo do fluxo (CLAUDE.md, "Fluxo de entrega").
   Se o próximo passo for aprovação, o founder roda o `aprovar-<frente>.sh` dele — você não roda.
5. Enuncie em 5 linhas: âncora, frente ativa/etapa, P0 do BACKLOG em aberto, próximo passo. Pare e espere.
