#!/usr/bin/env bash
# guard-git.sh — hook PreToolUse (Bash) do harness de desenvolvimento da auto-correcao.
#
# NEGA, quando o comando executa git (em posição de comando, inclusive após VAR=, env/sudo/time, dentro de
# `sh -c '...'`/`bash -c`/eval, e com opções globais `-C dir`, `-c k=v`, `--git-dir=`, `--no-pager`):
#   reset --hard · checkout com `--` ou `.` · restore (exceto só --staged) · clean -f/--force · stash (exceto
#   list/show) · push (sempre: push só pelo humano, no terminal dele) · add -A/--all/./:/ · commit -a/--all.
# PERMITE o resto (status, log, diff, show, add <arquivo>, commit -F <arquivo> -- <arquivos>, archive...).
# Corpo de heredoc e texto entre aspas passado a leitores (grep, cat, echo...) não é comando: não conta.
#
# Contrato: payload JSON pela stdin (tool_input.command). Nega com JSON hookSpecificOutput deny no stdout +
# exit 2 + motivo no stderr. Permite = exit 0 sem saída. Payload inválido: só nega se o texto citar git
# (hook de Bash não pode derrubar todo comando por erro de parse).
# Sem escape: o que este guard nega, o humano faz no terminal dele.
#
# Uso: guard-git.sh [--help]   (payload pela stdin)
#      guard-git.sh --check '<comando>'   (diagnóstico: imprime ALLOW ou DENY: motivo)
case "${1:-}" in
  -h|--help) awk 'NR>1 && !/^#/{exit} NR>1' "$0" | sed 's/^# \{0,1\}//'; exit 0;;
esac
PY="$(command -v python3 || echo /usr/bin/python3)"
if [ "${1:-}" = "--check" ]; then
  INPUT="$(GG_CMD="${2:-}" "$PY" -c 'import json,os;print(json.dumps({"tool_name":"Bash","tool_input":{"command":os.environ["GG_CMD"]}}))')"
  MODE=check
else
  INPUT="$(cat)"
  MODE=hook
fi
GG_INPUT="$INPUT" GG_MODE="$MODE" exec "$PY" -c '
import json, os, re, shlex, sys

SEPS = set(";&|()\n")
WRAPPERS = {"env", "nohup", "exec", "command", "builtin", "sudo", "time", "nice", "caffeinate", "noglob", "xargs"}
SHELLS = {"sh", "bash", "zsh", "dash", "ksh"}
GIT_OPTS_VAL = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--config-env"}

def strip_heredocs(cmd):
    out, delim = [], None
    for ln in cmd.split("\n"):
        if delim is not None:
            if ln.strip() == delim:
                delim = None
            continue
        out.append(ln)
        m = re.search(r"<<-?\s*([\x27\"]?)([A-Za-z_][A-Za-z0-9_]*)\1", ln)
        if m:
            delim = m.group(2)
    return "\n".join(out)

def segments(cmd):
    try:
        lex = shlex.shlex(cmd, posix=True, punctuation_chars=";&|()<>\n")
        lex.whitespace = " \t\r"
        lex.whitespace_split = True
        toks = list(lex)
    except ValueError:
        return None
    seg = []
    for t in toks:
        if t and set(t) <= set(";&|()<>\n") and not set(t) <= set("<>"):
            if seg:
                yield seg
            seg = []
        else:
            seg.append(t)
    if seg:
        yield seg

def strip_prefix(seg):
    i = 0
    while i < len(seg):
        t = seg[i]
        if re.match(r"^[A-Za-z_]\w*=", t):
            i += 1
        elif os.path.basename(t) in WRAPPERS:
            i += 1
            while i < len(seg) and seg[i].startswith("-"):
                i += 1
        else:
            break
    return seg[i:]

def git_violation(args):
    i = 0
    while i < len(args):
        a = args[i]
        if a in GIT_OPTS_VAL:
            i += 2
            continue
        if a.startswith("-"):
            i += 1
            continue
        break
    if i >= len(args):
        return None
    sub, rest = args[i], args[i + 1:]
    shorts = "".join(t[1:] for t in rest if re.match(r"^-[A-Za-z]+$", t))
    if sub == "reset" and "--hard" in rest:
        return "git reset --hard destrói trabalho não commitado"
    if sub == "checkout" and ("--" in rest or "." in rest):
        return "git checkout -- / checkout . descarta alteração do worktree sem cópia"
    if sub == "restore" and not ("--staged" in rest or "-S" in rest) or (
            sub == "restore" and ("--worktree" in rest or "-W" in rest)):
        return "git restore descarta alteração do worktree (só `restore --staged` é permitido)"
    if sub == "clean" and ("--force" in rest or "f" in shorts):
        return "git clean -f apaga arquivo não rastreado, irreversível"
    if sub == "stash" and not (rest and rest[0] in ("list", "show")):
        return "git stash tira o trabalho da vista (só stash list/show)"
    if sub == "push":
        return "git push é só do humano, no terminal dele (o harness nunca publica)"
    if sub == "add" and any(t in ("-A", "--all", ".", ":/", "*", "--no-ignore-removal") for t in rest):
        return "git add -A/--all/. junta arquivos de outras frentes e skills; adicione os arquivos da frente pelo nome"
    if sub == "add" and "A" in shorts:
        return "git add -A junta arquivos de outras frentes e skills"
    if sub == "commit":
        pre = shorts.split("m")[0].split("F")[0].split("C")[0].split("c")[0]
        if "--all" in rest or "a" in pre:
            return "git commit -a/--all commita tudo o que está sujo; commite só os arquivos da frente"
    return None

def check(cmd, depth=0):
    if depth > 5:
        return None
    cmd = strip_heredocs(cmd)
    segs = segments(cmd)
    if segs is None:
        if re.search(r"\bgit\b[^\n]*\b(reset\s+--hard|push|clean\s+-\w*f|stash)\b", cmd):
            return "comando não tokenizável parece git destrutivo (falha fechada)"
        return None
    for seg in segs:
        body = strip_prefix(seg)
        if not body:
            continue
        exe = os.path.basename(body[0])
        if exe == "git":
            why = git_violation(body[1:])
            if why:
                return why
        elif exe in SHELLS or exe == "eval":
            for t in body[1:]:
                if not t.startswith("-") or exe == "eval":
                    why = check(t, depth + 1)
                    if why:
                        return why
    return None

raw = os.environ.get("GG_INPUT", "")
mode = os.environ.get("GG_MODE")
try:
    payload = json.loads(raw)
    cmd = (payload.get("tool_input") or {}).get("command") if payload.get("tool_name") in ("Bash", None) else None
    why = check(cmd) if isinstance(cmd, str) else None
except Exception as exc:
    why = ("payload inválido (%s) citando git; falha fechada" % type(exc).__name__) if re.search(r"\bgit\b", raw) else None
if mode == "check":
    print("DENY: " + why if why else "ALLOW")
    sys.exit(2 if why else 0)
if not why:
    sys.exit(0)
msg = "guard-git: " + why + ". Ver .claude/CLAUDE.md (git e privacidade)."
print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                         "permissionDecisionReason": msg}}, ensure_ascii=False))
sys.stderr.write("BLOQUEADO (" + msg + ")\n")
sys.exit(2)
'
