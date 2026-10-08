"""Oráculo de aceite da campanha win-motor — o motor da auto-correcao compatível com Windows.

Escrito por um agente SEPARADO de quem corrige (quem testa não constrói). Cada teste de W1–W7 FALHA hoje pelo
motivo do defeito e passa quando a correção estiver feita. Contrato de nomes e o que cada teste prova: ESPEC.md.
unittest puro, stdlib, Python 3.9+. O MESMO arquivo roda no Windows nativo e no Linux/WSL: o ramo do "outro" SO é
exercitado por mocks (`unittest.mock.patch.object` em `frase._windows`, `msvcrt` falso em `sys.modules`).

Isolamento: HOME, USERPROFILE, AC_FRASE_FILE e AC_AUDIT_LOG apontam para um temporário por teste (dentro de
`tempfile.mkdtemp()`, apagado no fim). O `~/.claude/auto-correcao/` real nunca é lido nem escrito. Nenhum teste roda
`gate`, `preauth` nem `frase` do ac.py.

`ORACULO_SKILL` / `ORACULO_SCRIPTS` (env do processo de teste) trocam a skill testada (o portão aponta para uma
cópia limpa); sem elas, a skill é a raiz deste projeto (três pastas acima deste arquivo).
"""
import contextlib
import glob
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.environ.get("ORACULO_SKILL") or os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SCRIPTS = os.environ.get("ORACULO_SCRIPTS") or os.path.join(SKILL, "scripts")
AC = os.path.join(SCRIPTS, "ac.py")
FRASE_PY = os.path.join(SCRIPTS, "frase.py")
HOOK = os.path.join(SCRIPTS, "hook_aprovacao.py")
TESTS_DIR = os.path.join(SCRIPTS, "tests")
SKILL_MD = os.path.join(SKILL, "SKILL.md")
GITATTRIBUTES = os.path.join(SKILL, ".gitattributes")

FAKE_FD = 987654  # fd simulado do /dev/tty (nunca é um fd real)


def carregar(caminho, nome):
    spec = importlib.util.spec_from_file_location(nome, caminho)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def sha_bytes_legado(paths):
    """Fórmula do hash do oráculo ANTES da correção (bytes crus), para simular campanha já congelada."""
    h = hashlib.sha256()
    for p in sorted(paths):
        h.update(p.encode())
        with open(p, "rb") as fh:
            h.update(hashlib.sha256(fh.read()).digest())
    return h.hexdigest()


class FakeStdin:
    """stdin simulado: só isatty/fileno são permitidos; qualquer leitura é registrada e reprovada."""

    def __init__(self, tty):
        self._tty = tty
        self.leituras = []

    def isatty(self):
        return self._tty

    def fileno(self):
        return 0

    def _leu(self, *a, **k):
        self.leituras.append("read")
        raise AssertionError("o ramo Windows leu sys.stdin (proibido)")

    read = readline = readlines = _leu

    @property
    def buffer(self):
        self.leituras.append("buffer")
        raise AssertionError("o ramo Windows leu sys.stdin.buffer (proibido)")

    def __iter__(self):
        self._leu()


class FakeMsvcrt:
    """`msvcrt` falso: getwch devolve as teclas da fila; putwch grava a saída do console."""

    def __init__(self, teclas):
        self.fila = list(teclas)
        self.saida = []
        self.proibidos = []

    def getwch(self):
        if not self.fila:
            raise AssertionError("getwch chamado depois do fim da entrada simulada (Enter não encerrou?)")
        return self.fila.pop(0)

    def putwch(self, ch):
        self.saida.append(ch)

    def _proibido(self, nome):
        def f(*a, **k):
            self.proibidos.append(nome)
            raise AssertionError("msvcrt.%s usado; o contrato é getwch/putwch" % nome)
        return f

    def __getattr__(self, nome):
        if nome in ("getch", "putch", "getche", "getwche", "kbhit", "ungetch", "ungetwch"):
            return self._proibido(nome)
        raise AttributeError(nome)

    def texto(self):
        return "".join(self.saida)


@contextlib.contextmanager
def sem_ttyname():
    """Simula plataforma sem os.ttyname (Windows): remove o atributo do módulo os durante o bloco."""
    orig = os.__dict__.get("ttyname")
    if orig is not None:
        del os.ttyname
    try:
        yield
    finally:
        if orig is not None:
            os.ttyname = orig


def spy_os_open(registro, dev_tty_fd=None):
    """os.open que registra os caminhos; `/dev/tty` devolve um fd falso (ou OSError se dev_tty_fd=None)."""
    real = os.open

    def f(path, flags, *a, **k):
        registro.append(path)
        if path == "/dev/tty":
            if dev_tty_fd is None:
                raise OSError("sem /dev/tty (simulado)")
            return dev_tty_fd
        return real(path, flags, *a, **k)
    return f


def spy_os_close():
    real = os.close

    def f(fd):
        if fd == FAKE_FD:
            return None
        return real(fd)
    return f


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp(prefix="ac-oraculo-win-motor-"))
        self.home = os.path.join(self.tmp, "home")
        os.makedirs(self.home)
        self.iso = {"HOME": self.home, "USERPROFILE": self.home,
                    "AC_FRASE_FILE": os.path.join(self.tmp, "frase.json"),
                    "AC_AUDIT_LOG": os.path.join(self.tmp, "audit.jsonl")}
        p = mock.patch.dict(os.environ, self.iso)
        p.start()
        self.addCleanup(p.stop)
        self.addCleanup(shutil.rmtree, self.tmp, True)

    # ---- subprocesso do ac.py, isolado
    def env(self, encoding="utf-8"):
        e = dict(os.environ)
        e.pop("PYTHONUTF8", None)
        e.update(self.iso)
        e["PYTHONIOENCODING"] = encoding
        return e

    def ac(self, work, *args, encoding="utf-8"):
        return subprocess.run([sys.executable, AC, "--work", work] + list(args), stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=self.tmp,
                              env=self.env(encoding), timeout=120)

    def nova_campanha(self, nome="camp"):
        work = os.path.join(self.tmp, nome)
        alvo = os.path.join(self.tmp, "alvo-" + nome)
        os.makedirs(alvo)
        r = self.ac(work, "init", "--target", alvo, "--scope", "x/**", "--problem", "p", "--stop", "q >= 1")
        self.assertEqual(r.returncode, 0, "init falhou (pré-condição do teste): %r" % (r.stderr,))
        return work

    def state_path(self, work):
        return os.path.join(work, ".auto-correcao", "state.json")

    def ler_state(self, work):
        with open(self.state_path(work), encoding="utf-8") as fh:
            return json.load(fh)

    def gravar_state(self, work, st):
        with open(self.state_path(work), "w", encoding="utf-8") as fh:
            json.dump(st, fh, ensure_ascii=False, indent=1, sort_keys=True)

    def fechar_intake(self, work):
        """Fixture: marca intake.1-3 como concluídas direto no state.json (sem gate; o teste não aprova nada)."""
        st = self.ler_state(work)
        for sid in ("intake.1", "intake.2", "intake.3"):
            st["done"][sid] = "2026-10-07T00:00:00Z"
        self.gravar_state(work, st)

    # ---- frase.py em processo
    def frase(self):
        return carregar(FRASE_PY, "win_motor_frase")

    def exige_w1(self, m, *nomes):
        faltam = [n for n in nomes if not callable(getattr(m, n, None))]
        if faltam:
            self.fail("W1: frase.%s ausente — o ramo Windows de frase.py não existe" % ", frase.".join(faltam))


# ====================================================================== W1 — senha no console do Windows

class W1ConsoleWindowsTest(Base):
    def _ambiente(self, m, stack, stdin_tty=True, console_ok=True, teclas=None):
        """_windows()=True, console simulado, msvcrt falso, stdin falso, os.open espionado, stdout/stderr capturados."""
        self.exige_w1(m, "_windows", "_abrir_console")
        stack.enter_context(mock.patch.object(m, "_windows", return_value=True))
        stack.enter_context(mock.patch.object(
            m, "_abrir_console", side_effect=None if console_ok else OSError("sem console (simulado)")))
        fake = FakeMsvcrt(teclas or [])
        stack.enter_context(mock.patch.dict(sys.modules, {"msvcrt": fake}))
        stdin = FakeStdin(stdin_tty)
        stack.enter_context(mock.patch.object(sys, "stdin", stdin))
        abertos = []
        stack.enter_context(mock.patch.object(os, "open", side_effect=spy_os_open(abertos, None)))
        out, err = io.StringIO(), io.StringIO()
        stack.enter_context(mock.patch.object(sys, "stdout", out))
        stack.enter_context(mock.patch.object(sys, "stderr", err))
        return fake, stdin, abertos, out, err

    def test_windows_consulta_os_name_na_chamada(self):
        m = self.frase()
        self.exige_w1(m, "_windows")
        with mock.patch.object(os, "name", "nt"):
            nt = m._windows()
        with mock.patch.object(os, "name", "posix"):
            px = m._windows()
        self.assertIs(nt, True)
        self.assertIs(px, False)

    def test_abrir_console_sem_console_levanta_oserror(self):
        m = self.frase()
        self.exige_w1(m, "_abrir_console")
        if os.name == "nt":
            # processo sem console (DETACHED_PROCESS): CONIN$ não abre
            code = ("import importlib.util,sys\n"
                    "s=importlib.util.spec_from_file_location('f',sys.argv[1]);m=importlib.util.module_from_spec(s)\n"
                    "s.loader.exec_module(m)\n"
                    "try:\n m._abrir_console()\nexcept OSError:\n print('OSERROR');sys.exit(0)\n"
                    "print('ABRIU');sys.exit(3)\n")
            r = subprocess.run([sys.executable, "-c", code, FRASE_PY], stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=self.env(), cwd=self.tmp,
                               timeout=60, creationflags=subprocess.DETACHED_PROCESS)
            self.assertEqual(r.returncode, 0, "sem console, _abrir_console() deveria levantar OSError: %r %r"
                             % (r.stdout, r.stderr))
        else:
            cwd = os.getcwd()
            os.chdir(self.tmp)  # nenhum arquivo "CONIN$" aqui
            try:
                with self.assertRaises(OSError):
                    m._abrir_console()
            finally:
                os.chdir(cwd)

    def test_exigir_tty_windows_stdin_nao_tty_cita_winpty_e_powershell(self):
        m = self.frase()
        with contextlib.ExitStack() as s:
            _, _, abertos, _, _ = self._ambiente(m, s, stdin_tty=False)
            with self.assertRaises(m.SemTTY) as cm:
                m.exigir_tty()
        msg = str(cm.exception)
        self.assertIn("winpty", msg)
        self.assertIn("PowerShell", msg)
        self.assertNotIn("/dev/tty", abertos, "o ramo Windows abriu /dev/tty")

    def test_exigir_tty_windows_console_ok_devolve_conin(self):
        m = self.frase()
        with contextlib.ExitStack() as s:
            _, _, abertos, _, _ = self._ambiente(m, s)
            r = m.exigir_tty()
            chamou_console = m._abrir_console.called
        self.assertEqual(r, "CONIN$")
        self.assertTrue(chamou_console, "exigir_tty() no Windows não conferiu o console (_abrir_console)")
        self.assertNotIn("/dev/tty", abertos, "o ramo Windows abriu /dev/tty")

    def test_exigir_tty_windows_console_falha_semtty(self):
        m = self.frase()
        with contextlib.ExitStack() as s:
            _, _, abertos, _, _ = self._ambiente(m, s, console_ok=False)
            with self.assertRaises(m.SemTTY):
                m.exigir_tty()
        self.assertNotIn("/dev/tty", abertos, "o ramo Windows abriu /dev/tty")

    def _ler(self, teclas, prompt="FRASE: ", contexto=None):
        m = self.frase()
        with contextlib.ExitStack() as s:
            fake, stdin, abertos, out, err = self._ambiente(m, s, teclas=teclas)
            r = m.ler(prompt, contexto)
        self.assertEqual(stdin.leituras, [], "ler() leu sys.stdin")
        self.assertNotIn("/dev/tty", abertos, "o ramo Windows abriu /dev/tty")
        self.assertEqual(fake.proibidos, [])
        self.assertEqual(out.getvalue() + err.getvalue(), "", "ler() escreveu fora de msvcrt.putwch")
        return r, fake

    def test_ler_windows_le_sem_eco_e_escreve_contexto_e_prompt(self):
        senha = "Zebra#7 voo"
        contexto = "Contexto da aprovacao"
        r, fake = self._ler(list(senha) + ["\r"], prompt="FRASE do founder: ", contexto=contexto)
        self.assertEqual(r, senha)
        saida = fake.texto()
        self.assertIn(contexto, saida)
        i = saida.find("FRASE do founder: ")
        self.assertGreaterEqual(i, 0, "prompt não passou por putwch: %r" % saida)
        self.assertLess(saida.find(contexto), i, "contexto deve vir antes do prompt")
        cauda = saida[i + len("FRASE do founder: "):]
        self.assertTrue(set(cauda) <= set("\r\n"), "ecoou algo depois do prompt: %r" % cauda)
        self.assertNotIn(senha, saida)

    def test_ler_windows_enter_lf_tambem_encerra(self):
        r, _ = self._ler(["a", "b", "\n"])
        self.assertEqual(r, "ab")

    def test_ler_windows_enter_imediato_devolve_vazio(self):
        r, _ = self._ler(["\r"])
        self.assertEqual(r, "")

    def test_ler_windows_backspace_apaga_ultimo(self):
        r, _ = self._ler(["a", "b", "c", "\b", "d", "\r"])
        self.assertEqual(r, "abd")
        r, _ = self._ler(["\b", "\b", "x", "\r"])
        self.assertEqual(r, "x")

    def test_ler_windows_ctrl_c_keyboardinterrupt(self):
        m = self.frase()
        with contextlib.ExitStack() as s:
            self._ambiente(m, s, teclas=["a", "b", "\x03", "c", "\r"])
            with self.assertRaises(KeyboardInterrupt):
                m.ler("FRASE: ")

    def test_ler_windows_teclas_especiais_descartadas(self):
        r, _ = self._ler(["a", "\x00", ";", "b", "\xe0", "H", "c", "\r"])
        self.assertEqual(r, "abc")

    def test_ler_windows_limite_4096(self):
        r, _ = self._ler(["x"] * 5000 + ["\r"])
        self.assertEqual(r, "x" * 4096)

    def test_ler_windows_sem_console_semtty(self):
        m = self.frase()
        with contextlib.ExitStack() as s:
            fake, _, _, _, _ = self._ambiente(m, s, console_ok=False, teclas=list("Zebra#7 voo") + ["\r"])
            with self.assertRaises(m.SemTTY):
                m.ler("FRASE: ")
        self.assertEqual(fake.saida, [], "sem console, nada deveria ser escrito")
        self.assertEqual(len(fake.fila), 12, "sem console, nenhuma tecla deveria ser lida")

    def test_posix_inalterado_sem_dev_tty_semtty_e_nao_usa_msvcrt(self):
        """Guarda de regressão (passa hoje): no ramo posix, sem /dev/tty → SemTTY, e msvcrt nunca é usado."""
        m = self.frase()
        fake = FakeMsvcrt(["a", "\r"])
        abertos = []
        with contextlib.ExitStack() as s:
            if hasattr(m, "_windows"):
                s.enter_context(mock.patch.object(m, "_windows", return_value=False))
            s.enter_context(mock.patch.dict(sys.modules, {"msvcrt": fake}))
            s.enter_context(mock.patch.object(sys, "stdin", FakeStdin(True)))
            s.enter_context(mock.patch.object(os, "open", side_effect=spy_os_open(abertos, None)))
            with self.assertRaises(m.SemTTY):
                m.ler("FRASE: ")
        self.assertIn("/dev/tty", abertos)
        self.assertEqual(fake.saida, [])
        self.assertEqual(fake.fila, ["a", "\r"])


# ====================================================================== W2 — saída em cp1252

class W2SaidaCp1252Test(Base):
    def _sem_traceback(self, r):
        self.assertNotIn(b"Traceback", r.stderr, r.stderr.decode("cp1252", "replace"))
        self.assertNotIn(b"UnicodeEncodeError", r.stderr)

    def test_load_oraculo_em_cp1252(self):
        work = self.nova_campanha()
        self.fechar_intake(work)
        r = self.ac(work, "load", "oraculo", encoding="cp1252")
        self._sem_traceback(r)
        self.assertEqual(r.returncode, 0, r.stderr.decode("cp1252", "replace"))
        self.assertIn("# etapa oraculo", r.stdout.decode("cp1252", "replace"))
        self.assertIn("oraculo.2", r.stdout.decode("cp1252", "replace"))

    def test_status_em_cp1252(self):
        work = self.nova_campanha()
        self.fechar_intake(work)  # etapa completa imprime a marca de concluída
        r = self.ac(work, "status", encoding="cp1252")
        self._sem_traceback(r)
        self.assertEqual(r.returncode, 0, r.stderr.decode("cp1252", "replace"))
        txt = r.stdout.decode("cp1252", "replace")
        self.assertIn("intake", txt)
        self.assertIn("3/3", txt)

    def test_results_compare_em_cp1252(self):
        work = self.nova_campanha()
        st = self.ler_state(work)
        st["round"] = 1
        self.gravar_state(work, st)
        for rodada, passou in ((0, 1), (1, 2)):
            d = os.path.join(work, ".auto-correcao", "rounds", str(rodada))
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, "runs.jsonl"), "w", encoding="utf-8") as fh:
                fh.write(json.dumps({"round": rodada, "config": "sistema", "alvo": "default", "simulated": False,
                                     "quality": {"passed": passou, "total": 2}, "at": "2026-10-07T00:00:0%dZ" % rodada})
                         + "\n")
        r = self.ac(work, "results", "compare", encoding="cp1252")
        self._sem_traceback(r)
        self.assertEqual(r.returncode, 0, r.stderr.decode("cp1252", "replace"))
        self.assertIn("quality: rodada 1 = 1.00", r.stdout.decode("cp1252", "replace"))

    def test_verify_reprovado_em_cp1252_sai_1_sem_traceback(self):
        """Guarda de regressão (passa hoje): a recusa do `oracle verify` (stderr, traz '≠') em cp1252 sai 1 sem traceback."""
        work = self.nova_campanha()
        arq = os.path.join(self.tmp, "o.py")
        with open(arq, "wb") as fh:
            fh.write(b"a = 1\n")
        self.assertEqual(self.ac(work, "oracle", "freeze", "--file", arq).returncode, 0)
        with open(arq, "wb") as fh:
            fh.write(b"a = 2\n")
        r = self.ac(work, "oracle", "verify", encoding="cp1252")
        self._sem_traceback(r)
        self.assertEqual(r.returncode, 1, r.stderr.decode("cp1252", "replace"))


# ====================================================================== W3 — CRLF

class W3CrlfTest(Base):
    def _arquivo(self, conteudo):
        arq = os.path.join(self.tmp, "oraculo_x.py")
        with open(arq, "wb") as fh:
            fh.write(conteudo)
        return arq

    def _reescrever(self, arq, conteudo):
        with open(arq, "wb") as fh:
            fh.write(conteudo)

    LF = b"import unittest\n\nclass T(unittest.TestCase):\n    def test_a(self):\n        self.assertTrue(1)\n"

    def test_freeze_lf_verify_crlf_passa(self):
        work = self.nova_campanha()
        arq = self._arquivo(self.LF)
        self.assertEqual(self.ac(work, "oracle", "freeze", "--file", arq).returncode, 0)
        self._reescrever(arq, self.LF.replace(b"\n", b"\r\n"))
        r = self.ac(work, "oracle", "verify")
        self.assertEqual(r.returncode, 0, "o mesmo conteúdo com CRLF reprovou o oráculo: %s"
                         % r.stderr.decode("utf-8", "replace"))

    def test_freeze_crlf_verify_lf_passa(self):
        work = self.nova_campanha()
        arq = self._arquivo(self.LF.replace(b"\n", b"\r\n"))
        self.assertEqual(self.ac(work, "oracle", "freeze", "--file", arq).returncode, 0)
        self._reescrever(arq, self.LF)
        r = self.ac(work, "oracle", "verify")
        self.assertEqual(r.returncode, 0, "o mesmo conteúdo com LF reprovou o oráculo congelado em CRLF: %s"
                         % r.stderr.decode("utf-8", "replace"))

    def test_campanha_ja_congelada_em_lf_verifica_checkout_crlf(self):
        """Cenário real: oráculo congelado no macOS (hash por bytes LF), re-checkout no Windows com CRLF."""
        work = self.nova_campanha()
        arq = os.path.realpath(self._arquivo(self.LF))
        st = self.ler_state(work)
        st["oracle"] = {"files": [arq], "hash": sha_bytes_legado([arq]), "frozen_at": "2026-10-01T00:00:00Z"}
        self.gravar_state(work, st)
        self._reescrever(arq, self.LF.replace(b"\n", b"\r\n"))
        r = self.ac(work, "oracle", "verify")
        self.assertEqual(r.returncode, 0, "campanha congelada em LF reprovou no checkout CRLF: %s"
                         % r.stderr.decode("utf-8", "replace"))

    def test_campanha_ja_congelada_em_lf_continua_verificando_lf(self):
        """Guarda de regressão (passa hoje): campanha congelada antes da correção segue intacta com o mesmo LF."""
        work = self.nova_campanha()
        arq = os.path.realpath(self._arquivo(self.LF))
        st = self.ler_state(work)
        st["oracle"] = {"files": [arq], "hash": sha_bytes_legado([arq]), "frozen_at": "2026-10-01T00:00:00Z"}
        self.gravar_state(work, st)
        r = self.ac(work, "oracle", "verify")
        self.assertEqual(r.returncode, 0, r.stderr.decode("utf-8", "replace"))

    def test_mudanca_real_continua_reprovando(self):
        """Guarda de regressão (passa hoje): conteúdo diferente reprova, com ou sem CRLF."""
        work = self.nova_campanha()
        arq = self._arquivo(self.LF)
        self.assertEqual(self.ac(work, "oracle", "freeze", "--file", arq).returncode, 0)
        for novo in (self.LF.replace(b"assertTrue(1)", b"assertTrue(0)"),
                     self.LF.replace(b"assertTrue(1)", b"assertTrue(0)").replace(b"\n", b"\r\n"),
                     self.LF + b"\n"):
            with self.subTest(novo=novo[-30:]):
                self._reescrever(arq, novo)
                r = self.ac(work, "oracle", "verify")
                self.assertEqual(r.returncode, 1, "mudança real de conteúdo passou no verify")

    def test_gitattributes_fixa_eol_lf(self):
        self.assertTrue(os.path.isfile(GITATTRIBUTES), "falta %s" % GITATTRIBUTES)
        with open(GITATTRIBUTES, encoding="utf-8") as fh:
            linhas = [l.split() for l in fh.read().splitlines() if l.strip() and not l.lstrip().startswith("#")]
        efetivo = {}
        for padrao in ("*.py", "*.sh", "*.json5", "*.md", "*.json"):
            eol = None
            for toks in linhas:  # a última linha que casa vence (semântica do git)
                if toks[0] in (padrao, "*"):
                    for t in toks[1:]:
                        if t.startswith("eol="):
                            eol = t[4:]
                        elif t in ("-text", "binary"):
                            eol = None
            efetivo[padrao] = eol
        self.assertEqual(efetivo, {p: "lf" for p in efetivo}, ".gitattributes não fixa eol=lf: %r" % efetivo)


# ====================================================================== W4 — os.ttyname ausente

class W4TtynameAusenteTest(Base):
    def test_exigir_tty_posix_sem_ttyname_devolve_dev_tty(self):
        m = self.frase()
        abertos = []
        with contextlib.ExitStack() as s:
            if hasattr(m, "_windows"):
                s.enter_context(mock.patch.object(m, "_windows", return_value=False))
            s.enter_context(mock.patch.object(sys, "stdin", FakeStdin(True)))
            s.enter_context(mock.patch.object(os, "open", side_effect=spy_os_open(abertos, FAKE_FD)))
            s.enter_context(mock.patch.object(os, "close", side_effect=spy_os_close()))
            s.enter_context(sem_ttyname())
            try:
                r = m.exigir_tty()
            except AttributeError as e:
                self.fail("W4: exigir_tty() quebrou sem os.ttyname: %r" % (e,))
        self.assertEqual(r, "/dev/tty")
        self.assertIn("/dev/tty", abertos, "o ramo posix deve continuar exigindo /dev/tty")


# ====================================================================== W5 — instrução python3 fixa

class W5SkillMdWindowsTest(unittest.TestCase):
    def test_skill_md_documenta_invocacao_no_windows(self):
        with open(SKILL_MD, encoding="utf-8") as fh:
            linhas = fh.read().splitlines()
        idx = [i for i, l in enumerate(linhas) if "Windows" in l]
        self.assertTrue(idx, "SKILL.md não cita Windows")
        invoc = re.compile(r"(?<![\w.-])(python(\.exe)?|py(\.exe)?\s+-3)\s[^\n]*?ac\.py\b")
        perto = [linhas[j] for i in idx for j in range(max(0, i - 2), min(len(linhas), i + 15))
                 if invoc.search(linhas[j])]
        self.assertTrue(perto, "SKILL.md cita Windows mas não mostra `python .../ac.py` (ou `py -3 .../ac.py`) "
                               "junto (até 15 linhas depois)")


# ====================================================================== W6 — suíte importa sem pty/termios

IMPORT_SEM_PTY = r"""
import importlib.util, os, sys, unittest
sys.modules["pty"] = None
sys.modules["termios"] = None
tests, nome = sys.argv[1], sys.argv[2]
sys.path.insert(0, tests)
spec = importlib.util.spec_from_file_location(nome, os.path.join(tests, nome + ".py"))
m = importlib.util.module_from_spec(spec)
sys.modules[nome] = m
spec.loader.exec_module(m)
n = unittest.defaultTestLoader.loadTestsFromModule(m).countTestCases()
print("IMPORT-OK %s %d" % (nome, n))
"""


class W6SuiteImportaSemPtyTest(Base):
    def test_cada_modulo_de_teste_importa_sem_pty_e_termios(self):
        mods = sorted(os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(TESTS_DIR, "test_*.py")))
        self.assertTrue(mods, "nenhum scripts/tests/test_*.py em %s" % TESTS_DIR)
        for nome in mods:
            with self.subTest(modulo=nome):
                r = subprocess.run([sys.executable, "-c", IMPORT_SEM_PTY, TESTS_DIR, nome], stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=self.tmp, env=self.env(),
                                   timeout=120)
                ultima = (r.stderr.decode("utf-8", "replace").strip().splitlines() or [""])[-1]
                self.assertEqual(r.returncode, 0, "%s não importa sem pty/termios: %s" % (nome, ultima))
                self.assertIn(b"IMPORT-OK", r.stdout)


# ====================================================================== W7 — caminhos com "\"

class W7BarraInvertidaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ac = carregar(AC, "win_motor_ac")

    def test_barra_invertida_tratada_como_barra(self):
        casos = [("scripts\\ac.py", "scripts/ac.py"),
                 ("scripts/*.py", "scripts\\ac.py"),
                 ("scripts\\tests", "scripts/tests/*.py"),
                 ("scripts\\tests\\", "scripts/tests/test_ac.py"),
                 ("scripts\\tests", "scripts\\tests\\x.py"),
                 ("scripts\\tests\\**", "scripts/tests/sub/a.py")]
        for a, b in casos:
            for x, y in ((a, b), (b, a)):
                with self.subTest(a=x, b=y):
                    self.assertTrue(self.ac.globs_overlap(x, y), "%r e %r deveriam sobrepor" % (x, y))

    def test_disjuntos_continuam_disjuntos(self):
        """Guarda de regressão (passa hoje): normalizar `\\` não pode virar 'tudo sobrepõe'."""
        casos = [("scripts\\ac.py", "docs/x.md"),
                 ("scripts\\tests", "scripts/testsX/a.py"),
                 ("scripts\\tests\\*.py", "references/ciclo.json5"),
                 ("docs\\a.md", "docs/b.md")]
        for a, b in casos:
            for x, y in ((a, b), (b, a)):
                with self.subTest(a=x, b=y):
                    self.assertFalse(self.ac.globs_overlap(x, y), "%r e %r não deveriam sobrepor" % (x, y))


# ====================================================================== guarda: selftest do hook

class HookSelftestTest(Base):
    def test_hook_selftest_exit_0(self):
        """Guarda de regressão (passa hoje): o selftest embutido do hook de aprovação continua verde."""
        r = subprocess.run([sys.executable, HOOK, "--selftest"], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, cwd=self.tmp, env=self.env(), timeout=120)
        self.assertEqual(r.returncode, 0, (r.stdout + r.stderr).decode("utf-8", "replace")[-2000:])


if __name__ == "__main__":
    unittest.main()
