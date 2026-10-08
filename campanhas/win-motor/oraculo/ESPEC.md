# Oráculo de aceite — campanha win-motor (motor da auto-correcao compatível com Windows)

Autor: escritor do oráculo, separado do corretor (quem testa não constrói). Arquivo: `test_win_motor.py` (unittest
puro, stdlib, Python 3.9+, sem `pty`). Cada teste de W1–W7 FALHA hoje pelo motivo do defeito e passa quando a
correção estiver feita. Os testes marcados **guarda** passam hoje e passam depois: protegem contra regressão.

Fonte dos defeitos: `codebase-specialists/local/auditoria-windows-2026-10-07.md`, coluna "motor (auto-correcao)".

## Rodar

A partir da raiz do projeto `auto-correcao`:

- Windows nativo (Git Bash): `env -u PYTHONUTF8 python -m unittest discover -s campanhas/win-motor/oraculo -v`
- Windows nativo (PowerShell): `Remove-Item Env:PYTHONUTF8 -ErrorAction SilentlyContinue; python -m unittest discover -s campanhas/win-motor/oraculo -v`
- Linux/WSL/macOS: `env -u PYTHONUTF8 python3 -m unittest discover -s campanhas/win-motor/oraculo -v`
- Contra uma cópia limpa (portão): `ORACULO_SKILL=<raiz da cópia>`. Também existe `ORACULO_SCRIPTS=<pasta scripts>`.
  Sem essas variáveis, a skill testada é a raiz deste projeto, três pastas acima do arquivo de teste.

Isolamento: `HOME`, `USERPROFILE`, `AC_FRASE_FILE` e `AC_AUDIT_LOG` apontam para um temporário por teste
(`tempfile.mkdtemp()`, apagado no fim). O `~/.claude/auto-correcao/` real nunca é tocado. Nenhum teste roda `gate`,
`preauth` nem `frase` do ac.py. Os testes são multiplataforma: o ramo do "outro" SO é exercitado por mocks
(`patch.object(frase, "_windows")`, `msvcrt` falso via `patch.dict(sys.modules)`, `sys.stdin` falso, `os.open`
espionado).

## Contrato (fixado pelo orquestrador; o corretor implementa exatamente isto)

**W1 — senha no console do Windows (`scripts/frase.py`)**
- `frase._windows() -> bool`: devolve `os.name == "nt"`, consultado no momento da chamada.
- `frase._abrir_console()`: abre e fecha `CONIN$`. Levanta `OSError` se não houver console.
- `exigir_tty()` com `_windows()` True:
  - stdin não-tty: levanta `SemTTY` com uma mensagem que cita `winpty` e `PowerShell`.
  - stdin tty e console ok: devolve `"CONIN$"`.
  - console falha: levanta `SemTTY`.
  - Nunca abre `/dev/tty` nesse ramo.
- `ler(prompt, contexto=None)` com `_windows()` True:
  - Chama `exigir_tty()` e faz `import msvcrt` DENTRO da função.
  - Escreve contexto e prompt só por `msvcrt.putwch`. Lê tecla a tecla por `msvcrt.getwch`.
  - `\r` ou `\n` encerra. `\b` apaga o último caractere. `\x03` levanta `KeyboardInterrupt`. `\x00` e `\xe0`
    descartam também a tecla seguinte. Limite de 4096 caracteres.
  - Nunca ecoa o que foi digitado e nunca lê `sys.stdin`.
- O ramo posix fica inalterado.

**W2 — saída em cp1252.** `ac.py load <etapa>`, `status` e `results` não quebram com stdout num pipe cp1252
(`PYTHONIOENCODING=cp1252` estrito, sem `PYTHONUTF8`).

**W3 — CRLF.**
- (a) O hash do oráculo não depende do final de linha. Uma mudança real de conteúdo continua reprovando.
- (b) `.gitattributes` na raiz da skill fixa `eol=lf` para `*.py`, `*.sh`, `*.json5`, `*.md` e `*.json`.

**W4 — `os.ttyname` ausente.** O ramo posix de `exigir_tty()` devolve `"/dev/tty"` em vez de quebrar.

**W5 — instrução `python3` fixa.** `SKILL.md` documenta como rodar no Windows, com `python` (ou `py -3`) e o `ac.py`.

**W6 — a suíte importa no Windows.** Cada `scripts/tests/test_*.py` importa sem erro quando `pty` e `termios` não
existem. Os testes que precisam de pty se pulam com motivo; isso é do corretor e o oráculo não verifica.

**W7 — caminhos com `\`.** `globs_overlap(a, b)` (assinatura real, `scripts/ac.py`, perto da linha 302) trata `\`
como `/`. Nenhum nome novo foi necessário.

## Requisito → testes (o que cada um prova)

| Req | Teste | Prova |
|---|---|---|
| W1 | `W1ConsoleWindowsTest.test_windows_consulta_os_name_na_chamada` | `_windows()` segue `os.name` no momento da chamada (`nt` → True, `posix` → False) |
| W1 | `…test_abrir_console_sem_console_levanta_oserror` | sem console, `_abrir_console()` levanta OSError. No Windows roda num subprocesso `DETACHED_PROCESS`; no posix, em processo, num cwd sem `CONIN$` |
| W1 | `…test_exigir_tty_windows_stdin_nao_tty_cita_winpty_e_powershell` | stdin não-tty → `SemTTY` que cita `winpty` e `PowerShell`; `/dev/tty` nunca aberto |
| W1 | `…test_exigir_tty_windows_console_ok_devolve_conin` | stdin tty + console ok → `"CONIN$"`; `_abrir_console` foi chamado; `/dev/tty` nunca aberto |
| W1 | `…test_exigir_tty_windows_console_falha_semtty` | `_abrir_console` levanta OSError → `SemTTY` |
| W1 | `…test_ler_windows_le_sem_eco_e_escreve_contexto_e_prompt` | devolve a senha digitada; contexto e prompt saem por `putwch`, o contexto antes do prompt; depois do prompt só `\r`/`\n`; a senha não passa por `putwch`; `sys.stdin` não é lido; stdout e stderr ficam vazios; `getch`/`putch`/`kbhit`… não são usados |
| W1 | `…test_ler_windows_enter_lf_tambem_encerra` | `\n` encerra como `\r` |
| W1 | `…test_ler_windows_enter_imediato_devolve_vazio` | Enter direto → `""` |
| W1 | `…test_ler_windows_backspace_apaga_ultimo` | `abc\bd` → `abd`; `\b` com o buffer vazio não quebra |
| W1 | `…test_ler_windows_ctrl_c_keyboardinterrupt` | `\x03` → `KeyboardInterrupt` |
| W1 | `…test_ler_windows_teclas_especiais_descartadas` | `\x00`+tecla e `\xe0`+tecla são descartadas (`a\x00;b\xe0Hc` → `abc`) |
| W1 | `…test_ler_windows_limite_4096` | 5000 teclas → devolve 4096 |
| W1 | `…test_ler_windows_sem_console_semtty` | console falha → `SemTTY` antes de escrever ou ler qualquer tecla (prova que `ler` passa por `exigir_tty`) |
| W1 guarda | `…test_posix_inalterado_sem_dev_tty_semtty_e_nao_usa_msvcrt` | no ramo posix, sem `/dev/tty` → `SemTTY`, e o `msvcrt` não é tocado |
| W2 | `W2SaidaCp1252Test.test_load_oraculo_em_cp1252` | `load oraculo` (a etapa tem `≈`/`≥`) sai com exit 0, sem traceback, e imprime `# etapa oraculo` |
| W2 | `…test_status_em_cp1252` | `status` com uma etapa completa (marca `✓`) sai com exit 0 e mostra `3/3` |
| W2 | `…test_results_compare_em_cp1252` | `results compare` com duas rodadas (linha com `Δ`) sai com exit 0 e mostra `quality: rodada 1 = 1.00` |
| W2 guarda | `…test_verify_reprovado_em_cp1252_sai_1_sem_traceback` | a recusa do `oracle verify` (stderr com `≠`) sai 1 sem traceback. Passa hoje porque o stderr do Python usa `backslashreplace`; protege contra uma correção que troque o stderr para estrito |
| W3a | `W3CrlfTest.test_freeze_lf_verify_crlf_passa` | congela em LF, reescreve em CRLF → `verify` sai 0 |
| W3a | `…test_freeze_crlf_verify_lf_passa` | congela em CRLF, reescreve em LF → `verify` sai 0 |
| W3a | `…test_campanha_ja_congelada_em_lf_verifica_checkout_crlf` | **caso real**: `state.json` com o hash pela fórmula ANTIGA (bytes LF, como uma campanha congelada no macOS) e o arquivo em CRLF no disco → `verify` sai 0 |
| W3a guarda | `…test_campanha_ja_congelada_em_lf_continua_verificando_lf` | a campanha congelada antes da correção continua verificando com o mesmo LF |
| W3a guarda | `…test_mudanca_real_continua_reprovando` | conteúdo diferente reprova (exit 1), em LF, em CRLF e com uma linha a mais |
| W3b | `…test_gitattributes_fixa_eol_lf` | o `eol` efetivo de cada padrão (`*.py`, `*.sh`, `*.json5`, `*.md`, `*.json`, ou `*`) é `lf`; a última linha que casa vence, e `-text`/`binary` anulam |
| W4 | `W4TtynameAusenteTest.test_exigir_tty_posix_sem_ttyname_devolve_dev_tty` | com `os.ttyname` removido do módulo `os`, stdin tty e `/dev/tty` simulados, o ramo posix devolve `"/dev/tty"` e continua abrindo `/dev/tty` |
| W5 | `W5SkillMdWindowsTest.test_skill_md_documenta_invocacao_no_windows` | `SKILL.md` cita `Windows` e, até 15 linhas depois, mostra `python[.exe] … ac.py` ou `py -3 … ac.py` (`python3` não conta) |
| W6 | `W6SuiteImportaSemPtyTest.test_cada_modulo_de_teste_importa_sem_pty_e_termios` | um subteste por `scripts/tests/test_*.py`, num subprocesso com `sys.modules["pty"] = sys.modules["termios"] = None`: o módulo importa e carrega os testes |
| W7 | `W7BarraInvertidaTest.test_barra_invertida_tratada_como_barra` | `globs_overlap` dá True nos dois sentidos para: `scripts\ac.py`~`scripts/ac.py`, `scripts/*.py`~`scripts\ac.py`, `scripts\tests`~`scripts/tests/*.py`, `scripts\tests\`~`scripts/tests/test_ac.py`, `scripts\tests`~`scripts\tests\x.py`, `scripts\tests\**`~`scripts/tests/sub/a.py` |
| W7 guarda | `…test_disjuntos_continuam_disjuntos` | normalizar `\` não pode virar "tudo sobrepõe": `scripts\ac.py`≁`docs/x.md`, `scripts\tests`≁`scripts/testsX/a.py`, `scripts\tests\*.py`≁`references/ciclo.json5`, `docs\a.md`≁`docs/b.md` |
| guarda | `HookSelftestTest.test_hook_selftest_exit_0` | `scripts/hook_aprovacao.py --selftest` sai 0. Passa hoje (83/83 no Windows e no WSL) e protege contra regressão no hook |

Fixtures que gravam no estado da campanha temporária: W2 marca `intake.1`–`intake.3` como concluídas, e W2/W3 gravam
`round`, `runs.jsonl` ou `oracle` direto no `state.json` do temporário. Nenhum portão é aprovado.

## Resultado hoje (contra o projeto atual, branch `release/version-windows`, 2026-10-07)

Rodado com os comandos acima: Windows 11, Python 3.12.7 (`python`, sem `PYTHONUTF8`), e WSL Ubuntu, Python 3.10.12
(`python3`). Nenhum ERROR nos dois: toda reprovação é FAIL com o motivo do defeito.

| Teste | Windows hoje | WSL hoje | Motivo da falha |
|---|---|---|---|
| W1 (13 testes, exceto a guarda) | FAIL | FAIL | `frase._windows`/`_abrir_console` não existem: o ramo Windows não foi implementado |
| W1 guarda posix | ok | ok | — |
| W2 `load oraculo` | FAIL | FAIL | `UnicodeEncodeError` em `'≈'` (≈) → traceback, exit 1 |
| W2 `status` | FAIL | FAIL | `UnicodeEncodeError` em `'✓'` (✓) |
| W2 `results compare` | FAIL | FAIL | `UnicodeEncodeError` em `'Δ'` (Δ) |
| W2 guarda stderr | ok | ok | — |
| W3 LF→CRLF, CRLF→LF, legado LF→CRLF | FAIL (3) | FAIL (3) | `NÃO: oráculo mudou fora de oracle change (hash … ≠ congelado …)`, exit 1 (hash por bytes) |
| W3 guardas (legado LF, mudança real) | ok | ok | — |
| W3b `.gitattributes` | FAIL | FAIL | o arquivo não existe |
| W4 | FAIL | FAIL | `AttributeError: module 'os' has no attribute 'ttyname'` (frase.py:202 só captura OSError) |
| W5 | FAIL | FAIL | `SKILL.md` não cita Windows |
| W6 (3 subtestes: `test_ac`, `test_v03_oraculo`, `test_v04_frase`) | FAIL (3) | FAIL (3) | `ModuleNotFoundError: import of pty halted` (`_pty_helper.py`, `test_v03`, `test_v04` fazem `import pty` no topo) |
| W7 positivos (6 pares × 2 sentidos) | FAIL (6 de 12) | FAIL (12 de 12) | `globs_overlap` → False. No Windows, `fnmatch` passa por `normcase` (troca `/` por `\`), por isso os 3 pares de arquivo × arquivo/glob passam por acaso. Os pares de diretório (prefixo) falham nos dois |
| W7 guarda disjuntos | ok | ok | — |
| hook `--selftest` | ok | ok | — |

Totais: Windows `Ran 30 tests … FAILED (failures=31)`; WSL `Ran 30 tests … FAILED (failures=37)`. A diferença vem
das contagens por subteste do W7.

**Satisfazível.** Um protótipo descartável, aplicado só numa cópia no scratchpad e nunca neste projeto, passou 30/30
nos dois ambientes (`ORACULO_SKILL=<cópia>`). O protótipo fez cinco coisas:
- o ramo Windows em `frase.py`;
- `except (OSError, AttributeError)` no ttyname;
- `replace(b"\r\n", b"\n")` antes do sha256 de cada arquivo em `sha_files`;
- `\` virando `/` em `_prefix`/`globs_overlap`, e `reconfigure(errors="replace")` no stdout/stderr em `main`;
- `import pty` em `try`, mais `.gitattributes` e uma seção Windows no `SKILL.md`.

## Restrições que os testes impõem além da letra do contrato (para o corretor não se surpreender)

- **W3**: o hash normalizado precisa coincidir com o hash antigo quando o arquivo é só LF. Uma campanha já congelada
  no macOS tem de verificar no checkout CRLF (`test_campanha_ja_congelada_em_lf_verifica_checkout_crlf`). Uma
  normalização `CRLF → LF` antes do sha256 de cada arquivo cumpre isso. Um esquema novo (prefixo de versão, outro
  algoritmo) quebraria as campanhas existentes e reprova.
- **W1**: durante `ler()` no Windows, `sys.stdout`/`sys.stderr` ficam vazios (decorre de "só por putwch"). Depois do
  prompt só pode sair `\r`/`\n`: nem asterisco. Sem console, `ler` não escreve nem lê nenhuma tecla.
- **W2**: a saída pode ser `replace`, `backslashreplace` ou UTF-8. O teste só exige exit 0, nenhum traceback e os
  marcadores ASCII (`# etapa oraculo`, `3/3`, `quality: rodada 1 = 1.00`).

## Pendências para o orquestrador (fora do contrato W1–W7; não testadas)

1. **`ac.py:424` (`os.ttyname` em `human_channel`)**, citado na auditoria: `human_channel` não tem nenhum chamador
   no `scripts/` (código morto do canal v0.3). O W4 cobre só `frase.exigir_tty`. Decidir se remove ou corrige junto.
2. **`chk_plan` ponta a ponta (W7)**: `chk_plan` usa `os.path.relpath` (que no Windows devolve `\`) e
   `of.startswith(base + os.sep)`. O oráculo testa só `globs_overlap`. `ac.py plan check` com um oráculo dentro do
   alvo no Windows não é exercitado. Além disso, no Windows `fnmatch` não diferencia maiúsculas (via `normcase`), e
   isso não foi tratado.
3. **W6 só prova import**: o oráculo não exige que `scripts/tests` rode verde no Windows nem que os testes de pty
   se pulem com motivo. A simulação no posix anula só `pty` e `termios`; no Windows nativo, a ausência real de
   `fcntl`, `SIGKILL` etc. no import já é coberta, porque o mesmo teste roda lá.
4. **`hook_aprovacao.py`, lacunas da auditoria T7**: o matcher só vê `Bash` (o PowerShell passa), `python.exe`/`py`
   e `\` entre aspas. Isso está fora do W1–W7. O selftest aqui é só guarda de regressão.
5. **`ac.py:928` e `:1201`**, citados na auditoria (T3), são exatamente `status` e `results`, cobertos pelo W2. Outros
   `print` com caracteres fora do cp1252 (`gate`, `preauth`, `frase`, `done`…) não são exercitados. Uma correção
   global em `main` (reconfigure) cobre todos; uma correção pontual não.
