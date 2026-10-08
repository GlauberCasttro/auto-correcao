"""Testes do ac.py — cada um prova uma trava da skill (efeito, não só 'o comando rodou')."""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ac  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _pty_helper import FRASE_TESTE, frase_json_teste, precisa_pty, run_tty  # noqa: E402  (portão humano: pty real + frase)

REFS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "references")


def run(work, *argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = ac.main(["--work", work] + list(argv))
    return code, out.getvalue() + err.getvalue()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.work = os.path.join(self.tmp, "camp")
        self.target = os.path.join(self.tmp, "alvo")
        os.makedirs(os.path.join(self.target, "evals"))
        self.grader = os.path.join(self.target, "evals", "grader.py")
        with open(self.grader, "w", encoding="utf-8") as fh:
            fh.write("print('ok')\n")

    def human(self, *argv, frase=FRASE_TESTE):
        """Portão/pré-autorização pelo canal humano (v0.4): terminal (pty) com a FRASE do founder de teste, gravada
        num AC_FRASE_FILE temporário (o ~/.claude/auto-correcao real nunca é tocado)."""
        ff = os.path.join(self.tmp, "segredo", "frase.json")
        if not os.path.isfile(ff):
            frase_json_teste(ff)
        env = {k: v for k, v in os.environ.items() if not k.startswith("AC_")}
        env.update(AC_AUDIT_LOG=os.path.join(self.tmp, "auditoria", "audit.jsonl"), AC_FRASE_FILE=ff)
        code, out, _ = run_tty(self.work, *argv, env=env, answers=[frase])
        return code, out

    def init(self):
        self.assertEqual(run(self.work, "init", "--target", self.target, "--scope", "src/**", "--problem", "p",
                             "--stop", "qualidade>=13/13 em 3 alvos", "--max-rounds", "2")[0], 0)

    def write(self, rel, data):
        p = os.path.join(self.work, ".auto-correcao", "rounds", "0", rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(data)
        return p


class Json5Test(unittest.TestCase):
    def test_references_parse(self):
        for f in ("ciclo.json5", "licoes.json5", "formatos.json5", "prompts.json5"):
            d = ac.json5_load(os.path.join(REFS, f))
            self.assertIsInstance(d, dict, f)
        p = ac.json5_load(os.path.join(REFS, "prompts.json5"))
        self.assertIn("NUNCA edite o oráculo", p["frente_correcao"])

    def test_comment_inside_string_kept(self):
        self.assertEqual(ac.json5_loads('{a: "x // y", b: [1,2,],}'), {"a": "x // y", "b": [1, 2]})


class GatesTest(Base):
    @precisa_pty
    def test_stop_criterion_needs_human_gate(self):
        self.init()
        code, out = run(self.work, "check", "intake.3")
        self.assertEqual(code, 1)
        self.assertIn("portão 'stop'", out)
        self.assertEqual(self.human("gate", "stop", "--by", "founder", "--decision", "approve",
                                    frase="frase errada de agente")[0], 1)  # sem a frase não aprova
        self.assertEqual(run(self.work, "check", "intake.3")[0], 1)
        self.assertEqual(self.human("gate", "stop", "--by", "founder", "--decision", "approve")[0], 0)
        self.assertEqual(run(self.work, "check", "intake.3")[0], 0)

    def test_load_refuses_until_previous_stage_closes(self):
        self.init()
        code, out = run(self.work, "load", "oraculo")
        self.assertEqual(code, 1)
        self.assertIn("intake", out)


class OracleTest(Base):
    def test_tamper_detected_and_change_requires_evidence(self):
        self.init()
        self.assertEqual(run(self.work, "oracle", "freeze", "--file", self.grader)[0], 0)
        self.assertEqual(run(self.work, "oracle", "verify")[0], 0)
        with open(self.grader, "a", encoding="utf-8") as fh:
            fh.write("# fazer passar\n")
        code, out = run(self.work, "oracle", "verify")
        self.assertEqual(code, 1)
        self.assertIn("mudou fora de `oracle change`", out)
        self.assertEqual(run(self.work, "oracle", "change", "--why", "x")[0], 2)
        self.assertEqual(run(self.work, "oracle", "change", "--why", "campo errado",
                             "--evidence", "conferido à mão: x.json linha 3")[0], 0)
        self.assertEqual(run(self.work, "oracle", "verify")[0], 0)

    def test_set_cannot_touch_oracle_hash(self):
        self.init()
        self.assertEqual(run(self.work, "set", "oracle.hash", "abc")[0], 2)


class CalibrationTest(Base):
    def test_weak_calibration_rejected(self):
        self.init()
        c = ac.Campaign(self.work)
        run(self.work, "set", "oracle.calibration", '{"vazio": 0.3, "bom": 1.0, "configs": 1, "conferencias": []}')
        with self.assertRaises(ac.Fail) as e:
            ac.chk_calibration(c, c.load(), [])
        self.assertIn("vazia", str(e.exception))
        self.assertIn("mínimo 2", str(e.exception))
        run(self.work, "set", "oracle.calibration", '{"vazio": 0.0, "bom": 1.0, "configs": 1, "conferencias": ['
            '{"assercao": "a", "correto": true, "evidencia": "x:1"}, {"assercao": "b", "correto": false, "evidencia": "y:2"}]}')
        with self.assertRaises(ac.Fail) as e:
            ac.chk_calibration(c, c.load(), [])
        self.assertIn("oráculo errou", str(e.exception))


class RequisitoModeTest(Base):
    """L15: requisito novo calibra por vazio≈0 + spec por arquivo + portão humano (não simulado)."""

    @precisa_pty
    def test_requisito_mode(self):
        self.init()
        c = ac.Campaign(self.work)
        run(self.work, "oracle", "freeze", "--file", self.grader)
        run(self.work, "set", "oracle.calibration", '{"modo": "requisito", "vazio": 0.0, "spec": {}}')
        with self.assertRaises(ac.Fail) as e:
            ac.chk_calibration(c, c.load(), [])
        self.assertIn("sem seção de especificação", str(e.exception))
        self.assertIn("oracle:requisito", str(e.exception))
        run(self.work, "set", "oracle.calibration", '{"modo": "requisito", "vazio": 0.0, "spec": {"grader.py": "ROADMAP §X"}}')
        run(self.work, "gate", "oracle:requisito", "--by", "bot", "--decision", "approve", "--simulated")
        self.assertRaises(ac.Fail, ac.chk_calibration, c, c.load(), [])
        self.assertEqual(self.human("gate", "oracle:requisito", "--by", "founder", "--decision", "approve")[0], 0)
        ac.chk_calibration(c, c.load(), [])


class PreauthTest(Base):
    @precisa_pty
    def test_preauth_conditional_and_human(self):
        self.init()
        c = ac.Campaign(self.work)
        self.assertEqual(self.human("preauth", "commit", "--by", "founder", "--requires", "integracao.1", "--simulated")[0], 2)
        with self.assertRaises(SystemExit):  # sem --requires o argparse recusa (nunca incondicional)
            with contextlib.redirect_stderr(io.StringIO()):
                ac.main(["--work", self.work, "preauth", "commit", "--by", "founder"])
        self.assertEqual(self.human("preauth", "commit", "--by", "founder", "--requires", "integracao.1", "integracao.2")[0], 0)
        self.assertEqual(run(self.work, "set", "preauth.commit", '{"by":"x"}')[0], 2)
        with self.assertRaises(ac.Fail) as e:
            ac.chk_gate_ok(c, c.load(), ["commit"])
        self.assertIn("faltam", str(e.exception))
        st = c.load()
        st["done"]["integracao.1"] = st["done"]["integracao.2"] = "x"
        c.save(st, "test")
        ac.chk_gate_ok(c, c.load(), ["commit"])


class PlanTest(Base):
    def setUp(self):
        super().setUp()
        self.init()
        run(self.work, "oracle", "freeze", "--file", self.grader)

    def test_overlapping_fronts_rejected(self):
        self.write("PLANO.json5", '{parada: "x", frentes: [{nome: "a", escreve: ["scripts/team/**"]},'
                                  '{nome: "b", escreve: ["scripts/**"]}]}')
        code, out = run(self.work, "plan", "check")
        self.assertEqual(code, 1)
        self.assertIn("se sobrepõem", out)

    def test_front_writing_oracle_rejected(self):
        self.write("PLANO.json5", '{parada: "x", frentes: [{nome: "a", escreve: ["evals/**"]}]}')
        code, out = run(self.work, "plan", "check")
        self.assertEqual(code, 1)
        self.assertIn("escreve no oráculo", out)

    @precisa_pty
    def test_disjoint_plan_ok_and_product_decision_needs_gate(self):
        self.write("PLANO.json5", '{parada: "x", decisoes: [{id: "DEC-1", produto: true}],'
                                  'frentes: [{nome: "a", escreve: ["scripts/scan/**"]}, {nome: "b", escreve: ["SKILL.md"]}]}')
        self.assertEqual(run(self.work, "plan", "check")[0], 0)
        self.assertEqual(run(self.work, "plan", "gates")[0], 1)
        self.assertEqual(self.human("gate", "plan:DEC-1", "--by", "founder", "--decision", "approve")[0], 0)
        self.assertEqual(run(self.work, "plan", "gates")[0], 0)


class RunsAndDefectsTest(Base):
    def test_runs_need_grading_and_defects_need_evidence_and_class(self):
        self.init()
        st = ac.Campaign(self.work)
        self.assertRaises(ac.Fail, ac.chk_runs, st, st.load(), ["--min", "1"])
        g = os.path.join(self.tmp, "grading.json")
        with open(g, "w", encoding="utf-8") as fh:
            json.dump({"summary": {"quality": {"passed": 13, "total": 13}, "structure": {"passed": 30, "total": 40}}}, fh)
        run(self.work, "run", "record", "--config", "sistema", "--alvo", "py", "--grading", g, "--tokens", "100")
        ac.chk_runs(st, st.load(), ["--min", "1", "--graded"])
        self.write("DEFEITOS.json5", '{defeitos: [{id: "D-0-01", classe: "sistema", prioridade: "P0"}]}')
        code, out = run(self.work, "defects", "check")
        self.assertEqual(code, 1)
        self.assertIn("sem evidência", out)
        self.write("DEFEITOS.json5", '{defeitos: [{id: "D-0-01", classe: "talvez", prioridade: "P0", evidencia: ["x"]}]}')
        self.assertEqual(run(self.work, "defects", "check")[0], 1)

    def test_baseline_waiver_counts(self):
        self.init()
        st = ac.Campaign(self.work)
        self.assertRaises(ac.Fail, ac.chk_runs, st, st.load(), ["--round", "0", "--config", "baseline", "--or-waived"])
        run(self.work, "run", "waive", "--config", "baseline", "--why", "sem versão sem o sistema")
        ac.chk_runs(st, st.load(), ["--round", "0", "--config", "baseline", "--or-waived"])


class RoundTest(Base):
    def test_budget_blocks_extra_round(self):
        self.init()  # max-rounds 2
        c = ac.Campaign(self.work)
        cy = ac.ciclo()
        st = c.load()
        for name in cy["order"]:
            for sub in cy["stages"][name]["substages"]:
                st["done"][sub["id"]] = "x"
        c.save(st, "test")
        for r in range(2):
            st = c.load()
            for name in cy["per_round"]:
                for sub in cy["stages"][name]["substages"]:
                    st["done"][sub["id"]] = "x"
            c.save(st, "test")
            self.assertEqual(run(self.work, "round", "new")[0], 0)
        st = c.load()
        for name in cy["per_round"]:
            for sub in cy["stages"][name]["substages"]:
                st["done"][sub["id"]] = "x"
        c.save(st, "test")
        code, out = run(self.work, "round", "new")
        self.assertEqual(code, 1)
        self.assertIn("orçamento", out)

    def test_round_cannot_open_with_pending_substage(self):
        self.init()
        c = ac.Campaign(self.work)
        st = c.load()
        st["round"] = 1
        c.save(st, "test")
        code, out = run(self.work, "round", "new")
        self.assertEqual(code, 1)
        self.assertIn("não terminou", out)


class LockBypassTest(Base):
    """Defeitos achados ao documentar a v0.1: travas que o `set` e a ordem das etapas furavam."""

    def test_set_cannot_forge_gate_done_round_or_oracle(self):
        self.init()
        for key, val in (("gates.stop", '{"decision":"approve"}'), ("done", '{"intake.3":"x"}'),
                         ("round", "5"), ("oracle", '{"hash":"x"}'), ("waivers.0.baseline", '"x"')):
            self.assertEqual(run(self.work, "set", key, val)[0], 2, key)
        self.assertEqual(run(self.work, "check", "intake.3")[0], 1)

    def test_check_and_done_respect_stage_order(self):
        self.init()
        code, out = run(self.work, "check", "oraculo.1")
        self.assertEqual(code, 1)
        self.assertIn("intake", out)
        self.assertEqual(run(self.work, "done", "oraculo")[0], 1)

    def test_round_zero_needs_base_closed(self):
        self.init()
        code, out = run(self.work, "round", "new")
        self.assertEqual(code, 1)
        self.assertIn("intake", out)

    def test_latest_run_record_wins(self):
        self.init()
        c = ac.Campaign(self.work)
        run(self.work, "run", "record", "--config", "sistema", "--alvo", "py")
        self.assertRaises(ac.Fail, ac.chk_runs, c, c.load(), ["--graded"])
        g = os.path.join(self.tmp, "g.json")
        with open(g, "w", encoding="utf-8") as fh:
            json.dump({"summary": {"quality": {"passed": 1, "total": 1}}}, fh)
        run(self.work, "run", "record", "--config", "sistema", "--alvo", "py", "--grading", g)
        ac.chk_runs(c, c.load(), ["--graded"])

    def test_waive_needs_reason_and_missing_file_is_exit_2(self):
        self.init()
        self.assertEqual(run(self.work, "run", "waive", "--config", "baseline")[0], 2)
        self.assertEqual(run(self.work, "front", "report", "x", "--file", "/nao/existe")[0], 2)

    @precisa_pty
    def test_change_requires_prior_freeze_and_round_resets_gates(self):
        self.init()
        self.assertEqual(run(self.work, "oracle", "change", "--why", "a", "--evidence", "b")[0], 2)
        self.assertEqual(self.human("gate", "commit", "--by", "founder", "--decision", "approve")[0], 0)
        self.assertEqual(self.human("gate", "stop", "--by", "founder", "--decision", "approve")[0], 0)
        c = ac.Campaign(self.work)
        st = c.load()
        for name in ac.ciclo()["order"]:
            for sub in ac.ciclo()["stages"][name]["substages"]:
                st["done"][sub["id"]] = "x"
        c.save(st, "test")
        self.assertEqual(run(self.work, "round", "new")[0], 0)
        gates = c.load()["gates"]
        self.assertIn("stop", gates)
        self.assertNotIn("commit", gates)


if __name__ == "__main__":
    unittest.main()
