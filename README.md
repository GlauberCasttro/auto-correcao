# auto-correcao

Skill do Claude Code para **laços de refinamento medidos**: uma campanha com máquina de estado em JSON
(`scripts/ac.py`), oráculo congelado, base medida antes de corrigir, rodadas de correção com remedição real e
decisão registrada. Aprovação humana (portões `gate`/`preauth`) só no terminal do humano, com a senha ou frase
dele (tag HMAC por aprovação, conferida no fim), e um hook global (`scripts/hook_aprovacao.py`) que nega ao agente
os comandos de aprovação. Leia `SKILL.md` (o que a skill faz) e `docs/` (máquina de estado, oráculo, CLI, lições,
limites). Versão: **v0.4.1**.

Este repositório é o PROJETO de desenvolvimento: a raiz é a própria skill (`SKILL.md` na raiz) mais o harness de
desenvolvimento (`.claude/`), as campanhas que entregaram cada versão (`campanhas/`) e o estado do trabalho
(`.claude/state/`: RESUME, BACKLOG, DECISIONS, WORKFLOW).

```
SKILL.md  scripts/ (ac.py, frase.py, hook_aprovacao.py, tests/)  references/  docs/  evals/
.claude/  CLAUDE.md (regras do harness) · tools/ (portão, portar, conferir, guards, ac-estavel…) · skills/ · state/
campanhas/  oráculos das campanhas desta skill (README.md = tabela campanha → entrega → decisão)
local/      (no .gitignore) ac.py estável, cópias de trabalho, portões, termos privados — só desta máquina
```

## Requisitos
- Python **3.9+** (só a biblioteca padrão; testado em 3.13 e no `/usr/bin/python3` 3.9 do macOS), bash, git.
- macOS ou Linux (a aprovação usa `pty`/tty real), ou Windows nativo: lá os exemplos com `python3` viram `python`
  (ou `py -3`), ex.: `python ~/.claude/skills/auto-correcao/scripts/ac.py frase definir`. A frase só entra pelo
  console (PowerShell ou Windows Terminal); no Git Bash, `winpty python .../ac.py ...`. Na suíte da skill, os testes
  que precisam de `pty` são pulados no Windows (com o motivo).

## Instalar a skill a partir do projeto
A skill é instalada por **link**, para que a evolução no projeto seja a skill em uso:

```sh
ln -s "$PWD" ~/.claude/skills/auto-correcao        # rodado na raiz do projeto
```

### Hook global de aprovação (uma vez por máquina)
Acrescente ao `~/.claude/settings.json` (mesclando com os `hooks` que já existirem). O caminho passa pelo link, então
continua valendo quando o projeto muda de lugar:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$HOME/.claude/skills/auto-correcao/scripts/hook_aprovacao.py\""
          }
        ]
      }
    ]
  }
}
```

Confira: `python3 "$HOME/.claude/skills/auto-correcao/scripts/hook_aprovacao.py" --selftest` (exit 0) — de
preferência também com `/usr/bin/python3`.

## Primeira vez numa máquina nova
1. Clone, instale o link e o hook (acima).
2. **No seu terminal** (nunca pelo agente, nunca no chat), defina a sua senha ou frase de aprovação:
   `python3 ~/.claude/skills/auto-correcao/scripts/ac.py frase definir`. Senha forte (≥12 caracteres, 3 tipos) ou
   frase (≥3 palavras, ≥12 caracteres). Ela fica em `~/.claude/auto-correcao/`, fora do projeto.
3. Na raiz do projeto:
   ```sh
   bash .claude/tools/ac-estavel.sh --refresh           # extrai o ac.py estável (o juiz das campanhas) do HEAD
   bash .claude/tools/guard-privacidade.sh --install-hooks   # pre-commit e commit-msg contra termo privado
   git config user.name  "<seu usuário>"; git config user.email "<seu e-mail noreply>"
   ```
   Opcional: `local/termos-privados.txt` com os seus termos privados (um por linha). Sem ele o guard avisa e usa só
   os padrões genéricos (caminho de usuário, e-mail pessoal).
4. Verifique: `bash .claude/tools/verificar-harness.sh --suites` (~3 min; suítes nos 2 Pythons + hook --selftest).

## Como desenvolver
Abra o Claude Code **na raiz do projeto** (é ali que os guards do `.claude/settings.json` valem) e comece pela skill
`/load-session`. O fluxo (detalhado em `.claude/CLAUDE.md`): `new-front` abre uma frente = campanha (com o ac.py
ESTÁVEL, nunca o que está em edição) → oráculo por agente separado → você aprova no seu terminal o
`campanhas/<frente>/aprovar-<frente>.sh` gerado → correção numa cópia de trabalho em `local/work/` → portão em cópia
limpa (2 Pythons, hook --selftest, oráculos, nenhum `def` removido) → `portar.sh` (com rede de segurança do hook e
das campanhas existentes) → `conferir-commit.sh` → commit só dos arquivos da frente → `close-front` →
`/save-session`. O guard de git nega `push`: publicar é sempre seu, no seu terminal.

Testes:
```sh
cd scripts && PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests          # skill (101)
cd .claude/tools && PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests   # harness
```

## Limites
- Os testes da skill não dependem de recurso privado: rodam em qualquer máquina, sem pulos no macOS/Linux. Os que
  exercitam a aprovação usam `pty` e um `HOME` temporário (a sua senha real nunca é lida); no Windows, sem `pty`,
  esses são pulados com o motivo e os demais rodam.
- Os oráculos em `campanhas/*/oraculo/` são históricos: testam a skill pelo caminho instalado
  (`~/.claude/skills/auto-correcao`), não a pasta em que estão.
- O hook global é um filtro sintático, não uma sandbox; a garantia forte é a senha (veja `docs/07-limites.md`).
  Ele tem falsos positivos conhecidos (BACKLOG AC-13/AC-15).
- `portar.sh` vigia as campanhas que encontrar na máquina; numa máquina sem campanhas não há nada a vigiar.

## Licença
MIT — veja `LICENSE`.
