# WORKFLOW — auto-correcao

Frente = campanha auto-correcao orquestrada pelo ac.py ESTÁVEL. Uma ativa por vez (paralela só com `--paralela` e
`overlap` disjunto). O bloco abaixo é gerado por `tools/frente.py` a partir de `state/frentes.json`.

<!-- frentes:inicio (gerado por tools/frente.py; não edite à mão) -->
### Frente(s) ativa(s)
- nenhuma (abra com a skill new-front)

### Últimas entregas
- win-motor — commit `3e81f49` em 2026-10-08T12:58:22Z
<!-- frentes:fim -->

## Fila (ordem proposta; o founder reordena)
1. **ac-v05** — P0 do BACKLOG: AC-10, AC-14, AC-08, AC-12 (+ AC-09 se couber). Escopo: `scripts/ac.py`,
   `scripts/tests/**`, `docs/**`, `references/**`. Não toca `scripts/hook_aprovacao.py`.
2. **hook-v05** — AC-15 + AC-13 (falsos positivos do hook global). Escopo: `scripts/hook_aprovacao.py`,
   `scripts/tests/**`. Frente separada: portar o hook muda o hook global de todas as sessões na hora.
3. **licoes-v05** — L19–L23 em `references/licoes.json5`, AC-11 e AC-16 em `docs/`.
