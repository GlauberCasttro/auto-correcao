#!/usr/bin/env bash
# ac-estavel.sh — o ac.py ESTÁVEL que orquestra as campanhas DESTA skill.
#
# Por quê: a auto-correcao é o motor das campanhas. Usar o ac.py em edição para julgar a própria evolução é o
# réu julgando a si mesmo (e um defeito novo no ac.py viraria defeito na medição). As campanhas da
# auto-correcao usam uma cópia extraída de um COMMIT do próprio projeto (nunca do worktree) em
# <projeto>/local/ac-estavel/ (no .gitignore; scripts/ + references/, somente leitura, com ORIGEM.txt: commit, árvore,
# data e sha256 de cada arquivo). Numa máquina nova (ou clone novo) ele não existe: rode --refresh uma vez.
# O hook global continua apontando para o hook_aprovacao.py VIVO; este script não toca ~/.claude/settings.json.
#
# Uso: ac-estavel.sh [--check]                confere a integridade (sha256 × ORIGEM.txt); exit 0 íntegro, 1 não
#      ac-estavel.sh --refresh [--ref REF]    (re)extrai de `git archive REF` (padrão HEAD). Recusa se houver
#                                             campanha aberta em <projeto>/campanhas/ (trocar o juiz no meio
#                                             de uma campanha muda as regras do jogo)
#      ac-estavel.sh --path                   imprime o caminho do ac.py estável
#      ac-estavel.sh --dry-run --refresh      mostra o que faria
set -u
. "$(dirname "${BASH_SOURCE[0]}")/_comum.sh"
ACTION=check; REF=HEAD; DRY=0
while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) awk 'NR>1 && !/^#/{exit} NR>1' "$0" | sed 's/^# \{0,1\}//'; exit 0;;
    --check) ACTION=check;;
    --refresh) ACTION=refresh;;
    --path) echo "$ACE"; exit 0;;
    --ref) REF="${2:-}"; shift;;
    --dry-run) DRY=1;;
    *) die "opção desconhecida: $1 (veja --help)";;
  esac
  shift
done
EST="$WS/ac-estavel"

if [ "$ACTION" = check ]; then
  [ -f "$EST/ORIGEM.txt" ] || { echo "ac.py estável AUSENTE em $EST (rode --refresh)"; exit 1; }
  bad=0
  while IFS='=' read -r k v; do
    case "$k" in
      sha256:*) f="${k#sha256:}"
        if [ ! -f "$EST/$f" ]; then echo "FALTA $f"; bad=1
        elif [ "$(sha256 "$EST/$f")" != "$v" ]; then echo "ALTERADO $f"; bad=1; fi;;
    esac
  done < "$EST/ORIGEM.txt"
  [ -f "$ACE" ] || { echo "FALTA scripts/ac.py"; bad=1; }
  if [ "$bad" = 0 ]; then
    echo "ac.py estável íntegro: $ACE ($(grep '^commit=' "$EST/ORIGEM.txt" | cut -d= -f2 | cut -c1-12))"
    exit 0
  fi
  echo "ac.py estável NÃO confere com ORIGEM.txt — não use para julgar; investigue antes de --refresh"
  exit 1
fi

# --refresh
ROOT="$(repo_root)" || die "a skill não está num repo git"
PFX="$(repo_prefix)"
SHA="$(git -C "$ROOT" rev-parse --verify "$REF^{commit}" 2>/dev/null)" || die "ref inválida: $REF"
git -C "$ROOT" cat-file -e "$SHA:${PFX}scripts/ac.py" 2>/dev/null || die "$REF não tem ${PFX}scripts/ac.py"
abertas=""
for st in "$CAMP"/*/.auto-correcao/state.json; do
  [ -f "$st" ] || continue
  stage="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("stage",""))' "$st" 2>/dev/null)"
  [ "$stage" = concluida ] || abertas="$abertas $(basename "$(dirname "$(dirname "$st")")")($stage)"
done
[ -z "$abertas" ] || die "há campanha aberta usando o ac.py estável:$abertas — feche-a antes de trocar o juiz"
if [ "$DRY" = 1 ]; then
  echo "[dry-run] extrairia ${PFX}scripts e ${PFX}references de $SHA para $EST (substituindo o atual)"
  exit 0
fi
mkdir -p "$WS"
TMP="$WS/.ac-estavel.tmp.$$"
rm -rf "$TMP"; mkdir -p "$TMP"
git -C "$ROOT" archive "$SHA" -- "${PFX}scripts" "${PFX}references" | tar -x -C "$TMP" || die "git archive falhou"
SRC="$TMP/${PFX%/}"; [ -n "$PFX" ] || SRC="$TMP"
rm -rf "$SRC/scripts/tests"
NEW="$WS/.ac-estavel.new.$$"
rm -rf "$NEW"; mkdir -p "$NEW"
mv "$SRC/scripts" "$SRC/references" "$NEW/"
rm -rf "$TMP"
{
  echo "# ac.py ESTÁVEL — extraído por tools/ac-estavel.sh; não edite (o guard-entrega nega)"
  echo "commit=$SHA"
  echo "arvore=$(git -C "$ROOT" rev-parse "$SHA:${PFX%/}" 2>/dev/null)"
  echo "extraido_em=$(agora)"
  (cd "$NEW" && find scripts references -type f | LC_ALL=C sort) | while read -r f; do
    echo "sha256:$f=$(sha256 "$NEW/$f")"
  done
} > "$NEW/ORIGEM.txt"
if [ -d "$EST" ]; then
  chmod -R u+w "$EST" 2>/dev/null
  mv "$EST" "$WS/.ac-estavel.old.$(date +%Y%m%d%H%M%S)"
fi
mv "$NEW" "$EST"
find "$EST/scripts" "$EST/references" -type f -exec chmod a-w {} +
echo "ac.py estável extraído de ${SHA:0:12}: $ACE"
bash "$0" --check
