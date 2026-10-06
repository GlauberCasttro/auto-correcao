#!/usr/bin/env bash
# portao.sh — PORTÃO em cópia limpa de uma frente: HEAD da skill + SÓ os arquivos da frente (de --src, padrão a
# cópia de trabalho local/work/<frente>/<skill>), e então:
#   1. sintaxe: py_compile (2 Pythons) dos .py e `bash -n` dos .sh da frente
#   2. nenhum `def`/`class` removido vs HEAD nos .py da frente (nome qualificado, via ast)
#   3. suítes da skill (scripts/tests) em python3 e /usr/bin/python3 — 0 testes conta como falha
#   4. hook_aprovacao.py --selftest nos 2 Pythons (é o hook GLOBAL: não pode quebrar)
#   5. testes do próprio harness (.claude/tools/tests), se existirem na cópia
#   6. oráculos pedidos (--oraculo DIR:MODULO, repita) nos 2 Pythons, com ORACULO_SCRIPTS/ORACULO_SKILL apontando
#      para a cópia limpa; oráculo que não lê ORACULO_SCRIPTS nem ORACULO_SKILL é recusado (testaria a skill viva)
# Saída incremental em local/portao-<frente>/portao.out (termina em FIM); manifesto portao.json (HEAD, árvore,
# sha256 de cada arquivo, resultado) que tools/conferir-commit.sh usa. A cópia testada fica em
# local/portao-<frente>/limpa/<skill>/ (o guard-entrega nega edição ali).
#
# Uso: portao.sh <frente> [--src DIR] [--oraculo DIR:MOD]... [--dry-run] -- <arquivo> [<arquivo>...]
#   arquivos relativos à raiz da skill, EXPLÍCITOS (zsh não faz word-split de $VAR: liste um por um)
# Exit: 0 VERDE · 1 VERMELHO · 2 uso inválido. Dura ~3 min (as suítes nos 2 Pythons).
set -u
. "$(dirname "${BASH_SOURCE[0]}")/_comum.sh"
FRENTE=""; SRC=""; DRY=0; ORACULOS=(); FILES=()
while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) awk 'NR>1 && !/^#/{exit} NR>1' "$0" | sed 's/^# \{0,1\}//'; exit 0;;
    --src) SRC="${2:-}"; shift;;
    --oraculo) ORACULOS+=("${2:-}"); shift;;
    --dry-run) DRY=1;;
    --) shift; FILES=("$@"); break;;
    -*) die "opção desconhecida: $1";;
    *) [ -z "$FRENTE" ] || die "uma frente só (arquivos vão depois de --)"; FRENTE="$1";;
  esac
  shift
done
[ -n "$FRENTE" ] || die "uso: portao.sh <frente> [--src DIR] [--oraculo DIR:MOD]... -- <arquivos>"
valid_frente "$FRENTE"
[ "${#FILES[@]}" -gt 0 ] || die "lista de arquivos vazia: passe os arquivos da frente depois de --"
SRC="${SRC:-$WS/work/$FRENTE/$SKILLNAME}"
[ -d "$SRC" ] || die "--src não existe: $SRC (crie a cópia com tools/copia.sh $FRENTE)"
SRC="$(cd "$SRC" && pwd -P)"
for f in "${FILES[@]}"; do
  valid_relpath "$f"
  case "$f" in *" "*) die "arquivo com espaço não suportado: '$f'";; esac
  [ -f "$SRC/$f" ] || die "não existe na fonte: $SRC/$f"
done
for o in ${ORACULOS[@]+"${ORACULOS[@]}"}; do
  d="${o%:*}"; m="${o##*:}"
  [ "$d" != "$o" ] && [ -n "$m" ] && [ -f "$d/$m.py" ] || die "--oraculo DIR:MODULO inválido ou inexistente: $o"
done
ROOT="$(repo_root)" || die "a skill não está num repo git"
PFX="$(repo_prefix)"
HEADSHA="$(git -C "$ROOT" rev-parse HEAD)"
TREE="$(skill_tree)"
P="$WS/portao-$FRENTE"
CLEAN="$P/limpa/$SKILLNAME"
if [ "$DRY" = 1 ]; then
  echo "[dry-run] HEAD ${HEADSHA:0:12} (árvore ${TREE:0:12}) + ${#FILES[@]} arquivo(s) de $SRC → $CLEAN"
  printf '  %s\n' "${FILES[@]}"
  for o in ${ORACULOS[@]+"${ORACULOS[@]}"}; do echo "  oráculo $o"; done
  echo "  suítes scripts/tests + hook selftest + harness tests em $PY1 e $PY2"
  exit 0
fi

mkdir -p "$P"
OUT="$P/portao.out"
: > "$OUT"
log() { printf '%s\n' "$*" | tee -a "$OUT"; }
FAILS=()
step() {  # step <nome> <cmd...> : roda com saída incremental; registra falha
  local nome="$1"; shift
  log "--- $nome"
  "$@" 2>&1 | tee -a "$OUT"
  local rc=${PIPESTATUS[0]}
  if [ "$rc" = 0 ]; then log "+++ ok: $nome"; else log "!!! FALHOU ($rc): $nome"; FAILS+=("$nome"); fi
}

log "== portão $FRENTE · $(agora)"
log "HEAD ${HEADSHA:0:12} · árvore da skill ${TREE:0:12} · fonte $SRC"
chmod -R u+w "$P/limpa" 2>/dev/null; rm -rf "$P/limpa"; mkdir -p "$P/limpa"
TMP="$P/limpa/.tmp"; mkdir -p "$TMP"
git -C "$ROOT" archive "$HEADSHA" -- "${PFX:-.}" | tar -x -C "$TMP" || die "git archive falhou"
if [ -n "$PFX" ]; then mv "$TMP/${PFX%/}" "$CLEAN"; rm -rf "$TMP"; else mv "$TMP" "$CLEAN"; fi
for f in "${FILES[@]}"; do
  mkdir -p "$(dirname "$CLEAN/$f")"
  cp -p "$SRC/$f" "$CLEAN/$f"
  log "arquivo $f sha256=$(sha256 "$CLEAN/$f")"
done

sintaxe() {
  local rc=0 f py
  for f in "${FILES[@]}"; do
    case "$f" in
      *.py) for py in "$PY1" "$PY2"; do
              "$py" -c 'import ast,sys; ast.parse(open(sys.argv[1],encoding="utf-8").read(), sys.argv[1])' "$CLEAN/$f" \
                || { echo "sintaxe inválida ($py): $f"; rc=1; }
            done;;
      *.sh) bash -n "$CLEAN/$f" || { echo "bash -n falhou: $f"; rc=1; };;
    esac
  done
  return $rc
}
nada_removido() {
  local f
  for f in "${FILES[@]}"; do
    case "$f" in *.py) ;; *) continue;; esac
    if git -C "$ROOT" cat-file -e "$HEADSHA:${PFX}$f" 2>/dev/null; then
      git -C "$ROOT" show "$HEADSHA:${PFX}$f" > "$P/.head.py"
      "$PY1" - "$P/.head.py" "$CLEAN/$f" "$f" <<'PY' || return 1
import ast, sys
def names(p):
    t = ast.parse(open(p, encoding="utf-8").read())
    out = set()
    def walk(node, pre):
        for ch in ast.iter_child_nodes(node):
            if isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                q = pre + ch.name
                out.add(q)
                walk(ch, q + ".")
            else:
                walk(ch, pre)
    walk(t, "")
    return out
old, new = names(sys.argv[1]), names(sys.argv[2])
gone = sorted(old - new)
if gone:
    print("REMOVIDO vs HEAD em %s: %s" % (sys.argv[3], ", ".join(gone)))
    sys.exit(1)
print("%s: %d defs/classes, nenhum removido" % (sys.argv[3], len(new)))
PY
    else
      echo "$f: arquivo novo (não existe no HEAD)"
    fi
  done
  rm -f "$P/.head.py"
}
suite() {  # suite <python> <dir com tests/>
  local out rc
  out="$(cd "$2" && PYTHONDONTWRITEBYTECODE=1 "$1" -m unittest discover -s tests 2>&1)"; rc=$?
  printf '%s\n' "$out" | tail -25
  printf '%s\n' "$out" | grep -Eq '^Ran 0 tests' && { echo "0 testes executados: vácuo conta como falha"; return 1; }
  return $rc
}
oraculo() {  # oraculo <python> <dir> <modulo>
  grep -Eq 'ORACULO_(SCRIPTS|SKILL)' "$2/$3.py" || {
    echo "o oráculo $2/$3.py não lê ORACULO_SCRIPTS nem ORACULO_SKILL: testaria a skill VIVA, não a cópia limpa"
    return 1; }
  local out rc
  out="$(cd "$2" && ORACULO_SCRIPTS="$CLEAN/scripts" ORACULO_SKILL="$CLEAN" PYTHONDONTWRITEBYTECODE=1 \
         "$1" -m unittest "$3" 2>&1)"; rc=$?
  printf '%s\n' "$out" | tail -25
  printf '%s\n' "$out" | grep -Eq '^Ran 0 tests' && { echo "0 testes executados: vácuo conta como falha"; return 1; }
  return $rc
}

step "sintaxe dos arquivos da frente" sintaxe
step "nenhum def removido vs HEAD" nada_removido
for py in "$PY1" "$PY2"; do
  step "suítes da skill ($py)" suite "$py" "$CLEAN/scripts"
done
if [ -f "$CLEAN/scripts/hook_aprovacao.py" ]; then
  for py in "$PY1" "$PY2"; do
    step "hook_aprovacao --selftest ($py)" env PYTHONDONTWRITEBYTECODE=1 "$py" "$CLEAN/scripts/hook_aprovacao.py" --selftest
  done
fi
if [ -d "$CLEAN/.claude/tools/tests" ]; then
  for py in "$PY1" "$PY2"; do
    step "testes do harness ($py)" suite "$py" "$CLEAN/.claude/tools"
  done
fi
for o in ${ORACULOS[@]+"${ORACULOS[@]}"}; do
  d="$(cd "${o%:*}" && pwd -P)"; m="${o##*:}"
  for py in "$PY1" "$PY2"; do
    step "oráculo $m ($py)" oraculo "$py" "$d" "$m"
  done
done

RES=VERDE; [ "${#FAILS[@]}" = 0 ] || RES=VERMELHO
PORTAO_JSON="$P/portao.json" "$PY1" - "$FRENTE" "$HEADSHA" "$TREE" "$SRC" "$RES" "$CLEAN" \
  "${#FILES[@]}" "${FILES[@]}" ${ORACULOS[@]+"${ORACULOS[@]}"} <<'PY'
import datetime, hashlib, json, os, sys
a = sys.argv[1:]
frente, head, tree, src, res, clean, n = a[:7]
n = int(n)
files, oraculos = a[7:7 + n], a[7 + n:]
def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()
doc = {"frente": frente, "head": head, "arvore": tree, "fonte": src, "limpa": clean, "resultado": res,
       "arquivos": [{"path": f, "sha256": sha(os.path.join(clean, f))} for f in files], "oraculos": oraculos,
       "em": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
json.dump(doc, open(os.environ["PORTAO_JSON"], "w", encoding="utf-8"), ensure_ascii=False, indent=2)
PY
chmod -R a-w "$P/limpa" 2>/dev/null
if [ "$RES" = VERDE ]; then
  log "RESULTADO: VERDE (${#FILES[@]} arquivo(s); manifesto $P/portao.json)"
else
  log "RESULTADO: VERMELHO — falharam: ${FAILS[*]}"
fi
log "FIM"
[ "$RES" = VERDE ]
