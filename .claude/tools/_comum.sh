# shellcheck shell=bash
# _comum.sh — caminhos e helpers dos tools do harness de desenvolvimento da auto-correcao.
# Sourced pelos tools .sh (compatível com bash 3.2 do macOS). Não executa nada sozinho.
#
#   SKILL  = a raiz do PROJETO (= a skill: SKILL.md na raiz; dois níveis acima deste arquivo), ou $AC_DEV_SKILL (testes)
#   WS     = área LOCAL desta máquina, no .gitignore: <projeto>/local, ou $AC_DEV_WS (testes). Guarda o ac.py estável
#            (local/ac-estavel/), as cópias de trabalho (local/work/<frente>/) e os portões (local/portao-<frente>/)
#   CAMP   = campanhas desta skill: <projeto>/campanhas (oráculos versionados; ledgers .auto-correcao/ e
#            aprovar-*.sh no .gitignore), ou $AC_DEV_CAMP (testes)
#   ACE    = o ac.py ESTÁVEL (cópia de um commit, em $WS/ac-estavel/) que orquestra as campanhas DESTA skill.
#            Nunca o ac.py em edição: ele não julga a si mesmo. Recriável: tools/ac-estavel.sh --refresh.
TOOLS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
if [ -n "${AC_DEV_SKILL:-}" ]; then
  SKILL="$(cd "$AC_DEV_SKILL" && pwd -P)"
else
  SKILL="$(cd "$TOOLS/../.." && pwd -P)"
fi
SKILLNAME="$(basename "$SKILL")"
WS="${AC_DEV_WS:-$SKILL/local}"
CAMP="${AC_DEV_CAMP:-$SKILL/campanhas}"
STATE="$SKILL/.claude/state"
ACE="$WS/ac-estavel/scripts/ac.py"
PY1="python3"
PY2="${AC_DEV_PY2:-/usr/bin/python3}"

die() { echo "ERRO: $*" >&2; exit 2; }
repo_root() { git -C "$SKILL" rev-parse --show-toplevel 2>/dev/null; }
# prefixo da skill no repo (ex.: "auto-correcao/"); vazio se a skill é a raiz do repo
repo_prefix() { git -C "$SKILL" rev-parse --show-prefix 2>/dev/null; }
skill_tree() { git -C "$SKILL" rev-parse "${1:-HEAD}:$(repo_prefix)" 2>/dev/null; }
valid_frente() {
  case "$1" in
    ""|.*|-*|*/*|*" "*) die "nome de frente inválido: '$1' (use a-z 0-9 . _ -)";;
  esac
  printf '%s' "$1" | grep -Eq '^[a-z0-9][a-z0-9._-]{0,63}$' || die "nome de frente inválido: '$1' (use a-z 0-9 . _ -)"
}
# arquivo relativo à raiz da skill, sem '..' nem caminho absoluto
valid_relpath() {
  case "$1" in
    ""|/*|../*|*/../*|*/..|..) die "arquivo deve ser relativo à raiz da skill, sem '..': '$1'";;
  esac
}
sha256() { shasum -a 256 "$1" | awk '{print $1}'; }
agora() { date -u '+%Y-%m-%dT%H:%M:%SZ'; }
