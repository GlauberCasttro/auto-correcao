# Etapa `plano`

**Objetivo** (`ciclo.json5`): `PLANO.json5` com decisões, contrato de nomes e frentes disjuntas que não
tocam o oráculo.

Rodada: repete (`per_round`). Anterior: [diagnostico](diagnostico.md). Próxima: [correcao](correcao.md).
Guia completo: [03-frentes-paralelas.md](../03-frentes-paralelas.md).

## Por que existe

- **L09** — "Frentes paralelas precisam de arquivos disjuntos E de um contrato de nomes fixado antes;
  senão o código, a doc e o corretor divergem."
- **L06** — subagentes que gravam arquivos de outros sobrescrevem trabalho.
- Trava 2 (quem corrige não mexe no oráculo) e trava 3 (decisão de produto é portão humano).

## Sub-etapas

| ID | ctx | O que fazer | Check | Recusa quando |
|---|---|---|---|---|
| `plano.1` | main | frentes com conjuntos de escrita disjuntos e contrato de nomes | `plan check` | sem `PLANO.json5`; sem frentes; frente sem `escreve`; frente escreve no oráculo; frentes sobrepostas; sem `parada` |
| `plano.2` | user | decisões de produto aprovadas pelo usuário (ou nenhuma) | `plan gates` | alguma decisão `produto: true` sem portão `plan:<id>` aprovado |

## Formato (`formatos.json5` → `plano`)

```json5
{parada: "qualidade >= 12/13 nos 3 alvos; zero contornos manuais",
 decisoes: [{id: "DEC-1", produto: true, texto: "--fast vira o modo padrão"}],   // esquema v0.3 {id, produto, texto}
 contrato: {"flag-rapida": "--fast"},
 frentes: [{nome: "frente-scan", escreve: ["src/**"], defeitos: ["D-1-01"], criterio: "teste falha antes e passa depois"},
           {nome: "frente-docs", escreve: ["docs/**", "SKILL.md"], defeitos: ["D-1-02"], criterio: "teste falha antes e passa depois"}]}
```

`parada` é copiado do intake. Globs de `escreve` são relativos ao alvo. Só defeitos de classe `sistema`
devem virar frentes (L08) — o script não confere isso.

## Comandos

```bash
ac load plano
# escrever rounds/<n>/PLANO.json5
ac plan check
ac gate plan:DEC-1 --by <humano> --decision approve     # uma por decisão de produto
ac plan gates
ac done plano
```

## Exemplo real

```
$ ac plan check
NÃO: frentes frente-scan e frente-docs se sobrepõem (src/** ~ src/scan/**)
[exit 1]

$ ac plan check
NÃO: frente frente-evals escreve no oráculo (evals/** ~ evals/grader.py)
[exit 1]

$ ac plan check
plano ok

$ ac plan gates
NÃO: decisões de produto sem portão aprovado: ['DEC-1'] (ac.py gate plan:<id> ...)
[exit 1]

$ ac done plano
NÃO: etapa 'plano' não fecha:
  plano.2: decisões de produto sem portão aprovado: ['DEC-1'] (ac.py gate plan:<id> ...)
[exit 1]

$ ac gate plan:DEC-1 --by founder --decision approve
portão plan:DEC-1: approve por founder

$ ac done plano
etapa 'plano' fechada
```

## Erros comuns

- Globs sem prefixo de diretório (`*.py`, `**/*.md`) — colidem com tudo no `globs_overlap`.
- Duas frentes que precisam do mesmo arquivo: junte-as numa só ou mova a parte comum para o integrador.
- Deixar nome novo (flag, campo) para cada frente inventar — fixe em `contrato` antes.
- Frente para defeito de classe `oraculo` — vai por `oracle change`, não por frente; e o `plan check`
  recusa se o glob tocar o arquivo congelado.
- Reutilizar `DEC-1` numa rodada seguinte com outro significado: o portão `plan:DEC-1` da rodada anterior
  continua aprovado (portões não são zerados pelo `round new`). Use ids novos.
- Plano só com defeitos de oráculo: `plan check` exige ao menos uma frente.
