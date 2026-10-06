---
name: save-session
description: Salva o estado do desenvolvimento da skill auto-correcao — atualiza RESUME e WORKFLOW, acrescenta o log append-only da sessão, registra decisões do founder e commita SÓ o .claude/state. Use ao encerrar ou pausar, ou quando o usuário disser "salva a sessão", "save session", "registra onde paramos".
---

# save-session — salvar

Só escreve em `.claude/state/`. Data, HEAD e commits vêm dos scripts, nunca de você.

1. `bash .claude/tools/carimbo.sh --write-resume` (carimbo gerado).
2. Edite `.claude/state/RESUME.md` → "Onde paramos" e "Próximos passos": fatos verificáveis (commit, contagem de
   testes com o comando que a produziu, caminho do portao.out). Nada de "deve funcionar".
3. Frentes: `python3 .claude/tools/frente.py render` (o bloco é gerado; a Fila você edita à mão se mudou).
4. Decisão nova do FOUNDER (dita por ele nesta sessão) → `.claude/state/DECISIONS.md` (D-nn, data, decisão,
   porquê, onde vale). Proposta sua vai para `BACKLOG.md`, não para DECISIONS. Achado novo → BACKLOG com origem.
5. `python3 .claude/tools/sessao.py log --resumo "..." [--frente X] [--proximo "..."] [--commit SHA]`.
6. Commit só do estado: escreva a mensagem num arquivo em local/
   (`local/msg-state.txt`) e rode
   `bash .claude/tools/commit-state.sh --msg-file <arquivo> --dry-run`, confira, e sem `--dry-run`.
   Push nunca (é do humano).
