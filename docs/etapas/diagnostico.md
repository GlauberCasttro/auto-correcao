# Etapa `diagnostico`

**Objetivo** (`ciclo.json5`): `DEFEITOS.json5` com evidência exata, prioridade e classe.

Rodada: repete a cada rodada (`per_round`). Anterior: [base](base.md) (rodada 0) ou [decisao](decisao.md)
da rodada anterior, via `round new`. Próxima: [plano](plano.md).

## Por que existe

- **L08** — "Classifique o defeito antes de corrigir: sistema, oráculo, ambiente ou executor. Metade dos
  NO-GO vinha do oráculo ou do gerador de provas, não do sistema." Evidência: "5 agentes 'reprovados' só
  por perguntas de sha sem .git no exame; 13 respostas certas reprovadas por regex de 'nenhum'."
  Regra: "só defeito de classe sistema vira frente de correção."

## Sub-etapas

| ID | ctx | O que fazer | Check | Recusa quando |
|---|---|---|---|---|
| `diagnostico.1` | main | ler `notes.md` e asserções falhas; reproduzir os P0 | `defects --min 1 --evidence` | sem `rounds/<n>/DEFEITOS.json5`; zero defeitos; algum sem `evidencia` |
| `diagnostico.2` | main | classificar: sistema \| oraculo \| ambiente \| executor | `defects --classified` | classe fora das quatro ou prioridade fora de `P0..P3` |

## As quatro classes

| Classe | Exemplo | Destino |
|---|---|---|
| `sistema` | comando do sistema falha; instrução errada; contorno manual necessário | frente de correção |
| `oraculo` | corretor lê negação como afirmação; campo com nome divergente | `ac.py oracle change --why --evidence` + recalibração, fora das frentes |
| `ambiente` | ferramenta ausente, limite de API (ex.: 429) | ajustar ambiente/orçamento; não é correção do sistema |
| `executor` | o subagente executor desviou do roteiro | ajustar o prompt/execução; não é correção do sistema |

Prioridade (`formatos.json5`): P0 = "bloqueia ou faz o veredito mentir"; P1–P3 decrescentes.

## Formato (`formatos.json5` → `defeitos`)

Arquivo `<work>/.auto-correcao/rounds/<n>/DEFEITOS.json5` (crie a pasta se ainda não existir):

```json5
{defeitos: [
  {id: "D-1-01", titulo: "comando scan falha", classe: "sistema", prioridade: "P0",
   evidencia: ["python3 src/app.py scan → KeyError: 'files'", "src/app.py:1"], reproduzido: true, frente: "frente-scan"},
  {id: "D-1-02", titulo: "docs citam flag inexistente", classe: "sistema", prioridade: "P1",
   evidencia: ["docs/uso.md:12 cita --fast; ac --help não lista"], reproduzido: true, frente: "frente-docs"},
  {id: "D-1-03", titulo: "grader lê negação como afirmação", classe: "oraculo", prioridade: "P2",
   evidencia: ["run1/report.md:40"], reproduzido: true},
]}
```

`id` segue `D-<rodada>-<nn>`. Evidência = "comando + erro literal", "arquivo:linha" ou
"execução: <dir>/notes.md#item". `reproduzido` e `frente` fazem parte do schema mas não são conferidos.

## Comandos

```bash
ac load diagnostico
mkdir -p <work>/.auto-correcao/rounds/<n>
# escrever DEFEITOS.json5
ac defects check          # = defects --min 1 --evidence --classified
ac done diagnostico
```

## Exemplo real

```
$ ac load diagnostico
# etapa diagnostico · rodada 1
objetivo: DEFEITOS.json5 com evidência exata, prioridade e classe
parada: qualidade >= 12/13 nos 3 alvos; zero contornos manuais
orçamento: {'max_hours': 5.0, 'max_parallel': 3, 'max_rounds': 2}
[ ] diagnostico.1 (main) ler notes.md e asserções falhas; reproduzir os P0
[ ] diagnostico.2 (main) classificar: sistema | oraculo | ambiente | executor
handoff anterior:
rodada 0: Q 9/13 sistema, 10/13 baseline

$ ac done diagnostico
NÃO: etapa 'diagnostico' não fecha:
  diagnostico.1: sem $T/campanha/.auto-correcao/rounds/1/DEFEITOS.json5
  diagnostico.2: sem $T/campanha/.auto-correcao/rounds/1/DEFEITOS.json5
[exit 1]

# DEFEITOS com D-1-01 sem evidência e D-1-02 com classe "talvez"
$ ac defects check
NÃO: defeitos sem evidência: ['D-1-01']
[exit 1]

# DEFEITOS corrigido (acima)
$ ac defects check
defeitos ok
$ ac done diagnostico
etapa 'diagnostico' fechada
```

## Erros comuns

- Tratar todo NO-GO como defeito do sistema (L08) — metade vinha do oráculo ou do gerador de provas.
- Evidência vaga ("às vezes falha") em vez de comando + erro literal.
- Ignorar contornos manuais porque "deu certo" — contorno é defeito (`notes_md`).
- Rodada sem nenhum defeito: `--min 1` impede fechar a etapa com DEFEITOS vazio. Se não há defeito e o
  critério não foi cumprido, isso é sinal para decidir (escalar), não para inventar defeito.
