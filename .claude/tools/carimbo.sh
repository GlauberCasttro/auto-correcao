#!/usr/bin/env bash
# carimbo.sh — imprime a ÂNCORA do harness de desenvolvimento da auto-correcao (gerada, nunca escrita à mão):
#   branch, HEAD, árvore da skill no HEAD, versão (último commit feat da skill), ac.py estável (origem e
#   integridade), frente(s) ativa(s) com o status resumido da campanha (pelo ac.py ESTÁVEL), arquivos sujos
#   da skill (git status do diretório da skill) e a data do relógio do sistema.
#
# Uso: carimbo.sh               âncora completa
#      carimbo.sh --brief       versão curta (hook SessionStart; nunca falha)
#      carimbo.sh --write-resume  reescreve o bloco entre <!-- carimbo:inicio --> e <!-- carimbo:fim --> do
#                                 state/RESUME.md (o resto do arquivo fica intacto)
#      carimbo.sh --help
set -u
. "$(dirname "${BASH_SOURCE[0]}")/_comum.sh"
MODE=full
case "${1:-}" in
  -h|--help) awk 'NR>1 && !/^#/{exit} NR>1' "$0" | sed 's/^# \{0,1\}//'; exit 0;;
  --brief) MODE=brief;;
  --write-resume) MODE=resume;;
  "") ;;
  *) die "opção desconhecida: $1 (veja --help)";;
esac

ancora() {
  local brief="$1"
  local branch head tree versao dirty n_dirty est frentes
  branch="$(git -C "$SKILL" rev-parse --abbrev-ref HEAD 2>/dev/null || echo '?')"
  head="$(git -C "$SKILL" rev-parse --short HEAD 2>/dev/null || echo '?')"
  tree="$(skill_tree | cut -c1-12)"
  versao="$(git -C "$SKILL" log --format=%s -- . 2>/dev/null | grep -Eo "^(feat\($SKILLNAME\): |$SKILLNAME )v[0-9][0-9.]*" | head -1 | sed 's/.* v/v/')"
  [ -f "$SKILL/VERSION" ] && versao="$(head -1 "$SKILL/VERSION")"
  dirty="$(git -C "$SKILL" status --porcelain -- . 2>/dev/null)"
  n_dirty="$(printf '%s' "$dirty" | grep -c . || true)"
  if [ -f "$ACE" ]; then
    if bash "$TOOLS/ac-estavel.sh" --check >/dev/null 2>&1; then
      est="íntegro, origem $(grep '^commit=' "$WS/ac-estavel/ORIGEM.txt" 2>/dev/null | cut -d= -f2 | cut -c1-7)"
    else
      est="ALTERADO ou sem ORIGEM — rode tools/ac-estavel.sh --check"
    fi
  else
    est="AUSENTE — rode tools/ac-estavel.sh --refresh"
  fi
  echo "== âncora $SKILLNAME (tools/carimbo.sh, $(agora))"
  echo "branch: $branch · HEAD: $head · árvore da skill: ${tree:-?} · versão: ${versao:-?}"
  echo "ac.py estável: $est"
  frentes="$(python3 "$TOOLS/frente.py" list --ativas 2>/dev/null)"
  if [ -z "$frentes" ]; then
    echo "frente ativa: nenhuma"
  else
    printf '%s\n' "$frentes" | while IFS='|' read -r nome camp; do
      [ -n "$nome" ] || continue
      echo "frente ativa: $nome · campanha $camp"
      if [ -f "$ACE" ] && [ -d "$camp" ]; then
        if [ "$brief" = 1 ]; then
          python3 "$ACE" --work "$camp" status 2>&1 | sed -n '2p' | sed 's/^/  /'
        else
          python3 "$ACE" --work "$camp" status 2>&1 | sed 's/^/  /'
        fi
      fi
    done
  fi
  echo "sujos na skill: $n_dirty"
  if [ "$n_dirty" -gt 0 ]; then
    printf '%s\n' "$dirty" | head -10 | sed 's/^/  /'
    [ "$n_dirty" -gt 10 ] && echo "  ... (+$((n_dirty - 10)))"
  fi
  return 0
}

case "$MODE" in
  brief)
    ancora 1 2>/dev/null || true
    echo "(harness de desenvolvimento da $SKILLNAME: leia .claude/CLAUDE.md; retomar = skill load-session)"
    exit 0;;
  full) ancora 0;;
  resume)
    R="$STATE/RESUME.md"
    [ -f "$R" ] || die "não existe $R"
    BLOCO="$(ancora 0)"
    BLOCO="$BLOCO" python3 - "$R" <<'PY'
import os, re, sys
p = sys.argv[1]
s = open(p, encoding="utf-8").read()
ini, fim = "<!-- carimbo:inicio -->", "<!-- carimbo:fim -->"
if ini not in s or fim not in s:
    sys.exit("ERRO: RESUME.md sem os marcadores %s ... %s" % (ini, fim))
novo = ini + "\n```\n" + os.environ["BLOCO"].rstrip("\n") + "\n```\n" + fim
s = s[:s.index(ini)] + novo + s[s.index(fim) + len(fim):]
open(p, "w", encoding="utf-8").write(s)
print("carimbo gravado em %s" % p)
PY
    ;;
esac
