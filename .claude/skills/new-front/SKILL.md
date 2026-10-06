---
name: new-front
description: Abre uma frente de desenvolvimento da skill auto-correcao — campanha auto-correcao orquestrada pelo ac.py ESTÁVEL (um --scope por glob), cópia de trabalho, registro no WORKFLOW, oráculo por agente separado e script de aprovação para o founder. Use quando o usuário pedir para começar/abrir uma frente, corrigir defeitos AC-nn, "nova frente", "new front", ou levar um item do BACKLOG para entrega.
---

# new-front — abrir frente (= campanha)

Uma frente ativa por vez; outra só com `--paralela` (o `overlap` do ac.py estável precisa provar disjunção).
**Use SEMPRE o ac.py estável, por caminho literal** (o motor em edição não julga a si mesmo):
`python3 local/ac-estavel/scripts/ac.py --work campanhas/<frente> <comando>`.
Nunca rode gate/preauth/conferência: são do founder.

1. Pré: `bash .claude/tools/ac-estavel.sh --check` (íntegro; AUSENTE num clone novo ⇒ `bash .claude/tools/ac-estavel.sh --refresh`) e `python3 .claude/tools/frente.py list --ativas`.
2. Escolha com o founder o item do BACKLOG, o escopo (globs relativos à skill) e o critério de parada MEDIDO.
   Hook (`scripts/hook_aprovacao.py`) e ac.py em frentes separadas, de preferência.
3. `python3 .claude/tools/frente.py open <frente> --scope 'scripts/ac.py' --scope 'scripts/tests/**' --problem "..."
   --stop "..." [--dry-run]` — um `--scope` por glob (glob com vírgula é recusado). Cria a campanha em
   `campanhas/<frente>`, a cópia de trabalho e o registro no WORKFLOW.
4. Conduza intake/oráculo pelo ac.py estável (`load`, `check`, `done` — veja `docs/` da skill).
5. Oráculo: despache um agente SEPARADO (não o corretor) para escrever um teste por defeito em
   `campanhas/<frente>/oraculo/`, lendo `os.environ.get("ORACULO_SCRIPTS")`/`ORACULO_SKILL` com fallback para a skill viva
   (o portão aponta para a cópia limpa). Os que falham hoje provam o defeito. Congele com `oracle freeze --file A
   --file B ...` (todos os arquivos; AC-14: `oracle change` também precisa de TODOS).
6. Gere o script de aprovação (não rode):
   `python3 .claude/tools/script-aprovacao.py <frente> --gate stop="..." --gate oracle:requisito="..."
   --preauth commit=integracao.1="commit se verde" --conferir --resumo "1. stop: ..." --resumo "2. ..."`.
   Diga ao founder o caminho e o que ele aprova; espere ele avisar. Nunca peça a senha no chat.
7. `python3 .claude/tools/sessao.py log --resumo "frente <frente> aberta" --frente <frente>`.
