# Desenvolvimento da skill auto-correcao

Você está no PROJETO da skill `auto-correcao` (raiz do projeto = a skill: `SKILL.md` na raiz; repo git próprio,
branch `main`). Instalada, a skill é um link `~/.claude/skills/auto-correcao` → este projeto. Este harness entrega a
evolução da skill: toda mudança no produto passa pelo fluxo abaixo. Markdown explica, script decide
(`.claude/tools/`, todos com `--help`). Nunca fabrique aprovação, execução, contagem ou data. Comece pela skill
`load-session`.

## Layout
- Produto: `SKILL.md`, `scripts/` (ac.py, frase.py, hook_aprovacao.py, tests/), `references/`, `docs/`, `evals/`.
- `campanhas/<frente>/` — campanhas desta skill: oráculo versionado (`oraculo/`); o ledger `.auto-correcao/` e o
  `aprovar-*.sh` ficam no `.gitignore` (caminhos e tags desta máquina).
- `local/` (no `.gitignore`, nunca publicado): `ac-estavel/` (o juiz), `work/<frente>/auto-correcao` (cópias de
  trabalho), `portao-<frente>/` (portões), `termos-privados.txt` (lista do guard de privacidade), notas da máquina.
  Temporários sempre aqui, NUNCA /tmp.

## Esta skill é o MOTOR (cuidado redobrado)
- `scripts/ac.py`/`frase.py` orquestram as campanhas de TODAS as skills; `scripts/hook_aprovacao.py` é o hook
  GLOBAL (`~/.claude/settings.json`, PreToolUse Bash de toda sessão, pelo caminho do link
  `$HOME/.claude/skills/auto-correcao/scripts/hook_aprovacao.py`). Quebrar um deles quebra os outros projetos.
- **As campanhas desta skill usam o ac.py ESTÁVEL**, por caminho literal relativo à raiz do projeto:
  `python3 local/ac-estavel/scripts/ac.py --work campanhas/<frente> ...` (cópia de um commit DESTE projeto,
  conferida por `tools/ac-estavel.sh --check`; ausente num clone novo → `tools/ac-estavel.sh --refresh`). NUNCA o
  `scripts/ac.py` em edição: o motor não julga a si mesmo. Trocar o estável: `--refresh`, só sem campanha aberta,
  depois de uma entrega.
- `tools/portar.sh` roda o `--selftest` do hook antes e depois e o `status` de toda campanha encontrada na máquina
  (as deste projeto, `~/.claude/skills/*-workspace`, `<pasta-mãe>/*/campanhas`; ou `$AC_DEV_VIGIAR`) antes e depois
  de portar ac.py/frase.py/references; regrediu ⇒ restaura o backup. Nenhuma campanha = "nada a vigiar".
  Hook e ac.py: de preferência frentes separadas.

## Fluxo de entrega
1. `new-front`: `tools/frente.py open <frente> --scope G --scope G2 --problem .. --stop ..` (um `--scope` por glob)
   → campanha em `campanhas/<frente>` + cópia de trabalho em `local/work/<frente>/auto-correcao`.
2. Oráculo por um agente SEPARADO (quem testa não constrói), lendo `ORACULO_SCRIPTS`/`ORACULO_SKILL` (o portão
   recusa oráculo que testaria a skill viva). Congelado (`oracle freeze`). Mudança só oficial (`oracle change --why
   --evidence`, patch + PORQUE em `mudanca-oficial/`). **Defeito AC-14: `oracle change --file X` substitui a lista
   inteira — passe SEMPRE todos os arquivos do oráculo.**
3. Aprovação humana: `tools/script-aprovacao.py <frente> --gate .. --preauth .. --conferir` GERA
   `campanhas/<frente>/aprovar-<frente>.sh`; o founder roda no terminal dele com a senha. Nunca peça a senha no chat;
   nunca aprove; nunca rode o script gerado.
4. Corretor (agente) só na cópia de trabalho (`local/work/<frente>/auto-correcao`), escopo declarado. Máx. 5 agentes
   simultâneos (3 se houver 429). Confirme custo antes de medição pesada.
5. `tools/portao.sh <frente> [--oraculo DIR:MOD] -- <arq1> <arq2>` (cópia limpa: HEAD + só os arquivos da frente;
   2 Pythons; hook --selftest; oráculos; nenhum def removido). Leia `local/portao-<frente>/portao.out` até `FIM`.
6. `tools/portar.sh <frente> -- <arqs>` → `tools/conferir-commit.sh <frente> -- <arqs>` → `git add <arqs>` pelo nome
   → `git commit -F <arquivo-msg> -- <arqs>`. Se o portar fez merge de 3 vias, rode o portão de novo com
   `--src .` (o projeto) antes de conferir.
7. Fechar a campanha com o ac.py estável (front report, done…, run record --decision, decision/report); a conferência
   (`frase conferir`) é do founder, no fim do script de aprovação (ou `--so-conferir`); `done decisao`;
   `tools/frente.py close <frente> --commit <sha>`. Skill `close-front`.
Achados de uso real vindos de outras sessões chegam por mensagem e viram item do BACKLOG/frente; ninguém edita a
skill viva por fora.

## Git e privacidade (projeto PÚBLICO)
- Guard `tools/guard-git.sh` nega: reset --hard, checkout --/., restore (fora --staged), clean -f, stash (fora
  list/show), push (sempre — push é do humano), add -A/--all/., commit -a. Não há escape: o humano faz no terminal.
- Commit só dos arquivos da frente, mensagem em ARQUIVO (`-F`, em `local/`): o hook global nega texto com
  gate/approve/frase junto de ac.py na linha de comando. Estado: `tools/commit-state.sh --msg-file ARQ`.
  Autor: o noreply do GitHub do dono do repositório (`git config` local do clone).
- `tools/guard-privacidade.sh` (termos em `local/termos-privados.txt`, nunca versionado) roda no pre-commit e no
  commit-msg (instale por clone: `--install-hooks`), no `conferir-commit.sh` e no `commit-state.sh`. Nada de nome
  real, caminho de usuário, e-mail pessoal, senha ou token em arquivo versionado ou mensagem de commit.

## Edição
`tools/guard-entrega.py` nega Edit/Write no produto (o projeto, exceto `.claude/state/**`, `campanhas/**` e
`local/**`), em `local/ac-estavel/**`, nas cópias `local/portao-*` e nos ledgers `campanhas/*/.auto-correcao/**`.

## Rituais
`load-session` (carimbo + RESUME + WORKFLOW + status da campanha) · `save-session` (RESUME/WORKFLOW, log
`tools/sessao.py log`, decisões, commit só do state) · `new-front` · `close-front`. Âncora: `tools/carimbo.sh`
(SessionStart injeta `--brief`). Verificação do harness: `tools/verificar-harness.sh [--suites]`.

## Lições (curtas)
- zsh não faz word-split de `$VAR`: liste os arquivos um por um nos tools.
- Mensagem de commit sempre em arquivo (`-F`). Caminho LITERAL do ac.py (o hook nega `$AC` + subcomando aprovador).
  O hook também nega heredoc/`python3 -` cujo texto cite script de aprovação + gate/frase (AC-15): ponha o código
  num arquivo em `local/` e rode o arquivo.
- AC-09: `run record` no mesmo segundo do `done correcao` é recusado — espere 1 s e registre de novo.
- AC-14: `oracle change` substitui a lista — passe todos os arquivos.
- Só entra no commit o que o portão testou (`conferir-commit.sh`). Suítes da skill: `cd scripts &&
  PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests` (e `/usr/bin/python3`), ~3 min os dois.
- A cópia de trabalho e o portão moram dentro do projeto (em `local/`, ignorado) e não têm `.git` próprio: `git`
  rodado lá dentro enxerga o repo do projeto. Não rode git nas cópias.

## O que NÃO existe (não alegue)
- Os guards só valem com a sessão aberta NA RAIZ do projeto (ou no link `~/.claude/skills/auto-correcao`). Aberta em
  outra pasta, nada disto roda (o hook global de aprovação roda sempre, se instalado em `~/.claude/settings.json`).
- guard-entrega não vê Bash (cp, sed -i, >): o caminho sancionado é `tools/portar.sh`; o resto é disciplina + diff.
- O hook global é filtro sintático, não sandbox; a garantia é a senha (D-01). `portar.sh` confere campanhas só por
  `status`, não reconfere tags. A campanha mora DENTRO do alvo (o projeto) por desenho do projeto público (D-08):
  a regra da skill "campanha fora do alvo" é atendida pelo `.gitignore` do ledger + guard-entrega + escopo, não
  por diretório separado.
