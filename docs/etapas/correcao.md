# Etapa `correcao`

**Objetivo** (`ciclo.json5`): cada defeito de classe sistema com teste que falha antes e passa depois.

Rodada: repete (`per_round`). Anterior: [plano](plano.md). Próxima: [integracao](integracao.md).
Guia completo: [03-frentes-paralelas.md](../03-frentes-paralelas.md).

## Por que existe

- **L10** — "Cada defeito ganha teste que falha antes e passa depois; o integrador roda tudo nos runtimes
  suportados."
- **L06** — "lotes ≤3; espere o lote; cada subagente grava só o próprio arquivo; o orquestrador grava o
  estado em série."
- **L07** — lote em primeiro plano elimina devoluções de controle a cada lote.

## Sub-etapas

| ID | ctx | O que fazer | Check | Recusa quando |
|---|---|---|---|---|
| `correcao.1` | sub | despachar frentes (prompt em `prompts.json5`) e coletar relatórios | `fronts --reported` | alguma frente do PLANO sem `rounds/<n>/fronts/<nome>.md` |

O check só exige que o arquivo de relatório exista; o conteúdo não é lido.

## Despacho

- Um subagente `general-purpose` por frente, com o prompt `frente_correcao` preenchido: `{sistema}`,
  `{plano_path}`, `{frente}`, `{defeitos_path}`, `{escreve}`, `{oraculo_files}`, `{runtimes}`.
- Frentes longas podem rodar em segundo plano; lotes curtos, em primeiro plano, ≤3 (SKILL.md).
- Cada frente: reproduz → teste que **falha** → corrige → teste **passa** → roda as suítes do seu escopo em
  todos os runtimes → relatório curto (defeito → teste → correção; suítes; pendências).
- Nenhuma frente toca arquivo de outra nem o oráculo; nenhuma roda git.
- Se uma frente achar que o oráculo está errado, registra no relatório com evidência — quem decide é o
  orquestrador, via `oracle change`.

## Comandos

```bash
ac load correcao
# despachar frentes; salvar o relatório de cada uma num arquivo
ac front report <nome-da-frente> --file <relatorio.md>     # uma por frente
ac done correcao
```

## Artefatos

`rounds/<n>/fronts/<nome>.md` — cópia do relatório de cada frente.

## Exemplo real

```
$ ac done correcao
NÃO: etapa 'correcao' não fecha:
  correcao.1: frentes sem relatório: ['frente-scan', 'frente-docs'] (ac.py front report <nome> --file ...)
[exit 1]

$ ac front report frente-scan --file $T/rel-scan.md
relatório da frente frente-scan registrado
$ ac front report frente-docs --file $T/rel-docs.md
relatório da frente frente-docs registrado

$ ac done correcao
etapa 'correcao' fechada
```

Conteúdo do relatório usado (`rel-scan.md`):

```
D-1-01 → tests/test_scan.py::test_files_key (falhava, passa) → src/app.py
suítes: 12 ok
```

## Erros comuns

- Teste escrito depois da correção, que nunca foi visto falhando — não prova que pega o defeito.
- Redespachar uma frente antes de a primeira devolver (L06: duplicata sobrescreve trabalho).
- Mais de 3 frentes simultâneas (429, limite de sessão).
- Frente que "aproveita" e edita arquivo fora do `escreve` — o script não impede; a integração precisa
  conferir o diff contra os globs.
- Registrar relatório vazio só para passar o check — o check não lê o conteúdo, mas a integração e a
  decisão dependem dele.
