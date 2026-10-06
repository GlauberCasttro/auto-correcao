#!/usr/bin/env bash
# guard-privacidade.sh — barra termo privado em arquivo versionado e em mensagem de commit (projeto PÚBLICO).
#
# Termos: local/termos-privados.txt (um por linha, sem distinção de maiúsculas; '#' = comentário; no .gitignore,
# nunca publicado). Sem esse arquivo: AVISA e usa só os padrões genéricos (caminho /Users/<nome>, /home/<nome>,
# temporário de sessão do Claude em /private/tmp, e-mail de provedor pessoal). Placeholder de uma letra (/Users/x) é aceito.
#
# Uso: guard-privacidade.sh [--all]          arquivos rastreados + não rastreados não ignorados (padrão; pula local/)
#      guard-privacidade.sh --staged         conteúdo staged (o que o commit vai gravar) — usado pelo pre-commit
#      guard-privacidade.sh --msg-file ARQ   uma mensagem de commit — usado pelo commit-msg
#      guard-privacidade.sh --log            o histórico inteiro (git log -p --all, inclui mensagens)
#      guard-privacidade.sh --paths A [B..]  arquivos dados
#      guard-privacidade.sh --install-hooks [--dry-run]   instala .git/hooks/pre-commit e commit-msg (locais, não
#                                            versionados; rode uma vez por clone)
# Exit: 0 limpo · 1 achou termo (lista arquivo:linha) · 2 uso inválido.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/_comum.sh"
MODE=all; DRY=0; ARGS=()
while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) awk 'NR>1 && !/^#/{exit} NR>1' "$0" | sed 's/^# \{0,1\}//'; exit 0;;
    --all) MODE=all;;
    --staged) MODE=staged;;
    --log) MODE=log;;
    --msg-file) MODE=msg; ARGS=("${2:-}"); shift;;
    --paths) MODE=paths; shift; ARGS=("$@"); break;;
    --install-hooks) MODE=install;;
    --dry-run) DRY=1;;
    *) die "opção desconhecida: $1 (veja --help)";;
  esac
  shift
done
TERMOS="${AC_DEV_TERMOS:-$SKILL/local/termos-privados.txt}"

if [ "$MODE" = install ]; then
  ROOT="$(repo_root)" || die "o projeto não é um repo git"
  HK="$(git -C "$ROOT" rev-parse --git-path hooks)"
  case "$HK" in /*) ;; *) HK="$ROOT/$HK";; esac
  if [ "$DRY" = 1 ]; then echo "[dry-run] instalaria $HK/pre-commit e $HK/commit-msg"; exit 0; fi
  mkdir -p "$HK"
  printf '#!/bin/sh\n# instalado por .claude/tools/guard-privacidade.sh --install-hooks\nexec bash "$(git rev-parse --show-toplevel)/.claude/tools/guard-privacidade.sh" --staged\n' > "$HK/pre-commit"
  printf '#!/bin/sh\n# instalado por .claude/tools/guard-privacidade.sh --install-hooks\nexec bash "$(git rev-parse --show-toplevel)/.claude/tools/guard-privacidade.sh" --msg-file "$1"\n' > "$HK/commit-msg"
  chmod +x "$HK/pre-commit" "$HK/commit-msg"
  echo "hooks instalados: $HK/pre-commit (--staged) e $HK/commit-msg (--msg-file)"
  exit 0
fi
[ -f "$TERMOS" ] || echo "AVISO: $TERMOS ausente — só padrões genéricos (caminho de usuário, e-mail pessoal)" >&2

GP_MODE="$MODE" GP_SKILL="$SKILL" GP_TERMOS="$TERMOS" exec python3 - ${ARGS[@]+"${ARGS[@]}"} <<'PY'
import os, re, subprocess, sys

mode, skill, termos = os.environ["GP_MODE"], os.environ["GP_SKILL"], os.environ["GP_TERMOS"]
pats = [re.compile(r"/Users/[A-Za-z0-9._-]{2,}", re.I), re.compile(r"/home/[A-Za-z0-9._-]{2,}", re.I),
        re.compile(re.escape("/private/tmp/" + "claude" + "-"), re.I),
        re.compile(r"[A-Za-z0-9._%+-]+@(gmail|hotmail|outlook|yahoo|icloud|live|proton(mail)?)\.[A-Za-z.]+", re.I)]
if os.path.isfile(termos):
    for ln in open(termos, encoding="utf-8"):
        t = ln.strip()
        if t and not t.startswith("#"):
            pats.append(re.compile(re.escape(t), re.I))


def git(*a):
    r = subprocess.run(["git", "-C", skill] + list(a), capture_output=True)
    return r.stdout.decode("utf-8", "replace") if r.returncode == 0 else None


achados = []


def scan(nome, texto):
    for i, ln in enumerate(texto.splitlines(), 1):
        for p in pats:
            m = p.search(ln)
            if m:
                achados.append("%s:%d: %s" % (nome, i, m.group(0)))
                break


def binario(b):
    return b"\0" in b[:8192]


if mode == "all":
    lst = git("ls-files", "-co", "--exclude-standard", "-z")
    if lst is None:
        files = []
        for root, dirs, fs in os.walk(skill):
            dirs[:] = [d for d in dirs if d not in (".git", "local", "__pycache__")]
            files += [os.path.relpath(os.path.join(root, f), skill) for f in fs]
    else:
        files = [f for f in lst.split("\0") if f]
    for f in sorted(files):
        if f.split("/")[0] in ("local", ".git"):
            continue
        p = os.path.join(skill, f)
        if not os.path.isfile(p):
            continue
        b = open(p, "rb").read()
        if not binario(b):
            scan(f, b.decode("utf-8", "replace"))
    scan("(nomes de arquivo)", "\n".join(files))
elif mode == "staged":
    lst = git("diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z") or ""
    for f in [x for x in lst.split("\0") if x]:
        r = subprocess.run(["git", "-C", skill, "show", ":" + f], capture_output=True)
        if r.returncode == 0 and not binario(r.stdout):
            scan(f, r.stdout.decode("utf-8", "replace"))
        scan("(nome) " + f, f)
elif mode == "log":
    out = git("log", "-p", "--all", "--format=commit %H%nAuthor: %an <%ae>%n%n%B")
    if out is None:
        sys.exit("ERRO: git log falhou (repo sem commits?)")
    scan("git log -p --all", out)
elif mode in ("msg", "paths"):
    if not sys.argv[1:] or not all(sys.argv[1:]):
        sys.stderr.write("ERRO: faltou o arquivo\n")
        sys.exit(2)
    for f in sys.argv[1:]:
        if not os.path.isfile(f):
            sys.stderr.write("ERRO: não existe: %s\n" % f)
            sys.exit(2)
        scan(f, open(f, encoding="utf-8", errors="replace").read())
for a in achados:
    print("PRIVADO " + a)
print("guard-privacidade (%s): %s" % (mode, "%d achado(s)" % len(achados) if achados else "limpo"))
sys.exit(1 if achados else 0)
PY
