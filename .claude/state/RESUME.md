# RESUME — desenvolvimento da auto-correcao

<!-- carimbo:inicio -->
<!-- carimbo:fim -->

## Onde paramos (2026-10-06)
- A skill virou PROJETO próprio (D-08): `~/Repositorios/auto-correcao`, branch `main`, primeiro commit
  "auto-correcao v0.4.1 — projeto completo de desenvolvimento". Conteúdo da skill = o HEAD do repo de origem
  (último commit que tocava a skill lá: `7ac0666`, docs: PENDENTE.md), com três ajustes para o projeto público:
  termos privados trocados (docs/06, docs/PENDENTE, fixture "ana" em test_v04_frase), e `test_v03_oraculo.py`/
  `test_v04_frase.py` passam a testar a skill ONDE ESTÃO (pasta acima de `scripts/tests`, ou `$ORACULO_SKILL`) em
  vez do caminho fixo `~/.claude/skills/auto-correcao` — antes o portão em cópia limpa testava a skill instalada
  nessas duas suítes.
- Versão: **v0.4.1** (aprovação humana por senha/frase do founder, PBKDF2 + tag HMAC; hook global
  `hook_aprovacao.py`). Suítes da skill no projeto: **101 testes verdes** em `python3` e `/usr/bin/python3`
  (`cd scripts && PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests`, 2026-10-06).
- Harness de desenvolvimento adaptado ao projeto: `local/` (ignorado) guarda o ac.py estável, as cópias de
  trabalho e os portões; `campanhas/` guarda os oráculos (ledgers fora). Novo `tools/guard-privacidade.sh`
  (pre-commit/commit-msg via `--install-hooks`, chamado por `conferir-commit.sh`, `commit-state.sh` e
  `verificar-harness.sh`). `portar.sh` vigia campanhas do projeto, `~/.claude/skills/*-workspace` e
  `<pasta-mãe>/*/campanhas` (ou `$AC_DEV_VIGIAR`); nenhuma = "nada a vigiar". `script-aprovacao.py --by` padrão
  `$AC_FOUNDER` ou "founder".
- ac.py ESTÁVEL: extraído do HEAD do projeto em `local/ac-estavel/` (`tools/ac-estavel.sh --refresh`).
- Campanhas anteriores da skill trazidas só com o oráculo: `campanhas/ac-v03`, `campanhas/ac-v04`
  (tabela em `campanhas/README.md`).
- A skill instalada (`~/.claude/skills/auto-correcao`) AINDA é a pasta do repo de origem: o link para o projeto é
  feito pelo orquestrador depois da revisão do founder. Sem remoto, sem push.

## Próximos passos
1. Founder revisa o projeto; orquestrador cria o link `~/.claude/skills/auto-correcao` → projeto, o remoto e o push.
   Depois do link: `python3 ~/.claude/skills/auto-correcao/scripts/hook_aprovacao.py --selftest` nos 2 Pythons.
2. Abrir a frente `ac-v05` (skill new-front) com os P0 do BACKLOG: AC-10, AC-14 (oracle change substitui a lista),
   AC-08, AC-12. Escopo provável: `scripts/ac.py`, `scripts/tests/**`, `docs/**`, `references/**`.
   `scripts/hook_aprovacao.py` (AC-13/AC-15, falsos positivos do hook) numa frente SEPARADA: portar o hook muda
   o hook global de todas as sessões na hora.
3. Oráculo por agente separado, um teste por defeito (os que falham hoje provam o defeito).
