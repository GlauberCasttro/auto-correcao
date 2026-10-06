"""Testes do harness de desenvolvimento da auto-correcao (unittest, stdlib; Python 3.9+).

Rodar: cd .claude/tools && PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests   (e /usr/bin/python3)
Cada teste prova um EFEITO (deny/allow, arquivo escrito ou não, exit code), não só "o comando rodou".
Os testes de copia/portao/portar/conferir/ac-estavel usam um repo git TEMPORÁRIO (AC_DEV_SKILL/AC_DEV_WS):
nunca escrevem no projeto (a skill viva) nem no repo dele.
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

TOOLS = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
SKILL = os.path.realpath(os.path.join(TOOLS, "..", ".."))
GUARD_E = os.path.join(TOOLS, "guard-entrega.py")
GUARD_G = os.path.join(TOOLS, "guard-git.sh")
GUARD_P = os.path.join(TOOLS, "guard-privacidade.sh")
HOOK_GLOBAL = os.path.join(SKILL, "scripts", "hook_aprovacao.py")


def run(cmd, stdin=None, env=None, cwd=None):
    e = dict(os.environ)
    for k in ("AC_DEV_SKILL", "AC_DEV_WS", "AC_DEV_CAMP", "AC_DEV_VIGIAR", "AC_DEV_TERMOS", "AC_FOUNDER"):
        e.pop(k, None)
    e["PYTHONDONTWRITEBYTECODE"] = "1"
    e.update(env or {})
    r = subprocess.run(cmd, input=stdin, capture_output=True, text=True, env=e, cwd=cwd)
    return r.returncode, r.stdout, r.stderr


def git(repo, *args):
    r = subprocess.run(["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"]
                       + list(args), capture_output=True, text=True)
    if r.returncode != 0:
        raise AssertionError("git %s: %s" % (args, r.stderr))
    return r.stdout.strip()


class GuardEntrega(unittest.TestCase):
    def setUp(self):
        self.ws = tempfile.mkdtemp()
        self.env = {"AC_DEV_WS": self.ws}

    def tearDown(self):
        shutil.rmtree(self.ws, ignore_errors=True)

    def decide(self, payload, raw=None):
        code, out, err = run([sys.executable, GUARD_E], stdin=raw if raw is not None else json.dumps(payload),
                             env=self.env)
        return code, out, err

    def edit(self, path, tool="Edit", cwd=None):
        p = {"tool_name": tool, "tool_input": {"file_path": path}}
        if cwd:
            p["cwd"] = cwd
        return self.decide(p)

    def assertDeny(self, res):
        code, out, err = res
        self.assertEqual(code, 2, (out, err))
        d = json.loads(out)["hookSpecificOutput"]
        self.assertEqual(d["permissionDecision"], "deny")
        self.assertEqual(d["hookEventName"], "PreToolUse")
        self.assertTrue(d["permissionDecisionReason"])

    def assertAllow(self, res):
        code, out, err = res
        self.assertEqual((code, out), (0, ""), err)

    def test_edit_in_product_denied(self):
        self.assertDeny(self.edit(os.path.join(SKILL, "scripts", "ac.py")))
        self.assertDeny(self.edit(os.path.join(SKILL, "SKILL.md"), tool="Write"))
        self.assertDeny(self.edit(os.path.join(SKILL, ".claude", "tools", "portao.sh"), tool="MultiEdit"))

    def test_edit_in_state_allowed(self):
        self.assertAllow(self.edit(os.path.join(SKILL, ".claude", "state", "RESUME.md")))
        self.assertAllow(self.edit(os.path.join(SKILL, ".claude", "state", "logs", "novo.jsonl"), tool="Write"))

    def test_edit_outside_skill_allowed(self):
        self.assertAllow(self.edit(os.path.join(self.ws, "work", "f", "auto-correcao", "scripts", "ac.py")))
        self.assertAllow(self.edit(os.path.join(self.ws, "campanhas", "f", "oraculo", "test_x.py"), tool="Write"))

    def test_relative_path_resolved_against_cwd(self):
        self.assertDeny(self.edit("scripts/ac.py", cwd=SKILL))
        self.assertAllow(self.edit("state/RESUME.md", cwd=os.path.join(SKILL, ".claude")))

    def test_symlink_into_skill_denied(self):
        link = os.path.join(self.ws, "atalho")
        os.symlink(os.path.join(SKILL, "scripts"), link)
        self.assertDeny(self.edit(os.path.join(link, "ac.py")))

    def test_stable_ac_and_portao_copies_denied(self):
        self.assertDeny(self.edit(os.path.join(self.ws, "ac-estavel", "scripts", "ac.py")))
        self.assertDeny(self.edit(os.path.join(self.ws, "portao-f1", "limpa", "auto-correcao", "scripts", "ac.py")))

    def test_invalid_payload_denied_with_reason(self):
        for raw in ("{nao json", "", "[1,2]"):
            self.assertDeny(self.decide(None, raw=raw))
        self.assertDeny(self.decide({"tool_name": "Edit", "tool_input": {}}))
        self.assertDeny(self.decide({"tool_name": "Write"}))

    def test_non_edit_tool_allowed(self):
        self.assertAllow(self.decide({"tool_name": "Read", "tool_input": {"file_path": os.path.join(SKILL, "SKILL.md")}}))

    def test_default_layout_local_and_campanhas(self):
        """Sem AC_DEV_WS/AC_DEV_CAMP: local/ e campanhas/ ficam DENTRO do projeto (layout do projeto público)."""
        def dec(path):
            return run([sys.executable, GUARD_E],
                       stdin=json.dumps({"tool_name": "Write", "tool_input": {"file_path": path}}))
        self.assertAllow(dec(os.path.join(SKILL, "local", "work", "f", "auto-correcao", "scripts", "ac.py")))
        self.assertAllow(dec(os.path.join(SKILL, "local", "notas.md")))
        self.assertAllow(dec(os.path.join(SKILL, "campanhas", "f", "oraculo", "test_x.py")))
        self.assertAllow(dec(os.path.join(SKILL, "campanhas", "README.md")))
        self.assertDeny(dec(os.path.join(SKILL, "local", "ac-estavel", "scripts", "ac.py")))
        self.assertDeny(dec(os.path.join(SKILL, "local", "portao-f", "limpa", "auto-correcao", "scripts", "ac.py")))
        self.assertDeny(dec(os.path.join(SKILL, "campanhas", "f", ".auto-correcao", "state.json")))
        self.assertDeny(dec(os.path.join(SKILL, "scripts", "hook_aprovacao.py")))
        self.assertDeny(dec(os.path.join(SKILL, "README.md")))

    def test_notebook_path(self):
        self.assertDeny(self.decide({"tool_name": "NotebookEdit",
                                     "tool_input": {"notebook_path": os.path.join(SKILL, "x.ipynb")}}))


class GuardGit(unittest.TestCase):
    DENY = ["git reset --hard", "git -C /x reset --hard HEAD~1", "git checkout -- a.py", "git checkout .",
            "git clean -fd", "git clean --force", "git stash", "git stash push -m x", "git push",
            "git push origin master", "FOO=1 git push", "env X=1 git push", "git add -A", "git add .", "git add --all",
            "git commit -am x", "git commit -a -m x", "git restore a.py", "sh -c 'git push'",
            "bash -c \"git reset --hard\"", "echo ok && git reset --hard", "true; git clean -xdf",
            "git --no-pager -c core.x=1 push", "time git push"]
    ALLOW = ["git status", "git log --oneline -5", "git diff -- a.py", "git add auto-correcao/scripts/ac.py",
             "git commit -F /x/msg.txt -- auto-correcao/scripts/ac.py", "git checkout master", "git clean -n",
             "git stash list", "git stash show", "git restore --staged a.py", "grep -n 'git push' f.md",
             "echo 'git reset --hard'", "cat > f.md <<'EOF'\ngit reset --hard\ngit push\nEOF",
             "git archive HEAD auto-correcao | tar -x -C /x", "ls -la", "git show HEAD:auto-correcao/SKILL.md"]

    def check(self, cmd):
        return run(["bash", GUARD_G], stdin=json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}}))

    def test_deny(self):
        for c in self.DENY:
            code, out, err = self.check(c)
            self.assertEqual(code, 2, "deveria negar: %r" % c)
            self.assertEqual(json.loads(out)["hookSpecificOutput"]["permissionDecision"], "deny", c)

    def test_allow(self):
        for c in self.ALLOW:
            code, out, err = self.check(c)
            self.assertEqual((code, out), (0, ""), "deveria permitir: %r (%s)" % (c, err))

    def test_invalid_payload(self):
        self.assertEqual(run(["bash", GUARD_G], stdin="{lixo")[0], 0)
        self.assertEqual(run(["bash", GUARD_G], stdin="{lixo git push")[0], 2)
        self.assertEqual(run(["bash", GUARD_G], stdin=json.dumps({"tool_name": "Read"}))[0], 0)


class ToolsHelp(unittest.TestCase):
    def test_every_tool_has_help(self):
        n = 0
        for f in sorted(os.listdir(TOOLS)):
            p = os.path.join(TOOLS, f)
            if f.startswith("_") or not os.path.isfile(p) or not f.endswith((".sh", ".py")):
                continue
            cmd = [sys.executable, p, "--help"] if f.endswith(".py") else ["bash", p, "--help"]
            code, out, err = run(cmd, stdin="")
            self.assertEqual(code, 0, "%s --help: %s" % (f, err))
            self.assertTrue(out.strip(), f)
            n += 1
        self.assertGreaterEqual(n, 12)

    def test_no_old_skill_names(self):
        s, e = "-sessao", "-epico"
        pats = ["salvar" + s, "carregar" + s, "planejar-spr" + "int", "new" + e, "close" + e, "/corr" + "igir"]
        for root, _, files in os.walk(os.path.join(SKILL, ".claude")):
            for f in files:
                with open(os.path.join(root, f), encoding="utf-8", errors="replace") as fh:
                    txt = fh.read()
                for pat in pats:
                    self.assertNotIn(pat, txt, "%s cita %s" % (os.path.join(root, f), pat))

    def test_carimbo_brief_never_fails(self):
        code, out, err = run(["bash", os.path.join(TOOLS, "carimbo.sh"), "--brief"])
        self.assertEqual(code, 0, err)
        self.assertIn("harness de desenvolvimento", out)


class RepoTemp(unittest.TestCase):
    """Skill falsa num repo git temporário: copia → portão → portar → conferir; ac-estavel; script de aprovação."""

    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp())
        self.repo = os.path.join(self.tmp, "repo")
        self.skill = os.path.join(self.repo, "ac-x")
        self.ws = os.path.join(self.tmp, "ws")
        os.makedirs(os.path.join(self.skill, "scripts", "tests"))
        os.makedirs(os.path.join(self.skill, "references"))
        self.write("scripts/a.py", "def f():\n    return 1\n\n\ndef g():\n    return 2\n" + "\n# pad\n" * 20)
        self.write("scripts/ac.py", "print('ac falso')\n")
        self.write("references/ciclo.json5", "{}\n")
        self.write("scripts/tests/test_a.py", "import os, sys, unittest\nsys.path.insert(0, os.path.dirname("
                   "os.path.dirname(os.path.abspath(__file__))))\nimport a\n\n\nclass T(unittest.TestCase):\n"
                   "    def test_f(self):\n        self.assertEqual(a.f(), 1)\n")
        git(self.repo, "init", "-q")
        git(self.repo, "add", "ac-x")
        git(self.repo, "commit", "-q", "-m", "base")
        self.env = {"AC_DEV_SKILL": self.skill, "AC_DEV_WS": self.ws, "AC_DEV_CAMP": os.path.join(self.ws, "campanhas"),
                    "AC_DEV_VIGIAR": os.path.join(self.tmp, "vigiar")}

    def tearDown(self):
        subprocess.run(["chmod", "-R", "u+w", self.tmp])
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self, rel, txt, base=None):
        p = os.path.join(base or self.skill, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(txt)

    def read(self, p):
        with open(p, encoding="utf-8") as fh:
            return fh.read()

    def tool(self, name, *args):
        p = os.path.join(TOOLS, name)
        cmd = ([sys.executable, p] if name.endswith(".py") else ["bash", p]) + list(args)
        return run(cmd, env=self.env)

    def copia(self, frente="f1"):
        code, out, err = self.tool("copia.sh", frente)
        self.assertEqual(code, 0, err)
        return out.strip().splitlines()[-1]

    def test_copia_from_head_idempotent(self):
        self.write("scripts/a.py", "SUJO\n")  # worktree sujo não vaza para a cópia
        work = self.copia()
        self.assertEqual(work, os.path.join(self.ws, "work", "f1", "ac-x"))
        self.assertIn("def g", self.read(os.path.join(work, "scripts", "a.py")))
        self.write("scripts/a.py", "trabalho do corretor\n", base=work)
        self.assertEqual(self.copia(), work)
        self.assertEqual(self.read(os.path.join(work, "scripts", "a.py")), "trabalho do corretor\n")

    def test_fluxo_portao_portar_conferir(self):
        work = self.copia()
        self.write("scripts/a.py", self.read(os.path.join(work, "scripts", "a.py")) + "\n\ndef h():\n    return 3\n",
                   base=work)
        code, out, err = self.tool("conferir-commit.sh", "f1", "--", "scripts/a.py")
        self.assertEqual(code, 2, "sem portão deve recusar")
        code, out, err = self.tool("portao.sh", "f1", "--", "scripts/a.py")
        self.assertEqual(code, 0, out + err)
        pout = self.read(os.path.join(self.ws, "portao-f1", "portao.out"))
        self.assertTrue(pout.rstrip().endswith("FIM"))
        self.assertIn("RESULTADO: VERDE", pout)
        m = json.loads(self.read(os.path.join(self.ws, "portao-f1", "portao.json")))
        self.assertEqual(m["resultado"], "VERDE")
        self.assertEqual([a["path"] for a in m["arquivos"]], ["scripts/a.py"])
        code, out, err = self.tool("conferir-commit.sh", "f1", "--", "scripts/a.py")
        self.assertEqual(code, 1, "vivo ainda não portado ⇒ difere")
        self.assertIn("DIFERE", out)
        code, out, err = self.tool("portar.sh", "f1", "--", "scripts/a.py")
        self.assertEqual(code, 0, out + err)
        self.assertIn("def h", self.read(os.path.join(self.skill, "scripts", "a.py")))
        code, out, err = self.tool("conferir-commit.sh", "f1", "--", "scripts/a.py")
        self.assertEqual(code, 0, out + err)
        code, out, err = self.tool("conferir-commit.sh", "f1", "--", "scripts/a.py", "scripts/ac.py")
        self.assertEqual(code, 1)
        self.assertIn("NÃO testou", out)
        git(self.repo, "add", "ac-x/scripts/ac.py")  # nada staged fora da frente
        self.write("scripts/ac.py", "print('outra')\n")
        git(self.repo, "add", "ac-x/scripts/ac.py")
        code, out, err = self.tool("conferir-commit.sh", "f1", "--", "scripts/a.py")
        self.assertEqual(code, 1)
        self.assertIn("staged fora da frente", out)

    def test_portao_red_when_def_removed(self):
        work = self.copia()
        self.write("scripts/a.py", "def f():\n    return 1\n", base=work)
        code, out, err = self.tool("portao.sh", "f1", "--", "scripts/a.py")
        self.assertEqual(code, 1, out)
        self.assertIn("REMOVIDO vs HEAD em scripts/a.py: g", out)
        self.assertEqual(json.loads(self.read(os.path.join(self.ws, "portao-f1", "portao.json")))["resultado"], "VERMELHO")
        code, out, err = self.tool("conferir-commit.sh", "f1", "--", "scripts/a.py")
        self.assertEqual(code, 1)
        self.assertIn("não está VERDE", out)

    def test_portao_zero_tests_is_red_and_oracle_must_read_env(self):
        work = self.copia()
        os.remove(os.path.join(work, "scripts", "tests", "test_a.py"))
        self.write("scripts/tests/test_a.py", "# vazio\n", base=work)
        code, out, err = self.tool("portao.sh", "f1", "--", "scripts/tests/test_a.py")
        self.assertEqual(code, 1)
        self.assertIn("vácuo", out)
        odir = os.path.join(self.tmp, "oraculo")
        os.makedirs(odir)
        self.write("test_o.py", "import unittest\nclass T(unittest.TestCase):\n    def test_x(self):\n        pass\n",
                   base=odir)
        work2 = self.copia("f2")
        self.assertTrue(work2)
        code, out, err = self.tool("portao.sh", "f2", "--oraculo", odir + ":test_o", "--", "scripts/a.py")
        self.assertEqual(code, 1)
        self.assertIn("não lê ORACULO_SCRIPTS", out)
        self.write("test_o.py", "import os, unittest\nS = os.environ.get('ORACULO_SCRIPTS')\n"
                   "class T(unittest.TestCase):\n    def test_x(self):\n"
                   "        self.assertTrue(os.path.isfile(os.path.join(S, 'a.py')))\n"
                   "        self.assertIn('portao-f2', S)\n", base=odir)
        code, out, err = self.tool("portao.sh", "f2", "--oraculo", odir + ":test_o", "--", "scripts/a.py")
        self.assertEqual(code, 0, out + err)

    def test_portar_three_way_merge_and_conflict(self):
        work = self.copia()
        base = self.read(os.path.join(self.skill, "scripts", "a.py"))
        self.write("scripts/a.py", base.replace("return 1", "return 10"), base=work)  # corretor: topo
        self.write("scripts/a.py", base + "\n# outra sessão\n")  # vivo: fim
        code, out, err = self.tool("portar.sh", "f1", "--", "scripts/a.py")
        self.assertEqual(code, 0, out + err)
        vivo = self.read(os.path.join(self.skill, "scripts", "a.py"))
        self.assertIn("return 10", vivo)
        self.assertIn("# outra sessão", vivo)
        self.assertIn("merge", out)
        # conflito: mesma linha mudada dos dois lados ⇒ nada escrito
        self.write("scripts/a.py", base.replace("return 2", "return 20"), base=work)
        self.write("scripts/a.py", base.replace("return 2", "return 99"))
        antes = self.read(os.path.join(self.skill, "scripts", "a.py"))
        code, out, err = self.tool("portar.sh", "f1", "--", "scripts/a.py")
        self.assertEqual(code, 1)
        self.assertIn("CONFLITO", out)
        self.assertEqual(self.read(os.path.join(self.skill, "scripts", "a.py")), antes)
        self.assertTrue(os.path.isfile(os.path.join(self.ws, "portao-f1", "conflitos", "scripts", "a.py")))

    def test_portar_refuses_state_and_dry_run_writes_nothing(self):
        work = self.copia()
        self.write("scripts/a.py", "def f():\n    return 5\n\n\ndef g():\n    return 2\n", base=work)
        antes = self.read(os.path.join(self.skill, "scripts", "a.py"))
        code, out, err = self.tool("portar.sh", "f1", "--dry-run", "--", "scripts/a.py")
        self.assertEqual(code, 0, err)
        self.assertEqual(self.read(os.path.join(self.skill, "scripts", "a.py")), antes)
        self.write(".claude/state/x.md", "x\n", base=work)
        code, out, err = self.tool("portar.sh", "f1", "--", ".claude/state/x.md")
        self.assertEqual(code, 2)

    def test_portar_motor_nada_a_vigiar_e_regressao_restaura(self):
        work = self.copia()
        self.write("scripts/ac.py", "print('ac falso v2')\n", base=work)
        code, out, err = self.tool("portar.sh", "f1", "--", "scripts/ac.py")  # máquina sem campanhas
        self.assertEqual(code, 0, out + err)
        self.assertIn("nada a vigiar", out)
        git(self.repo, "add", "ac-x/scripts/ac.py")
        git(self.repo, "commit", "-q", "-m", "v2")
        # uma campanha que o status lia (exit 0) e o ac.py novo quebra (exit 3) ⇒ restaura o backup
        camp = os.path.join(self.tmp, "vigiar", "c1", ".auto-correcao")
        os.makedirs(camp)
        with open(os.path.join(camp, "state.json"), "w") as fh:
            json.dump({"stage": "oraculo"}, fh)
        self.write("scripts/ac.py", "raise SystemExit(3)\n", base=work)
        code, out, err = self.tool("portar.sh", "f1", "--", "scripts/ac.py")
        self.assertEqual(code, 1, out + err)
        self.assertIn("RESTAURADO", err)
        self.assertEqual(self.read(os.path.join(self.skill, "scripts", "ac.py")), "print('ac falso v2')\n")

    def test_guard_privacidade(self):
        termos = os.path.join(self.tmp, "termos.txt")
        self.write("termos.txt", "# comentário\nProjetoSecreto\n", base=self.tmp)
        env = dict(self.env, AC_DEV_TERMOS=termos)
        limpo = os.path.join(self.tmp, "limpo.md")
        self.write("limpo.md", "caminho ~/.claude/skills/x e /Users/x/placeholder e noreply@users.noreply.github.com\n",
                   base=self.tmp)
        sujo = os.path.join(self.tmp, "sujo.md")
        self.write("sujo.md", "ok\nveio do projetosecreto\n", base=self.tmp)
        code, out, err = run(["bash", GUARD_P, "--paths", limpo], env=env)
        self.assertEqual(code, 0, out + err)
        code, out, err = run(["bash", GUARD_P, "--paths", limpo, sujo], env=env)
        self.assertEqual(code, 1, out)
        self.assertIn("sujo.md:2", out)
        for linha in ("/Us" + "ers/ana.silva/x", "ana.silva" + "@gm" + "ail.com"):  # genéricos, mesmo sem a lista
            self.write("g.md", linha + "\n", base=self.tmp)
            code, out, err = run(["bash", GUARD_P, "--msg-file", os.path.join(self.tmp, "g.md")], env=self.env)
            self.assertEqual(code, 1, linha)
        self.assertIn("AVISO", err)  # sem a lista de termos: avisa
        self.write("x.md", "projetosecreto\n")  # --all no repo temporário (não rastreado também conta)
        self.assertEqual(run(["bash", GUARD_P, "--all"], env=env)[0], 1)
        os.remove(os.path.join(self.skill, "x.md"))
        self.assertEqual(run(["bash", GUARD_P, "--all"], env=env)[0], 0)
        code, out, err = run(["bash", GUARD_P, "--install-hooks", "--dry-run"], env=env)
        self.assertEqual(code, 0, err)
        self.assertIn("pre-commit", out)

    def test_ac_estavel_refresh_check_and_open_campaign_refusal(self):
        code, out, err = self.tool("ac-estavel.sh", "--check")
        self.assertEqual(code, 1)
        code, out, err = self.tool("ac-estavel.sh", "--refresh")
        self.assertEqual(code, 0, out + err)
        est = os.path.join(self.ws, "ac-estavel")
        self.assertEqual(self.read(os.path.join(est, "scripts", "ac.py")), "print('ac falso')\n")
        self.assertFalse(os.path.exists(os.path.join(est, "scripts", "tests")))
        self.assertIn("commit=" + git(self.repo, "rev-parse", "HEAD"), self.read(os.path.join(est, "ORIGEM.txt")))
        self.assertEqual(self.tool("ac-estavel.sh", "--check")[0], 0)
        p = os.path.join(est, "scripts", "ac.py")
        os.chmod(p, 0o644)
        self.write("scripts/ac.py", "adulterado\n", base=est)
        self.assertEqual(self.tool("ac-estavel.sh", "--check")[0], 1)
        camp = os.path.join(self.ws, "campanhas", "c1", ".auto-correcao")
        os.makedirs(camp)
        with open(os.path.join(camp, "state.json"), "w") as fh:
            json.dump({"stage": "oraculo"}, fh)
        code, out, err = self.tool("ac-estavel.sh", "--refresh")
        self.assertEqual(code, 2)
        self.assertIn("campanha aberta", err)

    def test_script_aprovacao_literal_path_and_blocked_for_agent(self):
        camp = os.path.join(self.ws, "campanhas", "f1")
        os.makedirs(os.path.join(camp, ".auto-correcao"))
        code, out, err = self.tool("script-aprovacao.py", "f1", "--gate", "stop=critério X", "--preauth",
                                   "commit=integracao.1,integracao.2=se verde", "--conferir", "--resumo", "1. stop")
        self.assertEqual(code, 0, err)
        dest = os.path.join(camp, "aprovar-f1.sh")
        txt = self.read(dest)
        ace = os.path.join(self.ws, "ac-estavel", "scripts", "ac.py")
        self.assertIn(ace + " --work " + camp + " gate stop", txt)
        self.assertIn("--requires integracao.1 integracao.2", txt)
        self.assertIn("--by founder", txt)  # rótulo genérico (sem nome real); $AC_FOUNDER troca
        self.assertTrue(txt.rstrip().splitlines()[-2].endswith("frase conferir"))
        self.assertNotIn("$", txt)
        self.assertTrue(os.access(dest, os.X_OK))
        if os.path.isfile(HOOK_GLOBAL):  # o hook global nega o agente de rodar o script gerado
            spec = importlib.util.spec_from_file_location("hook_ac", HOOK_GLOBAL)
            hook = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(hook)
            self.assertTrue(hook.check("sh " + dest))
            self.assertTrue(hook.check("bash " + dest))
        self.assertEqual(self.tool("script-aprovacao.py", "nao-existe", "--gate", "stop")[0], 2)
        self.assertEqual(self.tool("script-aprovacao.py", "f1")[0], 2)

    def test_frente_state_render_check_close(self):
        st = os.path.join(self.skill, ".claude", "state")
        os.makedirs(st)
        self.write(".claude/state/WORKFLOW.md", "# W\n\n<!-- frentes:inicio (gerado por tools/frente.py; não edite à "
                   "mão) -->\n<!-- frentes:fim -->\n\n## Fila\n- x\n")
        self.assertEqual(self.tool("frente.py", "check")[0], 1, "bloco vazio ≠ render")
        self.assertEqual(self.tool("frente.py", "render")[0], 0)
        self.assertEqual(self.tool("frente.py", "check")[0], 0)
        wf = self.read(os.path.join(st, "WORKFLOW.md"))
        self.assertIn("nenhuma (abra com a skill new-front)", wf)
        self.assertIn("## Fila\n- x", wf)
        code, out, err = self.tool("frente.py", "open", "f1", "--scope", "a/**, b/**", "--problem", "p", "--stop", "s")
        self.assertEqual(code, 2)
        self.assertIn("vírgula", err)
        code, out, err = self.tool("frente.py", "open", "f1", "--scope", "scripts/a.py", "--problem", "p",
                                   "--stop", "s", "--dry-run")
        self.assertEqual(code, 0, err)
        self.assertIn("init --target " + self.skill, out)
        self.assertEqual(self.tool("frente.py", "close", "f1", "--commit", "HEAD")[0], 2)

    def test_sessao_log_uses_system_clock_and_refuses_fake_commit(self):
        code, out, err = self.tool("sessao.py", "log", "--resumo", "r", "--dry-run")
        self.assertEqual(code, 0, err)
        rec = json.loads(out.split("[dry-run] ", 1)[1])
        self.assertRegex(rec["ts"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        self.assertEqual(rec["head"], git(self.repo, "rev-parse", "--short", "HEAD"))
        self.assertEqual(self.tool("sessao.py", "log", "--resumo", "r", "--commit", "deadbeef")[0], 2)


if __name__ == "__main__":
    unittest.main()
