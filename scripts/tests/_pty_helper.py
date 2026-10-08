"""Roda ac.py num pseudo-terminal real (pty.fork) e digita a FRASE do founder de teste — o caminho do humano (v0.4).

Sem variável de bypass: o filho recebe um pty como stdin/stdout/tty controlador; a cada prompt `FRASE...:` (eco já
desligado pelo ac.py) o helper digita a próxima resposta de `answers` (esgotou → linha vazia). A frase de teste só
vale porque o teste grava, num AC_FRASE_FILE temporário, um frase.json gerado com ela (`frase_json_teste`).

Sem `pty`/`termios`/`os.fork`/`SIGKILL` (Windows), o módulo importa igual: `TEM_PTY` fica False e os testes que
passam por `run_tty` levam `@precisa_pty` (pulados com o motivo). No macOS/Linux tudo roda como antes.
"""
import datetime
import hashlib
import json
import os
import re
import select
import signal
import sys
import time
import unicodedata
import unittest

try:
    import pty
    import termios  # noqa: F401  (o ac.py desliga o eco por termios; sem ele não há caminho do humano a testar)
except ImportError:  # Windows: não existem
    pty = None

TEM_PTY = pty is not None and hasattr(os, "fork") and hasattr(os, "WEXITSTATUS") and hasattr(signal, "SIGKILL")
MOTIVO_SEM_PTY = "precisa de pty/termios/os.fork/SIGKILL (terminal posix), ausentes neste Python"
precisa_pty = unittest.skipUnless(TEM_PTY, MOTIVO_SEM_PTY)

AC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ac.py")
PROMPT = re.compile(rb"FRASE[^\r\n:]*:")
FRASE_TESTE = "lagoa serena de inverno"
ITER = 600000
_FJ = {}


def _derivar(f, salt_hex, it):
    nb = unicodedata.normalize("NFC", f.strip()).encode("utf-8")
    return hashlib.pbkdf2_hmac("sha256", nb, bytes.fromhex(salt_hex), it, dklen=32)


def frase_json_teste(path, frase=FRASE_TESTE):
    """Grava (0600) um frase.json no formato v0.4 para `frase`; derivado uma vez por processo (custa ~0,2 s)."""
    if frase not in _FJ:
        sv, sk = os.urandom(16).hex(), os.urandom(16).hex()
        _FJ[frase] = {"versao": 1, "kdf": "pbkdf2-sha256", "iter": ITER, "salt_verificador": sv, "salt_chave": sk,
                      "verificador": _derivar(frase, sv, ITER).hex(),
                      "criada_em": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(_FJ[frase], fh)
    os.chmod(path, 0o600)
    return path


def run_tty(work, *argv, env=None, answers=(FRASE_TESTE,), timeout=60, ac=AC):
    """Retorna (exit, saída, nº de prompts FRASE vistos). answers: respostas digitadas, uma por prompt."""
    env = dict(os.environ if env is None else env)
    pid, fd = pty.fork()
    if pid == 0:
        try:
            os.execve(sys.executable, [sys.executable, ac, "--work", work] + list(argv), env)
        finally:
            os._exit(127)
    answers = list(answers)
    buf, seen, deadline = b"", 0, time.time() + timeout
    try:
        while True:
            if time.time() > deadline:
                os.kill(pid, signal.SIGKILL)
                raise AssertionError("ac.py no tty não terminou em %ss; saída: %r" % (timeout, buf[-500:]))
            r, _, _ = select.select([fd], [], [], 0.1)
            if not r:
                continue
            try:
                data = os.read(fd, 4096)
            except OSError:
                break
            if not data:
                break
            buf += data
            n = len(PROMPT.findall(buf))
            while seen < n:
                os.write(fd, ((answers[seen] if seen < len(answers) else "") + "\n").encode())
                seen += 1
    finally:
        _, status = os.waitpid(pid, 0)
        os.close(fd)
    code = os.WEXITSTATUS(status) if os.WIFEXITED(status) else 128 + os.WTERMSIG(status)
    return code, buf.decode("utf-8", "replace"), seen
