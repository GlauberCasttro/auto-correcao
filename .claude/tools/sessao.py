#!/usr/bin/env python3
"""sessao.py — log append-only das sessões de desenvolvimento (.claude/state/logs/sessoes.jsonl).

Data, HEAD e branch vêm do sistema (relógio e git), nunca do modelo: não se fabrica data nem commit.

Uso:
  sessao.py log --resumo TXT [--frente NOME] [--proximo TXT] [--commit SHA] [--dry-run]   acrescenta uma linha
  sessao.py tail [-n N]                                                                    últimas N (padrão 5)
  sessao.py check                                                                          toda linha é JSON com ts/resumo
"""
import argparse
import datetime
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
SKILL = os.path.realpath(os.environ.get("AC_DEV_SKILL") or os.path.join(HERE, "..", ".."))
LOG = os.path.join(SKILL, ".claude", "state", "logs", "sessoes.jsonl")


def git(*args):
    r = subprocess.run(["git", "-C", SKILL] + list(args), capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def main(argv=None):
    p = argparse.ArgumentParser(prog="sessao.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("log")
    s.add_argument("--resumo", required=True)
    s.add_argument("--frente")
    s.add_argument("--proximo")
    s.add_argument("--commit")
    s.add_argument("--dry-run", dest="dry_run", action="store_true")
    s = sub.add_parser("tail")
    s.add_argument("-n", type=int, default=5)
    sub.add_parser("check")
    a = p.parse_args(argv)
    if a.cmd == "log":
        if not a.resumo.strip():
            sys.stderr.write("ERRO: --resumo vazio\n")
            return 2
        if a.commit and not git("rev-parse", "--verify", a.commit + "^{commit}"):
            sys.stderr.write("ERRO: commit %r não existe (não se fabrica commit)\n" % a.commit)
            return 2
        rec = {"ts": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               "branch": git("rev-parse", "--abbrev-ref", "HEAD"), "head": git("rev-parse", "--short", "HEAD"),
               "frente": a.frente, "resumo": a.resumo.strip(), "proximo": a.proximo, "commit": a.commit}
        linha = json.dumps({k: v for k, v in rec.items() if v is not None}, ensure_ascii=False)
        if a.dry_run:
            print("[dry-run] " + linha)
            return 0
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write(linha + "\n")
        print("registrado em %s" % LOG)
        return 0
    linhas = open(LOG, encoding="utf-8").read().splitlines() if os.path.isfile(LOG) else []
    if a.cmd == "tail":
        for ln in linhas[-a.n:]:
            print(ln)
        return 0
    bad = 0
    for i, ln in enumerate(linhas, 1):
        try:
            r = json.loads(ln)
            if not (isinstance(r, dict) and r.get("ts") and r.get("resumo")):
                raise ValueError("sem ts/resumo")
        except ValueError as e:
            print("linha %d inválida: %s" % (i, e))
            bad += 1
    print("sessoes.jsonl: %d linha(s), %d inválida(s)" % (len(linhas), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
