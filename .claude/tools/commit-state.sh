#!/usr/bin/env bash
# commit-state.sh — commit SÓ do estado do harness (.claude/state/), com a mensagem num ARQUIVO (-F): o hook global
# nega texto com "approve"/"gate"/"frase" junto de ac.py na linha de comando, e mensagem em arquivo não é comando.
# Recusa se já houver qualquer coisa staged fora de .claude/state/ (não arrasta trabalho de outra frente/skill)
# e se o estado ou a mensagem tiverem termo privado (tools/guard-privacidade.sh: o projeto é público).
# Nunca faz push (push é do humano).
#
# Uso: commit-state.sh --msg-file ARQ [--dry-run]
set -u
. "$(dirname "${BASH_SOURCE[0]}")/_comum.sh"
MSG=""; DRY=0
while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) awk 'NR>1 && !/^#/{exit} NR>1' "$0" | sed 's/^# \{0,1\}//'; exit 0;;
    --msg-file) MSG="${2:-}"; shift;;
    --dry-run) DRY=1;;
    *) die "opção desconhecida: $1";;
  esac
  shift
done
[ -n "$MSG" ] && [ -s "$MSG" ] || die "--msg-file ARQ (arquivo com a mensagem, não vazio)"
ROOT="$(repo_root)" || die "a skill não está num repo git"
PFX="$(repo_prefix)"
ALVO="${PFX}.claude/state"
fora="$(git -C "$ROOT" diff --cached --name-only | grep -v "^$ALVO/" || true)"
[ -z "$fora" ] || die "há arquivos staged fora de $ALVO: $(echo "$fora" | tr '\n' ' ')"
mud="$(git -C "$ROOT" status --porcelain -- "$ALVO")"
[ -n "$mud" ] || { echo "nada a commitar em $ALVO"; exit 0; }
ARQS=()
while IFS= read -r f; do ARQS+=("$f"); done < <(find "$STATE" -type f ! -name '.DS_Store' | LC_ALL=C sort)
bash "$TOOLS/guard-privacidade.sh" --paths "$MSG" "${ARQS[@]}" || die "termo privado no estado ou na mensagem (acima)"
if [ "$DRY" = 1 ]; then
  echo "[dry-run] git add -- $ALVO && git commit -F $MSG -- $ALVO"
  printf '%s\n' "$mud" | sed 's/^/  /'
  exit 0
fi
git -C "$ROOT" add -- "$ALVO" && git -C "$ROOT" commit -q -F "$MSG" -- "$ALVO" || die "commit falhou"
echo "commit do estado: $(git -C "$ROOT" rev-parse --short HEAD)"
