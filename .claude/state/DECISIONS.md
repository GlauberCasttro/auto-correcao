# DECISIONS — decisões do founder sobre a auto-correcao

Formato: D-nn · data · decisão · porquê · onde vale. Só entra aqui o que o founder decidiu (ou que está num commit
dele); proposta da IA vai para o BACKLOG.

- **D-01 · 2026-10-05 · aprovação humana por senha do founder.** v0.4 (`6e5dc67`): `gate`/`preauth` só num tty real
  e com a frase do founder; cada aprovação grava uma tag HMAC que só quem sabe a frase calcula; `frase conferir`
  recalcula todas. v0.4.1 (`797dc3d`): aceita senha forte além de frase (≥12 caracteres, ≥6 distintos, 3 tipos).
  Porquê: tty + desafio era forjável por um agente com `pty.fork`; só um segredo do founder separa os dois.
  Vale: toda campanha. A IA nunca aprova, nunca pede a senha no chat, nunca a digita por pty.
- **D-02 · 2026-10-04/05 · hook global `hook_aprovacao.py`** em `~/.claude/settings.json` (PreToolUse Bash): nega
  execução de `ac.py gate|preauth|frase`, `co.py approve` e `aprovar-*.sh` vinda do agente. Porquê: AC-04 (`--by` é
  texto livre). É filtro sintático, não sandbox; a garantia forte é a D-01. Vale: todas as sessões, todas as skills
  — por isso mexer no hook é frente separada e `tools/portar.sh` roda o `--selftest` antes e depois.
- **D-03 · 2026-10-06 · portão em cópia limpa** (HEAD + só os arquivos da frente, 2 Pythons, oráculos, nada removido).
  Porquê: L23 — campanhas paralelas na mesma skill contaminam a medição. Vale: toda entrega (`tools/portao.sh`).
- **D-04 · 2026-10-06 · conferir commit × portão:** só entra no commit o que o portão testou e aprovou
  (`tools/conferir-commit.sh`: cmp vivo × cópia testada, árvore igual, nada staged fora da frente).
- **D-05 · 2026-10-06 · harness de desenvolvimento por skill** em `<skill>/.claude/` (ESPEC-HARNESS-DEV): toda
  mudança no produto passa pelo fluxo; sem `publish` para a auto-correcao (não tem versão pública).
- **D-06 · 2026-10-06 · ac.py estável para as campanhas da própria skill:** as campanhas da auto-correcao são
  orquestradas por uma cópia de um commit (hoje `local/ac-estavel/` do projeto, recriável por
  `tools/ac-estavel.sh --refresh`), nunca pelo ac.py em edição.
  Porquê: o motor não julga a si mesmo. Troca do estável só sem campanha aberta (`tools/ac-estavel.sh --refresh`).
- **D-07 · push só pelo humano**, no terminal dele (o guard-git nega push sempre).
- **D-08 · 2026-10-06 · a skill vira PROJETO público** (ESPEC-PROJETOS de 2026-10-06): repo próprio
  `~/Repositorios/auto-correcao` (branch `main`, autor noreply do GitHub), raiz = a skill, instalada por link
  `~/.claude/skills/auto-correcao` → projeto. Campanhas em `campanhas/` (oráculos versionados; ledger e
  `aprovar-*.sh` fora), área da máquina em `local/` (ignorada: ac.py estável, cópias, portões, termos privados).
  Termo privado nunca entra em arquivo versionado nem em mensagem de commit (`tools/guard-privacidade.sh`).
  Push e criação do remoto: do orquestrador/founder, depois da revisão. Vale: todo commit deste projeto.
