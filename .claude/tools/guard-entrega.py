#!/usr/bin/env python3
"""guard-entrega.py — hook PreToolUse (Edit|Write|MultiEdit|NotebookEdit) do harness de desenvolvimento da auto-correcao.

Nega edição direta no PRODUTO da skill: tudo dentro do projeto (= a skill) exceto .claude/state/**, campanhas/**
(oráculos; menos os ledgers campanhas/*/.auto-correcao/**) e local/** (área desta máquina, no .gitignore).
Toda mudança de produto entra pelo fluxo: frente (campanha) → cópia de trabalho (tools/copia.sh) → portão em cópia
limpa (tools/portao.sh) → tools/portar.sh → tools/conferir-commit.sh → commit só dos arquivos da frente.

Também nega (integridade das provas): local/ac-estavel/** (o ac.py que julga as campanhas desta skill),
local/portao-*/** (a cópia que o portão testou; o commit é conferido contra ela) e campanhas/*/.auto-correcao/**
(ledger e estado da campanha: só o ac.py escreve ali).
Permite o resto: cópias de trabalho (local/work/**), oráculos e notas das campanhas, fora do projeto.

Contrato: lê o payload JSON do hook pela stdin; usa tool_input.file_path (ou notebook_path). Nega com
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":...}}
no stdout + exit 2 + motivo no stderr (os dois caminhos, se um for ignorado o outro morde). Permite = exit 0 sem saída.
Payload inválido ou sem caminho ⇒ deny com motivo (falha fechada: este hook só roda quando a sessão é aberta na skill).

Limite honesto: só vale para as ferramentas de edição. Bash (cp, sed -i, >) não passa por aqui; o fluxo usa
tools/portar.sh, que é o caminho sancionado. Uso: guard-entrega.py [--help] (payload pela stdin).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
FLUXO = ("Fluxo: tools/frente.py open (campanha) → tools/copia.sh <frente> → edite a CÓPIA → tools/portao.sh → "
         "tools/portar.sh → tools/conferir-commit.sh → commit só dos arquivos da frente. Estado em .claude/state/ é livre.")


def paths():
    skill = os.path.realpath(os.environ.get("AC_DEV_SKILL") or os.path.join(HERE, "..", ".."))
    ws = os.path.realpath(os.environ.get("AC_DEV_WS") or os.path.join(skill, "local"))
    camp = os.path.realpath(os.environ.get("AC_DEV_CAMP") or os.path.join(skill, "campanhas"))
    return skill, ws, camp


def inside(path, root):
    return path == root or path.startswith(root.rstrip(os.sep) + os.sep)


def decide(payload):
    """(permitir: bool, motivo: str)."""
    if not isinstance(payload, dict):
        return False, "payload do hook não é um objeto JSON"
    tool = payload.get("tool_name")
    if tool not in EDIT_TOOLS:
        return True, "ferramenta %r não é de edição" % (tool,)
    ti = payload.get("tool_input")
    if not isinstance(ti, dict):
        return False, "payload sem tool_input"
    fp = ti.get("file_path") or ti.get("notebook_path")
    if not isinstance(fp, str) or not fp.strip():
        return False, "payload sem tool_input.file_path"
    fp = os.path.expanduser(fp)
    if not os.path.isabs(fp):
        cwd = payload.get("cwd") if isinstance(payload.get("cwd"), str) else os.getcwd()
        fp = os.path.join(cwd, fp)
    real = os.path.realpath(fp)
    skill, ws, camp = paths()
    if inside(real, os.path.join(ws, "ac-estavel")):
        return False, ("%s é o ac.py ESTÁVEL que julga as campanhas desta skill; ninguém o edita. Atualize só por "
                       "tools/ac-estavel.sh --refresh (de um commit, sem campanha aberta)." % real)
    if inside(real, ws) and real != ws and os.path.relpath(real, ws).split(os.sep)[0].startswith("portao-"):
        return False, ("%s está numa cópia de PORTÃO (prova do que foi testado; o commit é conferido contra ela). "
                       "Edite a cópia de trabalho e rode o portão de novo." % real)
    if inside(real, camp) and real != camp and ".auto-correcao" in os.path.relpath(real, camp).split(os.sep):
        return False, ("%s é ledger/estado de campanha: só o ac.py escreve ali (editar à mão falsifica a prova)."
                       % real)
    if inside(real, os.path.join(skill, ".claude", "state")):
        return True, "estado do harness"
    if inside(real, ws):
        return True, "área local desta máquina (cópias de trabalho, notas)"
    if inside(real, camp):
        return True, "campanhas (oráculos e notas)"
    if inside(real, skill):
        return False, "edição direta no produto da skill (%s) é proibida. %s" % (os.path.relpath(real, skill), FLUXO)
    return True, "fora da skill"


def emit_deny(reason):
    sys.stdout.write(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                                        "permissionDecisionReason": "guard-entrega: " + reason}},
                                ensure_ascii=False) + "\n")
    sys.stderr.write("BLOQUEADO (guard-entrega): %s\n" % reason)
    return 2


def main(argv):
    if "--help" in argv or "-h" in argv:
        print(__doc__.strip())
        return 0
    try:
        payload = json.loads(sys.stdin.read())
    except Exception as exc:  # noqa: BLE001
        return emit_deny("payload inválido (%s); falha fechada" % type(exc).__name__)
    try:
        ok, why = decide(payload)
    except Exception as exc:  # noqa: BLE001
        return emit_deny("erro interno (%s: %s); falha fechada" % (type(exc).__name__, exc))
    return 0 if ok else emit_deny(why)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
