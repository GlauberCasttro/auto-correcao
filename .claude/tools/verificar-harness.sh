#!/usr/bin/env bash
# verificar-harness.sh — verificação do próprio harness (a da ESPEC-HARNESS-DEV):
#   bash -n dos .sh, parse dos .py nos 2 Pythons, --help de cada tool (exit 0), testes .claude/tools/tests nos
#   2 Pythons, carimbo.sh roda, frente.py check, sessao.py check, ac-estavel.sh --check, guard-privacidade --all,
#   nomes proibidos ausentes.
#   Com --suites: também as suítes da skill viva (scripts/tests) nos 2 Pythons (~3 min) e o hook --selftest.
#
# Uso: verificar-harness.sh [--suites]
set -u
. "$(dirname "${BASH_SOURCE[0]}")/_comum.sh"
SUITES=0
case "${1:-}" in
  -h|--help) awk 'NR>1 && !/^#/{exit} NR>1' "$0" | sed 's/^# \{0,1\}//'; exit 0;;
  --suites) SUITES=1;;
  "") ;;
  *) die "opção desconhecida: $1";;
esac
FAIL=0
ok() { echo "ok   $*"; }
ko() { echo "FAIL $*"; FAIL=$((FAIL + 1)); }
for f in "$TOOLS"/*.sh; do bash -n "$f" && ok "bash -n $(basename "$f")" || ko "bash -n $(basename "$f")"; done
for f in "$TOOLS"/*.py "$TOOLS"/tests/*.py; do
  for py in "$PY1" "$PY2"; do
    "$py" -c 'import ast,sys; ast.parse(open(sys.argv[1],encoding="utf-8").read())' "$f" 2>/dev/null \
      && ok "parse $(basename "$f") ($py)" || ko "parse $(basename "$f") ($py)"
  done
done
for f in "$TOOLS"/*.sh "$TOOLS"/*.py; do
  b="$(basename "$f")"; [ "$b" = _comum.sh ] && continue
  case "$f" in *.py) cmd=(python3 "$f" --help);; *) cmd=(bash "$f" --help);; esac
  "${cmd[@]}" >/dev/null 2>&1 < /dev/null && ok "--help $b" || ko "--help $b"
done
for py in "$PY1" "$PY2"; do
  out="$(cd "$TOOLS" && PYTHONDONTWRITEBYTECODE=1 "$py" -m unittest discover -s tests 2>&1)"
  if [ $? = 0 ]; then ok "testes do harness ($py): $(printf '%s\n' "$out" | grep -E '^Ran ')"
  else ko "testes do harness ($py)"; printf '%s\n' "$out" | tail -30; fi
done
bash "$TOOLS/carimbo.sh" >/dev/null 2>&1 && ok "carimbo.sh" || ko "carimbo.sh"
python3 "$TOOLS/frente.py" check >/dev/null 2>&1 && ok "frente.py check" || ko "frente.py check"
python3 "$TOOLS/sessao.py" check >/dev/null 2>&1 && ok "sessao.py check" || ko "sessao.py check"
bash "$TOOLS/ac-estavel.sh" --check >/dev/null 2>&1 && ok "ac-estavel íntegro" || ko "ac-estavel.sh --check (clone novo: --refresh)"
bash "$TOOLS/guard-privacidade.sh" --all >/dev/null 2>&1 && ok "guard-privacidade --all limpo" || ko "guard-privacidade --all"
# nomes antigos de skill proibidos (um teste da codebase-specialists varre as skills)
S="-sessao"; E="-epico"   # montado por partes para este arquivo não casar consigo mesmo
PAT="salvar$S|carregar$S|planejar-spr""int|new$E|close$E|/corr""igir"
proib="$(grep -rlE "$PAT" "$SKILL/.claude" 2>/dev/null || true)"
[ -z "$proib" ] && ok "sem nomes antigos de skill" || ko "nomes antigos de skill em: $proib"
if [ "$SUITES" = 1 ]; then
  for py in "$PY1" "$PY2"; do
    out="$(cd "$SKILL/scripts" && PYTHONDONTWRITEBYTECODE=1 "$py" -m unittest discover -s tests 2>&1)"
    if [ $? = 0 ]; then ok "suítes da skill ($py): $(printf '%s\n' "$out" | grep -E '^Ran ')"
    else ko "suítes da skill ($py)"; printf '%s\n' "$out" | tail -30; fi
    PYTHONDONTWRITEBYTECODE=1 "$py" "$SKILL/scripts/hook_aprovacao.py" --selftest >/dev/null 2>&1 \
      && ok "hook --selftest ($py)" || ko "hook --selftest ($py)"
  done
fi
echo "verificar-harness: $FAIL falha(s)"
[ "$FAIL" = 0 ]
