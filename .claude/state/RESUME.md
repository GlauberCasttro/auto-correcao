# RESUME — desenvolvimento da auto-correcao

<!-- carimbo:inicio -->
<!-- carimbo:fim -->

## Onde paramos (2026-10-08, tarde) — frente win-hook entregue
- `30e2da6`: hook de aprovação vê a ferramenta PowerShell e o Windows (AC-18). Campanha `campanhas/win-hook` concluída
  (PARAR): oráculo 17/17 + 12 guardas em Windows (Git Bash, PowerShell) e WSL; selftest 135/135; prova real numa
  sessão `claude -p` com o hook em `.claude/settings.local.json` (local, matcher Bash|PowerShell): gate via
  PowerShell NEGADO. Juiz (`local/ac-estavel`) trocado para `d4e63e0` (motor com win-motor).
- Pendências do founder: push da branch `release/version-windows`.
- Próximo: AC-24 (2 brechas antigas do Bash no hook), AC-25 (save com retentativa no Windows), AC-20 (harness
  nativo), AC-23 (frentes.json com caminho absoluto — corrigido à mão a cada fechamento).

## Onde paramos (2026-10-08) — frente win-motor entregue (Windows)
- Branch **`release/version-windows`** (pedido do founder). Commit da frente: `3e81f49` (10 arquivos: frase.py,
  ac.py, scripts/tests/*, .gitattributes, SKILL.md, README.md, docs/04). Campanha `campanhas/win-motor` concluída
  (decisão PARAR): oráculo 0/24 → 24/24 em Windows (Git Bash e PowerShell, Python 3.12, sem PYTHONUTF8) e WSL
  (3.10); scripts/tests 101 OK no Windows (57 pulados por pty) e no WSL sem falha nova; selftest 83/83.
  Critério 4 (founder aprova gate no PowerShell) provado em `local/runs/win-motor/prova-powershell`.
- Máquina Windows: o processo do harness rodou pela **WSL** (Ubuntu, python3 3.10; o harness chama python3/bash por
  subprocess — AC-20). Repo com `core.autocrlf=input` e `core.eol=lf` locais; worktree convertido para LF.
  Autor local `GlauberCasttro` (noreply). Travas de privacidade instaladas; `local/termos-privados.txt` AUSENTE.
  Frase do founder definida nos DOIS ambientes (WSL `~/.claude/...`, Windows `%USERPROFILE%\.claude\...`).
- Pendências do founder: push da branch; `git update-index --really-refresh` (69 arquivos com cache de stat velho
  após a conversão para LF — conteúdo idêntico); decidir trocar o juiz (`ac-estavel.sh --refresh`).
- Próximo: AC-18 (hook vê PowerShell/python.exe) em frente separada; AC-20 (harness nativo no Windows).

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
