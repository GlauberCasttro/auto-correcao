#!/usr/bin/env bash
# copia.sh — cria a CÓPIA DE TRABALHO de uma frente: `git archive HEAD` do projeto → local/work/<frente>/<skill>/
# (local/ está no .gitignore; a cópia não tem .git próprio: não rode git dentro dela).
# O corretor só edita aqui. Só entra o que está COMMITADO (o worktree sujo da skill viva não vaza para a cópia).
# Idempotente: se a cópia já existe, só imprime o caminho (nunca sobrescreve trabalho de corretor).
#
# Uso: copia.sh <frente> [--ref REF] [--dry-run]
#      imprime na última linha o caminho da cópia (raiz da skill copiada)
set -u
. "$(dirname "${BASH_SOURCE[0]}")/_comum.sh"
FRENTE=""; REF=HEAD; DRY=0
while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) awk 'NR>1 && !/^#/{exit} NR>1' "$0" | sed 's/^# \{0,1\}//'; exit 0;;
    --ref) REF="${2:-}"; shift;;
    --dry-run) DRY=1;;
    -*) die "opção desconhecida: $1";;
    *) [ -z "$FRENTE" ] || die "uma frente só"; FRENTE="$1";;
  esac
  shift
done
[ -n "$FRENTE" ] || die "uso: copia.sh <frente> [--ref REF]"
valid_frente "$FRENTE"
DEST="$WS/work/$FRENTE"
if [ -d "$DEST/$SKILLNAME" ]; then
  echo "(cópia já existe; nada feito)"
  echo "$DEST/$SKILLNAME"
  exit 0
fi
ROOT="$(repo_root)" || die "a skill não está num repo git"
PFX="$(repo_prefix)"
SHA="$(git -C "$ROOT" rev-parse --verify "$REF^{commit}" 2>/dev/null)" || die "ref inválida: $REF"
if [ "$DRY" = 1 ]; then
  echo "[dry-run] git archive ${SHA:0:12} -- ${PFX:-.} → $DEST/$SKILLNAME"
  exit 0
fi
mkdir -p "$DEST"
TMP="$DEST/.tmp.$$"; mkdir -p "$TMP"
git -C "$ROOT" archive "$SHA" -- "${PFX:-.}" | tar -x -C "$TMP" || die "git archive falhou"
if [ -n "$PFX" ]; then mv "$TMP/${PFX%/}" "$DEST/$SKILLNAME"; else mv "$TMP" "$DEST/$SKILLNAME"; fi
rm -rf "$TMP"
printf 'commit=%s\narvore=%s\ncriada_em=%s\n' "$SHA" "$(skill_tree "$SHA")" "$(agora)" > "$DEST/BASE.txt"
echo "cópia de trabalho criada de ${SHA:0:12}"
echo "$DEST/$SKILLNAME"
