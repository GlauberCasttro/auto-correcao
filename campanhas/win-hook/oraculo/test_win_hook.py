"""Oráculo de aceite da campanha win-hook — o hook de aprovação (`scripts/hook_aprovacao.py`) enxergando o Windows.

Escrito por um agente SEPARADO de quem corrige (quem testa não constrói). Cada teste de H1–H6 FALHA hoje pelo motivo
do defeito e passa quando a correção estiver feita; os testes `Guarda*` passam hoje e continuam passando (proteção
contra regressão). Contrato e o que cada teste prova: ESPEC.md.

Forma de verificar o veredito (uma só, a do contrato do hook):
  * `decide(payload)` do módulo testado, carregado por importlib a partir de ORACULO_SCRIPTS: devolve um motivo
    (str não vazia) quando NEGA e `None` quando PERMITE. É a função que o `main()` usa.
  * Ponta a ponta (só onde o `main()` importa: payload pela stdin, códigos de saída): `python hook_aprovacao.py`
    com o JSON na stdin; negação = exit 2 e `hook_aprovacao: NEGADO` no stderr; permissão = exit 0 sem saída.

Todos os comandos abaixo são STRINGS de payload: nada aqui executa `ac.py`, `co.py` nem `aprovar-*.sh`.

unittest puro, stdlib, Python 3.9+. O MESMO arquivo roda no Windows nativo e no Linux/WSL. `ORACULO_SKILL` /
`ORACULO_SCRIPTS` (env do processo de teste) trocam a skill testada (o portão aponta para uma cópia limpa); sem elas,
a skill é a raiz deste projeto (três pastas acima deste arquivo).
"""
import base64
import contextlib
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

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.environ.get("ORACULO_SKILL") or os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SCRIPTS = os.environ.get("ORACULO_SCRIPTS") or os.path.join(SKILL, "scripts")
HOOK = os.path.join(SCRIPTS, "hook_aprovacao.py")
SKILL_MD = os.path.join(SKILL, "SKILL.md")
README_MD = os.path.join(SKILL, "README.md")
REF_CLI_MD = os.path.join(SKILL, "docs", "04-referencia-cli.md")

NEGA = "NEGA"
PERMITE = "PERMITE"


def carregar_hook():
    spec = importlib.util.spec_from_file_location("hook_aprovacao_oraculo_win_hook", HOOK)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def payload(tool, cmd):
    return {"tool_name": tool, "tool_input": {"command": cmd}}


def rodar_hook(raw, *args):
    """Roda o hook como o Claude Code roda: payload na stdin. Devolve (exit, stdout, stderr)."""
    tmp = tempfile.mkdtemp(prefix="oraculo-win-hook-")
    try:
        env = dict(os.environ)
        env.pop("PYTHONUTF8", None)
        p = subprocess.run([sys.executable, HOOK] + list(args), input=raw.encode("utf-8"), stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, cwd=tmp, env=env, timeout=120)
        return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# --------------------------------------------------------------------------------------------------------------
# Guarda de regressão: SELF_DENY / SELF_ALLOW do hook_aprovacao.py ANTES da campanha (74 comandos), copiados
# literalmente (com `_A` expandido) em 2026-10-08. Mais o caso de ferramenta não-Bash e os 8 payloads brutos do
# selftest: 44 + 30 + 1 + 8 = 83 casos. NÃO editar: mudança só por mudança oficial do oráculo.
# --------------------------------------------------------------------------------------------------------------
FROZEN_DENY = [
    'python3 /Users/x/.claude/skills/auto-correcao/scripts/ac.py --work /tmp/c gate stop --by founder --decision approve',
    'python3 ~/.claude/skills/auto-correcao/scripts/ac.py --work /tmp/c preauth commit --by f',
    'cd /s && python3 ./ac.py --work /tmp/c gate stop --by f --decision approve',
    './ac.py --work /tmp/c gate stop',
    'PYTHONPATH=/s python3 -m ac --work /tmp/c gate stop',
    'python3 -mac --work /tmp/c gate stop',
    '"python3" "/Users/x/.claude/skills/auto-correcao/scripts/ac.py" --work /tmp/c "gate" stop',
    "python3 '/Users/x/.claude/skills/auto-correcao/scripts/ac.py' 'preauth' commit",
    "sh -c 'python3 /Users/x/.claude/skills/auto-correcao/scripts/ac.py --work /tmp/c gate stop'",
    'bash -lc "python3 ac.py preauth commit"',
    'true; python3 ac.py gate stop',
    'echo ok && python3 ac.py gate stop',
    'false || python3 ac.py gate stop',
    'yes | python3 ac.py gate stop',
    'ls\npython3 ac.py gate stop',
    'AC=/Users/x/.claude/skills/auto-correcao/scripts/ac.py; python3 "$AC" --work /tmp/c gate stop',
    'python3 $AC --work /tmp/c gate stop',
    'python3 ${AC} preauth commit',
    'python3 -c \'import runpy,sys; sys.argv=["ac.py","gate","stop"]; runpy.run_path("/Users/x/.claude/skills/auto-correcao/scripts/ac.py")\'',
    'python3 -c \'import ac; ac.main(["--work","/tmp/c","gate","stop"])\'',
    'python3 /x/scripts/co.py --work /tmp/o approve entrega',
    'python3 co.py approve plan:DEC-1',
    'sh -c "cd /x && python3 ./co.py --work . approve stop"',
    'env FOO=1 python3 ac.py gate stop',
    'timeout 10 python3 ac.py gate stop',
    'echo $(python3 ac.py gate stop)',
    'bash ~/bin/aprovar-sprint.sh 03',
    './aprovar-gate.sh',
    'source scripts/aprovar-x.sh',
    'echo stop | xargs python3 ac.py --work /tmp/c gate',
    'eval "python3 ac.py gate stop"',
    "python3 ac.py --work /tmp/c gate stop 'unterminated",
    "sed -n '1e python3 ac.py gate stop' x.txt",
    "sed -e 'e python3 ac.py --work /tmp/c preauth commit' /dev/null",
    'python3 ac.py --work=/tmp/c frase conferir',
    "printf 'python3 ac.py --work /tmp/c gate stop --by f --decision approve' | sh",
    "echo 'python3 ac.py --work /tmp/c frase definir' | bash",
    "bash -s <<'EOF'\npython3 ac.py --work /tmp/c gate stop\nEOF",
    "cat <<'EOF' | bash\npython3 ac.py --work /tmp/c preauth commit\nEOF",
    "python3 - <<'EOF'\nimport runpy, sys; sys.argv = ['ac.py', '--work', '/tmp/c', 'frase', 'conferir']\nEOF",
    'python3 /Users/x/.claude/skills/auto-correcao/scripts/ac.py --work /tmp/c frase definir',
    'python3 ac.py --work /tmp/c frase conferir',
    'echo x | python3 ac.py --work /tmp/c frase definir',
    'python3 $AC --work /tmp/c frase conferir',
]
FROZEN_ALLOW = [
    'ls -la',
    'git status',
    'echo gate',
    'python3 other.py gate stop',
    'cat docs/gate.md',
    'python3 /Users/x/.claude/skills/auto-correcao/scripts/ac.py --work /tmp/c status',
    'python3 /Users/x/.claude/skills/auto-correcao/scripts/ac.py --work /tmp/c check intake.3',
    'python3 ac.py --work /tmp/c done intake',
    'python3 ac.py --work /tmp/c load',
    'python3 ac.py --work /tmp/c run record --config sistema --alvo py',
    'python3 "$AC" --work /tmp/c status',
    'python3 co.py --work /tmp/o status',
    'cat /Users/x/.claude/skills/auto-correcao/scripts/ac.py | grep -n gate',
    "grep -n 'def cmd_gate\\|preauth' /Users/x/.claude/skills/auto-correcao/scripts/ac.py",
    "head -50 ac.py; sed -n '1,40p' co.py",
    'tail -f log.txt; less ac.py',
    'git diff -- ac.py  # gate preauth',
    "git commit -m 'ac.py: endurece gate e preauth'",
    'cat ~/bin/aprovar-sprint.sh',
    'echo $HOME',
    'grep -n frase /Users/x/.claude/skills/auto-correcao/scripts/ac.py',
    'cat ~/.claude/skills/auto-correcao/scripts/frase.py',
    'echo frase',
    'python3 other.py frase definir',
    'python3 /Users/x/.claude/skills/auto-correcao/scripts/ac.py --work /tmp/c front report frase --file /tmp/rel.md',
    'python3 ac.py --work /tmp/c front report gate --file /tmp/rel.md',
    "printf 'texto com frase e gate\\n' > /tmp/rel.md && python3 ac.py --work /tmp/c done correcao",
    "echo 'ac.py gate stop e frase conferir' > /tmp/nota.md && python3 ac.py --work /tmp/c status",
    "git commit -m 'ac.py: gate/preauth agora pedem a frase'",
    'python3 ac.py --work /tmp/c oracle change --why x --evidence y',
]
FROZEN_RAW = [("{nao json", 0), ("", 0), ("[1,2]", 0), ('{"tool_name": "Bash", "tool_input": 5}', 0),
              ("{nao json gate", 2), ("{quebrado PREAUTH", 2), ("[\"approve\"]", 2), ("lixo aprovar-x", 2)]

# --------------------------------------------------------------------------------------------------------------
# Casos novos (H1–H3). Strings Python cruas onde há `\` do Windows: o texto é exatamente o que o agente digitaria.
# --------------------------------------------------------------------------------------------------------------

# H1 — ferramenta PowerShell com sintaxe que o `check()` de hoje JÁ nega quando vem como Bash (barras `/`, código em
# -c, stdin com ac.py + gate no texto). Falham hoje só porque `decide()` ignora tool_name "PowerShell".
H1_PS_NEGA = [
    "python3 scripts/ac.py --work c gate stop --by f --decision approve",
    "python scripts/ac.py --work c preauth commit --by f",
    "python -m ac --work c frase conferir",
    "python ac.py --work=c frase conferir",
    "python scripts/co.py --work o approve entrega",
    "Write-Output ok; python ac.py --work c gate stop",
    "python.exe -c \"import ac; ac.main(['gate','stop'])\"",
    r"Start-Process -FilePath python -ArgumentList 'scripts\ac.py --work c gate stop' -Wait",
    "bash ./aprovar-x.sh",
]

# H2 — interpretadores e caminhos do Windows na ferramenta PowerShell: `\`, `.\`, drive `C:\`, aspas, `&`,
# `py -3`, `python.exe`, `pythonw.exe`, `Start-Process` com lista de argumentos.
H2_PS_NEGA = [
    r"python scripts\ac.py --work c gate stop --by f --decision approve",
    r"py -3 C:\x\scripts\ac.py --work c preauth commit --by f --requires a",
    r"& 'C:\Program Files\Python312\python.exe' scripts\ac.py --work c frase conferir",
    r'& "C:\Program Files\Python312\python.exe" "C:\x\scripts\ac.py" --work c gate stop',
    r"py.exe -3.12 'scripts\ac.py' --work c gate stop",
    r"pythonw.exe .\scripts\ac.py --work c preauth commit",
    r".\scripts\ac.py --work c gate stop",
    r"python C:\x\scripts\co.py --work o approve entrega",
    r"Start-Process -FilePath python.exe -ArgumentList 'scripts\ac.py','--work','c','gate','stop' -Wait",
]

# H2 — ferramenta Bash (Git Bash no Windows): interpretador do Windows lendo código pela stdin. Isola o defeito do
# INTERPRETER_RE (o heredoc com `python3 -` já é negado hoje; com `python.exe -`/`py -3 -` passa).
H2_BASH_STDIN_NEGA = [
    "python.exe - <<'EOF'\nimport ac\nac.main(['--work','c','gate','stop'])\nEOF",
    "py -3 - <<'EOF'\nimport runpy, sys; sys.argv = ['ac.py', '--work', 'c', 'preauth', 'commit']\nEOF",
    "py.exe -3.12 - <<'EOF'\nimport ac; ac.main(['frase', 'conferir'])\nEOF",
    "pythonw.exe - <<'EOF'\nimport ac; ac.main(['gate', 'stop'])\nEOF",
    "'/c/Program Files/Python312/python.exe' - <<'EOF'\nimport ac; ac.main(['gate', 'stop'])\nEOF",
    "'C:\\Program Files\\Python312\\python.exe' - <<'EOF'\nimport ac; ac.main(['gate', 'stop'])\nEOF",
    "printf 'import ac; ac.main([\"gate\",\"stop\"])' | python.exe -",
]

# H2 — ferramenta Bash, caminho do ac.py com `\` ENTRE ASPAS. O veredito não pode depender do SO em que o hook roda:
# hoje o Windows nega (ntpath.basename separa `\`) e o posix/WSL permite.
H2_BASH_PORTABILIDADE_NEGA = [
    r"python 'scripts\ac.py' --work c gate stop",
    r"py -3 'C:\x\scripts\ac.py' --work c preauth commit",
]

# H3 — script de aprovação com `\` ou `.\`.
H3_PS_NEGA = [
    r"sh 'campanhas\x\aprovar-x.sh'",
    r"bash .\aprovar-x.sh",
    r"& .\campanhas\x\aprovar-x.sh",
    r"& 'C:\camp\x\aprovar-x.sh' 03",
    r".\aprovar-x.sh",
]
H3_BASH_NEGA = [
    r"sh 'campanhas\x\aprovar-x.sh'",
    r"bash '.\aprovar-x.sh'",
    r"bash 'C:\camp\x\aprovar-x.sh' 03",
]

# H1+H2 com stdin — PowerShell entregando código a interpretador pela stdin (equivalente ao heredoc do bash).
STDIN_PS_NEGA = [
    "@'\nimport ac\nac.main([\"gate\",\"stop\"])\n'@ | python -",
    r"Get-Content .\ac.py | python - --work c gate stop",
    "@\"\nimport runpy, sys; sys.argv = ['ac.py', '--work', 'c', 'preauth', 'commit']\n\"@ | py -3 -",
    "\"import ac; ac.main(['frase','conferir'])\" | python.exe -",
    r"Get-Content scripts\ac.py | py -3 - --work c preauth commit",
]

# Permitidos (não pode virar falso positivo). Os 6 primeiros são os do contrato; os demais aplicam ao PowerShell a
# semântica que o hook já tem no Bash (subcomando não-aprovador, AC-13, leitores, stdin sem ac.py).
PS_PERMITE = [
    r"python scripts\ac.py --work c status",
    r"python scripts\ac.py --work c load oraculo",
    "git status",
    r"Get-Content scripts\ac.py",
    r"Select-String -Path scripts\ac.py -Pattern gate",
    r"python -m unittest discover -s scripts\tests",
    r"py -3 scripts\ac.py --work c check intake.3",
    r"& 'C:\Program Files\Python312\python.exe' scripts\ac.py --work c status",
    r"python scripts\ac.py --work c front report frase --file rel.md",
    "git commit -m 'ac.py: gate e preauth no Windows'",
    r"Get-Content campanhas\x\aprovar-x.sh",
    "python --version",
    "'print(1)' | python -",
    "Get-Content notas.txt | py -3 -",
]
BASH_PERMITE = [
    "python.exe --version",
    "py -3 -m unittest discover -s scripts/tests",
    "py -3 scripts/ac.py --work c status",
    "cat notas.txt | py -3 -",
    "python.exe scripts/ac.py --work c load oraculo",
]

# H5 — indireções do PowerShell: o texto interno cita ac.py/co.py/aprovar-*.sh + gate/preauth/frase/approve.
# Mesma régua do `eval`/`sh -c` do bash.
H5_PS_NEGA = [
    r'iex "python scripts\ac.py --work c gate stop --by f --decision approve"',
    r"Invoke-Expression 'python scripts\ac.py --work c preauth commit --by f'",
    r"Invoke-Command -ScriptBlock { python scripts\ac.py --work c preauth commit --by f }",
    r'powershell -Command "python scripts\ac.py --work c gate stop"',
    r'powershell.exe -NoProfile -Command "py -3 C:\x\scripts\ac.py --work c gate stop"',
    r"pwsh -c 'python scripts\ac.py --work c frase conferir'",
    r'cmd /c "python scripts\ac.py --work c gate stop"',
    r'cmd.exe /c "python C:\x\scripts\co.py --work o approve entrega"',
    r"& { python scripts\ac.py --work c frase conferir }",
    r'iex "& .\campanhas\x\aprovar-x.sh"',
    r'powershell -Command "& .\campanhas\x\aprovar-x.sh"',
]
# Indireções inócuas: não podem virar falso positivo. Os 3 primeiros são os do contrato.
H5_PS_PERMITE = [
    'iex "git status"',
    'powershell -Command "Get-ChildItem"',
    "cmd /c dir",
    r"pwsh -c 'python scripts\ac.py --work c status'",
    "Invoke-Command -ScriptBlock { Get-ChildItem }",
    "& { git status }",
]


def b64_ps(cmd):
    """Base64 do -EncodedCommand do PowerShell: UTF-16LE do texto."""
    return base64.b64encode(cmd.encode("utf-16-le")).decode("ascii")


# -EncodedCommand / -enc / -ec: conteúdo opaco → NEGADO sempre, inclusive com um comando inócuo dentro.
H5_PS_ENCODED_NEGA = [
    "powershell -EncodedCommand " + b64_ps(r"python scripts\ac.py --work c gate stop"),
    "pwsh -enc " + b64_ps(r"python scripts\ac.py --work c preauth commit"),
    "powershell -EncodedCommand " + b64_ps("Get-ChildItem"),
    "pwsh -enc " + b64_ps("git status"),
    "powershell.exe -NoProfile -ec " + b64_ps("Get-ChildItem"),
    "pwsh.exe -NonInteractive -ENC " + b64_ps("Write-Output ok"),
]
# O mesmo -EncodedCommand pela ferramenta Bash (Git Bash chamando o PowerShell): NEGADO sempre.
H5_BASH_ENCODED_NEGA = [
    "powershell.exe -enc " + b64_ps(r"python scripts\ac.py --work c gate stop"),
    "powershell -EncodedCommand " + b64_ps(r"python scripts\ac.py --work c preauth commit"),
    "pwsh -ec " + b64_ps("python scripts/ac.py --work c frase conferir"),
    "powershell.exe -enc " + b64_ps("Get-ChildItem"),
    "powershell -EncodedCommand " + b64_ps("git status"),
    "pwsh -ec " + b64_ps("Write-Output ok"),
]
H5_BASH_PERMITE = [
    'powershell.exe -c "Get-ChildItem"',
]


class _Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hook = carregar_hook()

    def veredito(self, tool, cmd):
        return NEGA if self.hook.decide(payload(tool, cmd)) else PERMITE

    def exigir(self, tool, cmds, esperado):
        erradas = []
        for cmd in cmds:
            with self.subTest(tool=tool, cmd=cmd):
                v = self.veredito(tool, cmd)
                if v != esperado:
                    erradas.append(cmd)
                self.assertEqual(v, esperado, "%s %r -> %s (esperado %s)" % (tool, cmd, v, esperado))
        return erradas


# ============================================================================================================== H1
class H1PowerShellAnalisadoTest(_Base):
    def test_powershell_com_sintaxe_que_o_bash_ja_nega_e_negado(self):
        self.exigir("PowerShell", H1_PS_NEGA, NEGA)

    def test_powershell_ponta_a_ponta_exit_2_com_negado_no_stderr(self):
        raw = json.dumps(payload("PowerShell", "python scripts/ac.py --work c gate stop --by f --decision approve"))
        code, out, err = rodar_hook(raw)
        self.assertEqual(code, 2, "exit %d (esperado 2); stderr=%r" % (code, err))
        self.assertIn("hook_aprovacao: NEGADO", err)
        self.assertEqual(out, "")


# ============================================================================================================== H2
class H2InterpretadorWindowsTest(_Base):
    def test_powershell_interpretador_e_caminho_do_windows_negado(self):
        self.exigir("PowerShell", H2_PS_NEGA, NEGA)

    def test_bash_interpretador_do_windows_lendo_stdin_negado(self):
        self.exigir("Bash", H2_BASH_STDIN_NEGA, NEGA)

    def test_bash_caminho_com_barra_invertida_entre_aspas_negado_em_qualquer_so(self):
        self.exigir("Bash", H2_BASH_PORTABILIDADE_NEGA, NEGA)


# ============================================================================================================== H3
class H3AprovarComBarraInvertidaTest(_Base):
    def test_powershell_aprovar_com_barra_invertida_negado(self):
        self.exigir("PowerShell", H3_PS_NEGA, NEGA)

    def test_bash_aprovar_com_barra_invertida_entre_aspas_negado(self):
        self.exigir("Bash", H3_BASH_NEGA, NEGA)


# ===================================================================================================== H1+H2 stdin
class StdinPowerShellTest(_Base):
    def test_powershell_codigo_pela_stdin_de_interpretador_negado(self):
        self.exigir("PowerShell", STDIN_PS_NEGA, NEGA)


# ============================================================================================================== H5
class H5IndirecaoPowerShellTest(_Base):
    def test_indirecoes_com_aprovacao_negadas(self):
        self.exigir("PowerShell", H5_PS_NEGA, NEGA)

    def test_encoded_command_negado_sempre_mesmo_inocuo(self):
        self.exigir("PowerShell", H5_PS_ENCODED_NEGA, NEGA)

    def test_bash_encoded_command_negado_sempre_mesmo_inocuo(self):
        self.exigir("Bash", H5_BASH_ENCODED_NEGA, NEGA)


# ======================================================================================== H6 (critério de parada 2)
SELFTEST_RE = re.compile(r"selftest:\s*(\d+)/(\d+)\s+ok")


class H6SelftestAmpliadoTest(_Base):
    def test_selftest_tem_mais_de_83_casos_todos_ok(self):
        code, out, err = rodar_hook("", "--selftest")
        m = SELFTEST_RE.search(out)
        self.assertIsNotNone(m, "saída do --selftest sem 'selftest: N/M ok': %r %r" % (out, err))
        ok, total = int(m.group(1)), int(m.group(2))
        self.assertEqual(ok, total, out)
        self.assertGreater(total, 83, "o --selftest ainda tem só %d casos (esperado > 83)" % total)

    def test_selftest_inclui_powershell_negado_e_permitido(self):
        """Espiona `decide` durante `selftest()` em processo: exige ao menos um payload tool_name "PowerShell"
        negado (motivo) e um permitido (None). O tool_name só existe no payload, e `decide` é a porta dele."""
        hook = carregar_hook()
        original = hook.decide
        chamadas = []

        def espiao(p):
            r = original(p)
            chamadas.append((p, r))
            return r

        hook.decide = espiao
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            hook.selftest()
        ps = [(p, r) for p, r in chamadas if isinstance(p, dict) and p.get("tool_name") == "PowerShell"]
        self.assertTrue(any(r for _, r in ps), "selftest sem payload PowerShell NEGADO (chamadas PowerShell: %r)" % ps)
        self.assertTrue(any(r is None for _, r in ps),
                        "selftest sem payload PowerShell PERMITIDO (chamadas PowerShell: %r)" % ps)


# ============================================================================================================== H4
def _ler(caminho):
    with open(caminho, encoding="utf-8") as fh:
        return fh.read()


def _matchers_json(texto):
    return re.findall(r'"matcher"\s*:\s*"([^"]*)"', texto)


def _inclui_bash_e_powershell(matcher):
    partes = {p.strip() for p in matcher.split("|")}
    return "Bash" in partes and "PowerShell" in partes


class H4DocsMatcherPowerShellTest(unittest.TestCase):
    def test_skill_md_instrui_matcher_bash_e_powershell(self):
        texto = _ler(SKILL_MD)
        achados = re.findall(r"matcher[^\n]{0,40}?((?:Bash|PowerShell)(?:\s*\|\s*(?:Bash|PowerShell))+)", texto)
        achados += _matchers_json(texto)
        self.assertTrue(any(_inclui_bash_e_powershell(m) for m in achados),
                        "SKILL.md não instrui matcher com Bash e PowerShell (achados: %r)" % achados)

    def test_readme_ou_referencia_cli_registra_matcher_bash_e_powershell(self):
        achados = {}
        for caminho in (README_MD, REF_CLI_MD):
            achados[os.path.basename(caminho)] = _matchers_json(_ler(caminho)) if os.path.exists(caminho) else []
        self.assertTrue(any(_inclui_bash_e_powershell(m) for ms in achados.values() for m in ms),
                        "nem README.md nem docs/04-referencia-cli.md registram \"matcher\" com Bash e PowerShell "
                        "(achados: %r)" % achados)

    def test_comando_do_hook_para_windows_nativo_com_python(self):
        """SKILL.md ou docs/04 mostram o comando do hook com `python`/`py -3` (não `python3`) perto de "Windows"."""
        cmd_re = re.compile(r"(?<![\w./\\-])(?:pythonw?(?:\.exe)?|py(?:\.exe)?(?:\s+-3(?:\.\d+)?)?)(?=[\s\"'])"
                            r"[^\n]{0,200}?hook_aprovacao\.py")
        achados, sem_windows = [], []
        for caminho in (SKILL_MD, REF_CLI_MD):
            if not os.path.exists(caminho):
                continue
            linhas = _ler(caminho).split("\n")
            for i, linha in enumerate(linhas):
                if cmd_re.search(linha):
                    perto = "\n".join(linhas[max(0, i - 15):i + 16])
                    alvo = achados if "Windows" in perto else sem_windows
                    alvo.append("%s:%d: %s" % (os.path.basename(caminho), i + 1, linha.strip()))
        self.assertTrue(achados, "nem SKILL.md nem docs/04-referencia-cli.md mostram o comando do hook com `python` "
                                 "(ou `py -3`) a até 15 linhas de \"Windows\" (sem Windows por perto: %r)" % sem_windows)

    def test_nenhuma_instrucao_restante_com_matcher_so_bash(self):
        velhos = []
        for caminho in (SKILL_MD, README_MD, REF_CLI_MD):
            if not os.path.exists(caminho):
                continue
            texto = _ler(caminho)
            for m in re.finditer(r'"matcher"\s*:\s*"Bash"|matcher\s+`Bash`', texto):
                linha = texto.count("\n", 0, m.start()) + 1
                velhos.append("%s:%d: %s" % (os.path.basename(caminho), linha, m.group(0)))
        self.assertEqual(velhos, [], "instrução de registro com matcher só Bash ainda presente")


# ========================================================================================================= guardas
class GuardaSemRegressaoTest(_Base):
    def test_selftest_antigo_negados_continuam_negados_no_bash(self):
        self.assertEqual(len(FROZEN_DENY), 44)
        self.exigir("Bash", FROZEN_DENY, NEGA)

    def test_selftest_antigo_permitidos_continuam_permitidos_no_bash(self):
        self.assertEqual(len(FROZEN_ALLOW), 30)
        self.exigir("Bash", FROZEN_ALLOW, PERMITE)

    def test_ferramenta_read_continua_permitida(self):
        self.assertIsNone(self.hook.decide({"tool_name": "Read", "tool_input": {"file_path": "/tmp/ac.py"}}))

    def test_payloads_brutos_mantem_o_exit(self):
        for raw, esperado in FROZEN_RAW:
            with self.subTest(raw=raw):
                code, _, err = rodar_hook(raw)
                self.assertEqual(code, esperado, "payload %r: exit %d (esperado %d); stderr=%r" % (
                    raw, code, esperado, err))

    def test_hook_selftest_exit_0(self):
        code, out, err = rodar_hook("", "--selftest")
        self.assertEqual(code, 0, "selftest saiu %d\n%s\n%s" % (code, out, err))


class GuardaOutrasFerramentasTest(_Base):
    def test_ferramentas_nao_shell_continuam_none(self):
        texto = "python scripts/ac.py --work c gate stop; bash ./aprovar-x.sh"
        casos = [
            {"tool_name": "Read", "tool_input": {"file_path": "scripts/ac.py"}},
            {"tool_name": "Write", "tool_input": {"file_path": "x.sh", "content": texto}},
            {"tool_name": "Edit", "tool_input": {"file_path": "x.sh", "old_string": "a", "new_string": texto}},
            {"tool_name": "Grep", "tool_input": {"pattern": "gate|preauth", "path": "scripts"}},
            {"tool_name": "Glob", "tool_input": {"pattern": "**/aprovar-*.sh"}},
            {"tool_name": "Task", "tool_input": {"prompt": texto, "command": texto}},
        ]
        for p in casos:
            with self.subTest(tool=p["tool_name"]):
                self.assertIsNone(self.hook.decide(p))

    def test_powershell_sem_comando_string_e_none(self):
        for ti in ({}, {"command": None}, {"command": 5}, {"command": ["python", "ac.py", "gate"]}):
            with self.subTest(tool_input=ti):
                self.assertIsNone(self.hook.decide({"tool_name": "PowerShell", "tool_input": ti}))


class GuardaPermitidosTest(_Base):
    def test_powershell_permitidos(self):
        self.exigir("PowerShell", PS_PERMITE, PERMITE)

    def test_bash_interpretador_do_windows_sem_aprovacao_permitido(self):
        self.exigir("Bash", BASH_PERMITE, PERMITE)

    def test_powershell_indirecoes_inocuas_permitidas(self):
        self.exigir("PowerShell", H5_PS_PERMITE, PERMITE)

    def test_bash_powershell_command_inocuo_permitido(self):
        self.exigir("Bash", H5_BASH_PERMITE, PERMITE)

    def test_powershell_permitido_ponta_a_ponta_exit_0_sem_saida(self):
        code, out, err = rodar_hook(json.dumps(payload("PowerShell", r"python scripts\ac.py --work c status")))
        self.assertEqual((code, out, err), (0, "", ""))


if __name__ == "__main__":
    unittest.main()
