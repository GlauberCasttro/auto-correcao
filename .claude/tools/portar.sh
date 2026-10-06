#!/usr/bin/env bash
# portar.sh — leva os arquivos de uma frente da cópia de trabalho para a skill VIVA (o projeto) (o único caminho sancionado de
# escrita no produto). Tudo ou nada:
#   * arquivo vivo igual ao HEAD → copia a versão de trabalho;
#   * arquivo vivo mudou desde o HEAD (outra sessão) → merge de 3 vias (git merge-file, base = HEAD); conflito ⇒
#     para sem escrever nada e deixa os arquivos com marcadores em local/portao-<frente>/conflitos/.
#     Depois de um merge, o vivo ≠ o que o portão testou: rode o portão de novo com --src <skill viva>.
# Salvaguardas do motor (esta skill É o motor das campanhas de todas as skills):
#   * scripts/hook_aprovacao.py na frente → --selftest da versão nova nos 2 Pythons ANTES de portar e do vivo
#     DEPOIS; falhou ⇒ restaura o backup (o hook é GLOBAL: quebrado, nega ou deixa passar o Bash de toda sessão).
#   * scripts/ac.py, scripts/frase.py ou references/ na frente → `status` (ac.py VIVO) de toda campanha encontrada
#     antes e depois; campanha que lia e passou a falhar ⇒ restaura o backup. Onde procura: $AC_DEV_VIGIAR (diretórios
#     separados por ':'), ou o padrão campanhas/ deste projeto + ~/.claude/skills/*-workspace + <pasta-mãe>/*/campanhas
#     (projetos irmãos). Nenhuma campanha na máquina (ex.: máquina nova) = "nada a vigiar", não é falha.
# Backup do que foi sobrescrito em local/portao-<frente>/backup-portar-<data>/.
#
# Uso: portar.sh <frente> [--src DIR] [--dry-run] -- <arquivo> [<arquivo>...]   (relativos à raiz da skill)
set -u
. "$(dirname "${BASH_SOURCE[0]}")/_comum.sh"
FRENTE=""; SRC=""; DRY=0; FILES=()
while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) awk 'NR>1 && !/^#/{exit} NR>1' "$0" | sed 's/^# \{0,1\}//'; exit 0;;
    --src) SRC="${2:-}"; shift;;
    --dry-run) DRY=1;;
    --) shift; FILES=("$@"); break;;
    -*) die "opção desconhecida: $1";;
    *) [ -z "$FRENTE" ] || die "uma frente só"; FRENTE="$1";;
  esac
  shift
done
[ -n "$FRENTE" ] && [ "${#FILES[@]}" -gt 0 ] || die "uso: portar.sh <frente> [--src DIR] -- <arquivos>"
valid_frente "$FRENTE"
SRC="${SRC:-$WS/work/$FRENTE/$SKILLNAME}"
[ -d "$SRC" ] || die "fonte não existe: $SRC"
SRC="$(cd "$SRC" && pwd -P)"
[ "$SRC" != "$SKILL" ] || die "--src é a própria skill viva: nada a portar"
for f in "${FILES[@]}"; do
  valid_relpath "$f"
  case "$f" in .claude/state/*) die "$f é estado, não produto: não se porta";; esac
  [ -f "$SRC/$f" ] || die "não existe na fonte: $SRC/$f"
done
ROOT="$(repo_root)" || die "a skill não está num repo git"
PFX="$(repo_prefix)"
P="$WS/portao-$FRENTE"
STG="$P/.portar-staging"
chmod -R u+w "$STG" 2>/dev/null; rm -rf "$STG" "$P/conflitos"; mkdir -p "$STG"

conflitos=0; HOOK=0; MOTOR=0
for f in "${FILES[@]}"; do
  case "$f" in
    scripts/hook_aprovacao.py) HOOK=1;;
    scripts/ac.py|scripts/frase.py|references/*) MOTOR=1;;
  esac
  mkdir -p "$(dirname "$STG/$f")"
  base="$STG/.base"; : > "$base"
  git -C "$ROOT" show "HEAD:${PFX}$f" > "$base" 2>/dev/null || : > "$base"
  vivo="$SKILL/$f"
  if [ ! -f "$vivo" ] || cmp -s "$vivo" "$base"; then
    cp -p "$SRC/$f" "$STG/$f"; echo "copiar  $f"
  elif cmp -s "$vivo" "$SRC/$f"; then
    cp -p "$SRC/$f" "$STG/$f"; echo "igual   $f (vivo já tem a versão de trabalho)"
  else
    cp -p "$SRC/$f" "$STG/$f"
    if git merge-file -q -L trabalho -L HEAD -L vivo "$STG/$f" "$base" "$vivo"; then
      echo "merge   $f (vivo mudou desde o HEAD; 3 vias sem conflito — rode o portão de novo com --src $SKILL)"
    else
      mkdir -p "$(dirname "$P/conflitos/$f")"; cp "$STG/$f" "$P/conflitos/$f"
      echo "CONFLITO $f → $P/conflitos/$f"; conflitos=$((conflitos + 1))
    fi
  fi
done
rm -f "$STG/.base"
[ "$conflitos" = 0 ] || { echo "nada portado: $conflitos conflito(s). Resolva na cópia de trabalho e repita."; exit 1; }
if [ "$DRY" = 1 ]; then echo "[dry-run] nada escrito na skill viva"; exit 0; fi

if [ "$HOOK" = 1 ]; then
  for py in "$PY1" "$PY2"; do
    PYTHONDONTWRITEBYTECODE=1 "$py" "$STG/scripts/hook_aprovacao.py" --selftest >/dev/null 2>&1 \
      || die "hook_aprovacao.py novo FALHA o --selftest em $py: nada portado (o hook global não é tocado)"
  done
fi
raizes_vigiadas() {  # uma por linha; ausentes são ignoradas
  local d
  if [ -n "${AC_DEV_VIGIAR:-}" ]; then
    printf '%s\n' "$AC_DEV_VIGIAR" | tr ':' '\n'
    return 0
  fi
  echo "$CAMP"
  for d in "$HOME"/.claude/skills/*-workspace "$(dirname "$SKILL")"/*/campanhas; do echo "$d"; done
}
campanhas() {
  local d
  raizes_vigiadas | while read -r d; do
    [ -n "$d" ] && [ -d "$d" ] || continue
    find "$(cd "$d" && pwd -P)" -maxdepth 4 -path '*/.auto-correcao/state.json' \
      -not -path '*/work/*' -not -path '*/portao-*' -not -path '*/ac-estavel*' -not -path '*/_descartadas/*' 2>/dev/null
  done | LC_ALL=C sort -u
}
status_todas() {  # imprime "<exit> <campanha>" por campanha, com o ac.py VIVO
  local st w
  campanhas | while read -r st; do
    w="$(dirname "$(dirname "$st")")"
    PYTHONDONTWRITEBYTECODE=1 "$PY1" "$SKILL/scripts/ac.py" --work "$w" status >/dev/null 2>&1
    echo "$? $w"
  done
}
[ "$MOTOR" = 1 ] && status_todas > "$STG/.antes"

BK="$P/backup-portar-$(date +%Y%m%d%H%M%S)"
mkdir -p "$BK"
: > "$BK/NOVOS.txt"
for f in "${FILES[@]}"; do
  if [ -f "$SKILL/$f" ]; then mkdir -p "$(dirname "$BK/$f")"; cp -p "$SKILL/$f" "$BK/$f"; else echo "$f" >> "$BK/NOVOS.txt"; fi
done
restaurar() {
  local f
  for f in "${FILES[@]}"; do
    if [ -f "$BK/$f" ]; then cp -p "$BK/$f" "$SKILL/$f"; else rm -f "$SKILL/$f"; fi
  done
  echo "RESTAURADO o backup $BK: $*" >&2
  exit 1
}
for f in "${FILES[@]}"; do
  mkdir -p "$(dirname "$SKILL/$f")"
  cp -p "$STG/$f" "$SKILL/$f"
done
if [ "$HOOK" = 1 ]; then
  for py in "$PY1" "$PY2"; do
    PYTHONDONTWRITEBYTECODE=1 "$py" "$SKILL/scripts/hook_aprovacao.py" --selftest >/dev/null 2>&1 \
      || restaurar "hook_aprovacao.py vivo falhou o --selftest em $py"
  done
  echo "hook global: --selftest verde nos 2 Pythons"
fi
if [ "$MOTOR" = 1 ]; then
  status_todas > "$STG/.depois"
  quebradas="$(python3 - "$STG/.antes" "$STG/.depois" <<'PY'
import sys
def rd(p):
    d = {}
    for ln in open(p, encoding="utf-8"):
        c, _, w = ln.strip().partition(" ")
        if w:
            d[w] = c
    return d
a, b = rd(sys.argv[1]), rd(sys.argv[2])
print(" ".join(w for w in a if a[w] == "0" and b.get(w) != "0"))
PY
)"
  [ -z "$quebradas" ] || restaurar "campanhas que liam e passaram a falhar no status: $quebradas"
  n_camp="$(wc -l < "$STG/.depois" | tr -d ' ')"
  if [ "$n_camp" = 0 ]; then
    echo "motor: nenhuma campanha encontrada nesta máquina — nada a vigiar"
  else
    echo "motor: $n_camp campanha(s) conferida(s) com status, nenhuma regrediu"
  fi
fi
chmod -R u+w "$STG" 2>/dev/null; rm -rf "$STG"
echo "portado: ${#FILES[@]} arquivo(s) para $SKILL (backup em $BK)"
echo "próximo: tools/conferir-commit.sh $FRENTE -- ${FILES[*]}"
