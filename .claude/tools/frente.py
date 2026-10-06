#!/usr/bin/env python3
"""frente.py — frentes de desenvolvimento da auto-correcao (frente = campanha auto-correcao).

O estado decide em .claude/state/frentes.json; o bloco "Frentes" do state/WORKFLOW.md é GERADO daqui (entre
<!-- frentes:inicio --> e <!-- frentes:fim -->; não edite à mão). Uma frente ativa por vez; outra só com --paralela,
e só se o `overlap` do ac.py estável provar escopo e oráculo disjuntos.

A campanha é aberta com o ac.py ESTÁVEL (local/ac-estavel/scripts/ac.py), por caminho literal — nunca o ac.py
em edição. Este script nunca aprova nada (gate/preauth/conferência são do founder, no terminal dele).

Uso:
  frente.py open <nome> --scope GLOB [--scope GLOB]... --problem TXT --stop TXT [--max-rounds N] [--paralela] [--dry-run]
      ac.py estável `init` em campanhas/<nome> (alvo = o projeto/skill viva), cópia de trabalho (tools/copia.sh),
      registro em frentes.json e WORKFLOW.md
  frente.py close <nome> --commit SHA [--dry-run]   exige campanha concluída (stage) e o commit existente
  frente.py abandon <nome> --why TXT                encerra sem entrega (a campanha fica no disco, como prova)
  frente.py list [--ativas] [--json]                --ativas imprime "nome|campanha" (para o carimbo)
  frente.py check                                    frentes.json válido, campanhas existem, WORKFLOW em dia
  frente.py render                                   regenera o bloco do WORKFLOW.md
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
SKILL = os.path.realpath(os.environ.get("AC_DEV_SKILL") or os.path.join(HERE, "..", ".."))
NAME = os.path.basename(SKILL)
WS = os.path.realpath(os.environ.get("AC_DEV_WS") or os.path.join(SKILL, "local"))  # local/: no .gitignore
CAMP = os.path.realpath(os.environ.get("AC_DEV_CAMP") or os.path.join(SKILL, "campanhas"))
STATE = os.path.join(SKILL, ".claude", "state")
DB = os.path.join(STATE, "frentes.json")
WORKFLOW = os.path.join(STATE, "WORKFLOW.md")
ACE = os.path.join(WS, "ac-estavel", "scripts", "ac.py")
INI, FIM = "<!-- frentes:inicio (gerado por tools/frente.py; não edite à mão) -->", "<!-- frentes:fim -->"
NOME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")


class Erro(Exception):
    pass


def agora():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load():
    if not os.path.isfile(DB):
        return {"versao": 1, "frentes": []}
    d = json.load(open(DB, encoding="utf-8"))
    if not isinstance(d, dict) or not isinstance(d.get("frentes"), list):
        raise Erro("%s inválido: esperado {\"frentes\": [...]}" % DB)
    return d


def save(d):
    os.makedirs(STATE, exist_ok=True)
    tmp = DB + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(d, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    os.replace(tmp, DB)


def ativas(d):
    return [f for f in d["frentes"] if f.get("status") == "ativa"]


def achar(d, nome):
    for f in d["frentes"]:
        if f.get("nome") == nome:
            return f
    return None


def stage(camp):
    try:
        return json.load(open(os.path.join(camp, ".auto-correcao", "state.json"), encoding="utf-8")).get("stage")
    except (OSError, ValueError):
        return None


def bloco(d):
    linhas = [INI, "### Frente(s) ativa(s)"]
    at = ativas(d)
    if not at:
        linhas.append("- nenhuma (abra com a skill new-front)")
    for f in at:
        linhas.append("- **%s** — campanha `%s` · cópia `%s` · escopo %s · aberta em %s%s · etapa: %s" % (
            f["nome"], f["campanha"], f.get("copia", "?"), ", ".join("`%s`" % g for g in f.get("scope", [])),
            f.get("aberta_em", "?"), " · PARALELA" if f.get("paralela") else "", stage(f["campanha"]) or "?"))
    linhas.append("")
    linhas.append("### Últimas entregas")
    ent = [f for f in d["frentes"] if f.get("status") in ("entregue", "abandonada")]
    ent.sort(key=lambda f: f.get("fechada_em", ""), reverse=True)
    if not ent:
        linhas.append("- nenhuma ainda")
    for f in ent[:10]:
        if f["status"] == "entregue":
            linhas.append("- %s — commit `%s` em %s" % (f["nome"], f.get("commit", "?")[:7], f.get("fechada_em", "?")))
        else:
            linhas.append("- %s — ABANDONADA em %s: %s" % (f["nome"], f.get("fechada_em", "?"), f.get("why", "")))
    linhas.append(FIM)
    return "\n".join(linhas)


def render(d, write=True):
    if not os.path.isfile(WORKFLOW):
        raise Erro("não existe %s" % WORKFLOW)
    s = open(WORKFLOW, encoding="utf-8").read()
    i, j = s.find(INI), s.find(FIM)
    if i < 0 or j < 0:
        raise Erro("WORKFLOW.md sem os marcadores do bloco de frentes")
    novo = s[:i] + bloco(d) + s[j + len(FIM):]
    if write and novo != s:
        open(WORKFLOW, "w", encoding="utf-8").write(novo)
    return novo == s


def ac_estavel(*args):
    if not os.path.isfile(ACE):
        raise Erro("ac.py estável ausente (%s): rode tools/ac-estavel.sh --refresh" % ACE)
    chk = subprocess.run(["bash", os.path.join(HERE, "ac-estavel.sh"), "--check"], capture_output=True, text=True)
    if chk.returncode != 0:
        raise Erro("ac.py estável não confere com a ORIGEM: %s" % chk.stdout.strip())
    return subprocess.run(["python3", ACE] + list(args), capture_output=True, text=True)


def cmd_open(a):
    if not NOME_RE.match(a.nome):
        raise Erro("nome de frente inválido: %r (a-z 0-9 . _ -)" % a.nome)
    d = load()
    if achar(d, a.nome):
        raise Erro("já existe frente %r em frentes.json" % a.nome)
    for g in a.scope:
        if "," in g:
            raise Erro("glob com vírgula (%r): passe um --scope por glob (AC-06)" % g)
    at = ativas(d)
    if at and not a.paralela:
        raise Erro("já há frente ativa (%s). Feche-a, ou declare --paralela (escopo e oráculo disjuntos, conferidos "
                   "pelo overlap do ac.py estável)" % ", ".join(f["nome"] for f in at))
    camp = os.path.join(CAMP, a.nome)
    if os.path.exists(camp):
        raise Erro("a campanha já existe no disco: %s" % camp)
    init = ["--work", camp, "init", "--target", SKILL, "--problem", a.problem, "--stop", a.stop]
    for g in a.scope:
        init += ["--scope", g]
    if a.max_rounds:
        init += ["--max-rounds", str(a.max_rounds)]
    if a.dry_run:
        print("[dry-run] python3 %s %s" % (ACE, " ".join(init)))
        print("[dry-run] bash %s %s" % (os.path.join(HERE, "copia.sh"), a.nome))
        return 0
    r = ac_estavel(*init)
    sys.stdout.write(r.stdout)
    if r.returncode != 0:
        raise Erro("ac.py init falhou: %s" % (r.stderr or r.stdout).strip())
    if at:
        for f in at:
            ov = ac_estavel("--work", camp, "overlap", "--other", f["campanha"])
            if ov.returncode != 0:
                dest = os.path.join(CAMP, "_descartadas", "%s-%s" % (a.nome, agora().replace(":", "")))
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                os.rename(camp, dest)
                raise Erro("colide com a frente ativa %s: %s (campanha movida para %s)"
                           % (f["nome"], (ov.stdout + ov.stderr).strip(), dest))
    c = subprocess.run(["bash", os.path.join(HERE, "copia.sh"), a.nome], capture_output=True, text=True)
    if c.returncode != 0:
        raise Erro("copia.sh falhou: %s" % c.stderr.strip())
    copia = c.stdout.strip().splitlines()[-1]
    d["frentes"].append({"nome": a.nome, "status": "ativa", "campanha": camp, "copia": copia, "scope": a.scope,
                         "problema": a.problem, "parada": a.stop, "paralela": bool(at), "aberta_em": agora(),
                         "ac_estavel": ACE})
    save(d)
    render(d)
    print("frente %s aberta\n  campanha: %s\n  cópia de trabalho: %s" % (a.nome, camp, copia))
    print("próximo: oráculo por agente SEPARADO → `oracle freeze` (estável) → tools/script-aprovacao.py %s ..." % a.nome)
    return 0


def cmd_close(a):
    d = load()
    f = achar(d, a.nome)
    if not f or f.get("status") != "ativa":
        raise Erro("frente %r não está ativa" % a.nome)
    st = stage(f["campanha"])
    if st != "concluida":
        raise Erro("campanha %s não está concluída (etapa %r): feche-a com o ac.py estável antes" % (f["campanha"], st))
    root = subprocess.run(["git", "-C", SKILL, "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    sha = subprocess.run(["git", "-C", SKILL, "rev-parse", "--verify", a.commit + "^{commit}"],
                         capture_output=True, text=True)
    if root.returncode != 0 or sha.returncode != 0:
        raise Erro("commit %r não existe no repo da skill" % a.commit)
    sha = sha.stdout.strip()
    if a.dry_run:
        print("[dry-run] fecharia %s com commit %s" % (a.nome, sha[:12]))
        return 0
    f.update({"status": "entregue", "commit": sha, "fechada_em": agora()})
    save(d)
    render(d)
    print("frente %s entregue (commit %s)" % (a.nome, sha[:12]))
    return 0


def cmd_abandon(a):
    d = load()
    f = achar(d, a.nome)
    if not f or f.get("status") != "ativa":
        raise Erro("frente %r não está ativa" % a.nome)
    if not (a.why or "").strip():
        raise Erro("--why obrigatório")
    f.update({"status": "abandonada", "why": a.why, "fechada_em": agora()})
    save(d)
    render(d)
    print("frente %s abandonada (campanha mantida em %s)" % (a.nome, f["campanha"]))
    return 0


def cmd_list(a):
    d = load()
    fs = ativas(d) if a.ativas else d["frentes"]
    if a.json:
        print(json.dumps(fs, ensure_ascii=False, indent=2))
    elif a.ativas:
        for f in fs:
            print("%s|%s" % (f["nome"], f["campanha"]))
    else:
        for f in fs:
            print("%-24s %-10s %s" % (f["nome"], f.get("status"), f.get("commit", f["campanha"])))
    return 0


def cmd_check(a):
    d = load()
    erros = []
    for f in d["frentes"]:
        if f.get("status") not in ("ativa", "entregue", "abandonada"):
            erros.append("%s: status inválido %r" % (f.get("nome"), f.get("status")))
        if f.get("status") == "ativa" and not os.path.isdir(os.path.join(f.get("campanha", ""), ".auto-correcao")):
            erros.append("%s: campanha ativa sem .auto-correcao/ em %s" % (f.get("nome"), f.get("campanha")))
    if len(ativas(d)) > 1 and not all(f.get("paralela") for f in ativas(d)[1:]):
        erros.append("mais de uma frente ativa sem declaração --paralela")
    try:
        if not render(d, write=False):
            erros.append("WORKFLOW.md fora de dia com frentes.json (rode frente.py render)")
    except Erro as e:
        erros.append(str(e))
    for e in erros:
        print("ERRO: " + e)
    print("frentes: %d (%d ativa[s]) — %s" % (len(d["frentes"]), len(ativas(d)), "ok" if not erros else "FALHOU"))
    return 1 if erros else 0


def cmd_render(a):
    render(load())
    print("WORKFLOW.md: bloco de frentes regenerado")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="frente.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("open")
    s.add_argument("nome")
    s.add_argument("--scope", action="append", required=True)
    s.add_argument("--problem", required=True)
    s.add_argument("--stop", required=True)
    s.add_argument("--max-rounds", dest="max_rounds", type=int)
    s.add_argument("--paralela", action="store_true")
    s.add_argument("--dry-run", dest="dry_run", action="store_true")
    s = sub.add_parser("close")
    s.add_argument("nome")
    s.add_argument("--commit", required=True)
    s.add_argument("--dry-run", dest="dry_run", action="store_true")
    s = sub.add_parser("abandon")
    s.add_argument("nome")
    s.add_argument("--why", required=True)
    s = sub.add_parser("list")
    s.add_argument("--ativas", action="store_true")
    s.add_argument("--json", action="store_true")
    sub.add_parser("check")
    sub.add_parser("render")
    a = p.parse_args(argv)
    try:
        return {"open": cmd_open, "close": cmd_close, "abandon": cmd_abandon, "list": cmd_list, "check": cmd_check,
                "render": cmd_render}[a.cmd](a)
    except Erro as e:
        sys.stderr.write("ERRO: %s\n" % e)
        return 2


if __name__ == "__main__":
    sys.exit(main())
