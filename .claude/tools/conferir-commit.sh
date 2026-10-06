#!/usr/bin/env bash
# conferir-commit.sh — regra: só entra no commit o que o portão TESTOU e aprovou.
# Confere, para a frente:
#   1. local/portao-<frente>/portao.json existe e o resultado é VERDE
#   2. a árvore da skill no HEAD é a mesma do portão (outra entrega na skill depois do portão ⇒ portão de novo)
#   3. os arquivos pedidos são EXATAMENTE os do portão (nem a mais, nem a menos)
#   4. cmp de cada arquivo VIVO × a cópia que o portão testou (após portar.sh)
#   5. o índice do git (staged) não tem nada fora dos arquivos da frente
#   6. nenhum termo privado nos arquivos (tools/guard-privacidade.sh: o projeto é público)
# Qualquer diferença ⇒ exit 1 e a lista. Não escreve nada.
#
# Uso: conferir-commit.sh <frente> -- <arquivo> [<arquivo>...]   (relativos à raiz da skill, explícitos)
set -u
. "$(dirname "${BASH_SOURCE[0]}")/_comum.sh"
FRENTE=""; FILES=()
while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) awk 'NR>1 && !/^#/{exit} NR>1' "$0" | sed 's/^# \{0,1\}//'; exit 0;;
    --) shift; FILES=("$@"); break;;
    -*) die "opção desconhecida: $1";;
    *) [ -z "$FRENTE" ] || die "uma frente só"; FRENTE="$1";;
  esac
  shift
done
[ -n "$FRENTE" ] && [ "${#FILES[@]}" -gt 0 ] || die "uso: conferir-commit.sh <frente> -- <arquivos>"
valid_frente "$FRENTE"
for f in "${FILES[@]}"; do valid_relpath "$f"; done
P="$WS/portao-$FRENTE"
[ -f "$P/portao.json" ] || die "sem portão para '$FRENTE' ($P/portao.json): rode tools/portao.sh antes"
ROOT="$(repo_root)" || die "a skill não está num repo git"
PFX="$(repo_prefix)"
STAGED="$(git -C "$ROOT" diff --cached --name-only)"
python3 - "$P/portao.json" "$SKILL" "$(skill_tree)" "$PFX" "$STAGED" "${FILES[@]}" <<'PY' || exit 1
import filecmp, json, os, sys
manif, skill, tree, pfx, staged = sys.argv[1:6]
pedidos = sys.argv[6:]
m = json.load(open(manif, encoding="utf-8"))
erros = []
if m.get("resultado") != "VERDE":
    erros.append("o portão não está VERDE (resultado=%r) — veja portao.out" % m.get("resultado"))
if m.get("arvore") != tree:
    erros.append("a árvore da skill mudou desde o portão (portão %s, HEAD %s): rode o portão de novo"
                 % (str(m.get("arvore"))[:12], tree[:12]))
testados = [a["path"] for a in m.get("arquivos", [])]
if sorted(set(pedidos)) != sorted(set(testados)):
    a_mais = sorted(set(pedidos) - set(testados))
    a_menos = sorted(set(testados) - set(pedidos))
    if a_mais:
        erros.append("arquivos que o portão NÃO testou: %s" % ", ".join(a_mais))
    if a_menos:
        erros.append("arquivos testados que ficariam fora do commit: %s" % ", ".join(a_menos))
for f in pedidos:
    vivo, testado = os.path.join(skill, f), os.path.join(m["limpa"], f)
    if not os.path.isfile(vivo):
        erros.append("%s: não existe na skill viva (rode tools/portar.sh)" % f)
    elif not os.path.isfile(testado) or not filecmp.cmp(vivo, testado, shallow=False):
        erros.append("%s: arquivo vivo DIFERE da cópia testada pelo portão" % f)
frente = set(pfx + f for f in pedidos)
fora = [s for s in staged.splitlines() if s.strip() and s not in frente]
if fora:
    erros.append("staged fora da frente (não commite junto): %s" % ", ".join(fora))
if erros:
    print("CONFERÊNCIA FALHOU (%s):" % m.get("frente"))
    for e in erros:
        print("  - " + e)
    sys.exit(1)
print("conferido: %d arquivo(s) vivos = cópia testada pelo portão VERDE de %s (árvore %s)"
      % (len(pedidos), m.get("em"), tree[:12]))
PY
ABS=()
for f in "${FILES[@]}"; do ABS+=("$SKILL/$f"); done
bash "$TOOLS/guard-privacidade.sh" --paths "${ABS[@]}" >/dev/null || {
  bash "$TOOLS/guard-privacidade.sh" --paths "${ABS[@]}"; echo "CONFERÊNCIA FALHOU: termo privado (acima)"; exit 1; }
