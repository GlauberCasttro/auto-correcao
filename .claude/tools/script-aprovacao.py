#!/usr/bin/env python3
"""script-aprovacao.py — GERA (não roda) o script de aprovação humana de uma frente, para o FOUNDER rodar no terminal
dele com a senha. A IA nunca executa o script gerado, nunca aprova, nunca pede a senha no chat (o hook global
hook_aprovacao.py nega a execução de aprovar-*.sh e de ac.py com subcomando aprovador vindo do agente).

O script gerado chama o ac.py ESTÁVEL por caminho LITERAL (sem variável: o hook nega `$VAR` + subcomando aprovador),
encadeia com && e termina com a conferência das aprovações (recomendado: a conferência depois da última aprovação
satisfaz o `done decisao`).

Uso:
  script-aprovacao.py <frente> [--by NOME] [--resumo TXT]... [--gate NOME=NOTA]... [--preauth NOME=REQ1,REQ2[=NOTA]]...
                      [--conferir] [--so-conferir] [--dry-run]
  ex.: script-aprovacao.py ac-v05 --gate stop="critério v0.5" --gate oracle:requisito="oráculo 12 testes" \\
         --preauth commit=integracao.1="commit se verde" --conferir --resumo "1. stop: ..."
Saída: campanhas/<frente>/aprovar-<frente>.sh (ou aprovar-<frente>-conferir.sh com --so-conferir) — no .gitignore
(tem caminho absoluto desta máquina). --by: padrão $AC_FOUNDER ou "founder" (rótulo; a prova é a tag HMAC da senha).
"""
import argparse
import json
import os
import shlex
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
SKILL = os.path.realpath(os.environ.get("AC_DEV_SKILL") or os.path.join(HERE, "..", ".."))
NAME = os.path.basename(SKILL)
WS = os.path.realpath(os.environ.get("AC_DEV_WS") or os.path.join(SKILL, "local"))  # local/: no .gitignore
CAMP = os.path.realpath(os.environ.get("AC_DEV_CAMP") or os.path.join(SKILL, "campanhas"))
ACE = os.path.join(WS, "ac-estavel", "scripts", "ac.py")


def main(argv=None):
    p = argparse.ArgumentParser(prog="script-aprovacao.py", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("frente")
    p.add_argument("--by", default=os.environ.get("AC_FOUNDER") or "founder")
    p.add_argument("--resumo", action="append", default=[])
    p.add_argument("--gate", action="append", default=[])
    p.add_argument("--preauth", action="append", default=[])
    p.add_argument("--conferir", action="store_true")
    p.add_argument("--so-conferir", dest="so_conferir", action="store_true")
    p.add_argument("--dry-run", dest="dry_run", action="store_true")
    a = p.parse_args(argv)
    camp = os.path.join(CAMP, a.frente)
    if not os.path.isdir(os.path.join(camp, ".auto-correcao")):
        sys.stderr.write("ERRO: campanha inexistente: %s (abra a frente com tools/frente.py open)\n" % camp)
        return 2
    if a.so_conferir and (a.gate or a.preauth):
        sys.stderr.write("ERRO: --so-conferir não combina com --gate/--preauth\n")
        return 2
    if not (a.gate or a.preauth or a.so_conferir):
        sys.stderr.write("ERRO: nada a aprovar: passe --gate/--preauth (ou --so-conferir)\n")
        return 2
    base = ["python3", ACE, "--work", camp]
    cmds = []
    for g in a.gate:
        nome, _, nota = g.partition("=")
        if not nome:
            sys.stderr.write("ERRO: --gate NOME=NOTA\n")
            return 2
        cmds.append(base + ["gate", nome, "--by", a.by, "--decision", "approve"] + (["--note", nota] if nota else []))
    for pa in a.preauth:
        partes = pa.split("=", 2)
        if len(partes) < 2 or not partes[0] or not partes[1]:
            sys.stderr.write("ERRO: --preauth NOME=REQ1,REQ2[=NOTA]\n")
            return 2
        reqs = [r for r in partes[1].split(",") if r]
        cmds.append(base + ["preauth", partes[0], "--by", a.by, "--requires"] + reqs +
                    (["--note", partes[2]] if len(partes) > 2 and partes[2] else []))
    if a.conferir or a.so_conferir:
        cmds.append(base + ["frase", "conferir"])
    nome_arq = "aprovar-%s%s.sh" % (a.frente, "-conferir" if a.so_conferir else "")
    dest = os.path.join(camp, nome_arq)
    linhas = ["#!/bin/sh",
              "# Aprovações da frente %s (auto-correcao, harness de desenvolvimento). Rode NO SEU TERMINAL." % a.frente,
              "# Cada passo pede a sua SENHA (sem eco). Nunca a digite no chat. Gerado por tools/script-aprovacao.py.",
              "# ac.py ESTÁVEL: %s" % ACE, "#"]
    linhas += ["# " + r for r in a.resumo] or ["# (sem resumo)"]
    linhas.append("set -e")
    for c in cmds:
        linhas.append(" ".join(shlex.quote(x) for x in c))
    linhas.append('echo "OK — feito. Pode avisar o Claude."')
    texto = "\n".join(linhas) + "\n"
    if a.dry_run:
        sys.stdout.write(texto)
        return 0
    with open(dest, "w", encoding="utf-8") as fh:
        fh.write(texto)
    os.chmod(dest, 0o755)
    print(json.dumps({"script": dest, "passos": len(cmds)}, ensure_ascii=False))
    print("Peça ao founder para rodar no terminal dele: sh %s" % dest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
