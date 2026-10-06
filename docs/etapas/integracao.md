# Etapa `integracao`

**Objetivo** (`ciclo.json5`): todas as suítes verdes, contratos alinhados, commit com portão.

Rodada: repete (`per_round`). Anterior: [correcao](correcao.md). Próxima: [remedicao](remedicao.md).

## Por que existe

- **L10** — "regressões apareceram só em Python 3.9 (doctest) e foram pegas na integração." Regra:
  "integração roda todas as suítes em todas as versões."
- **L09** — frentes paralelas divergem em nomes; é aqui que o contrato é reconciliado.
- Trava 2 (oráculo intacto depois das frentes) e trava 3 (commit/push é portão humano).

## Sub-etapas

| ID | ctx | O que fazer | Check | Recusa quando |
|---|---|---|---|---|
| `integracao.1` | main | rodar TODAS as suítes em todos os runtimes suportados | `require integration.tests_green` | `integration.tests_green` ausente/vazio |
| `integracao.2` | main | oráculo intacto (hash) — mudanças só via `oracle change` | `oracle verify` | hash diferente do congelado; arquivo sumiu |
| `integracao.3` | user | commit/push com portão humano ou autorização prévia | `gate-ok commit` | portão `commit` não aprovado e sem `preauth.commit` |

`integration.tests_green` é **declarado** pelo orquestrador com `set` depois de rodar as suítes; o
script não roda testes. `round new` apaga essa chave, então cada rodada precisa declará-la de novo.

## Comandos

```bash
ac load integracao
# rodar todas as suítes em todos os runtimes; reconciliar contrato; pontas soltas
ac set integration.tests_green true
ac oracle verify
ac gate commit --by <humano> --decision approve [--simulated]
#   ou, se o usuário autorizou o commit de antemão:
ac preauth commit --by <humano> --requires integracao.1 integracao.2   # só no terminal do founder, com a frase
ac done integracao
```

## Exemplo real

```
$ ac done integracao
NÃO: etapa 'integracao' não fecha:
  integracao.1: faltando: integration.tests_green
  integracao.3: portão 'commit' não aprovado
[exit 1]

$ ac set integration.tests_green true
ok: integration.tests_green

$ ac gate commit --by founder --decision approve --simulated --note "eval: aprovação simulada"
portão commit: approve por founder (simulado)

$ ac oracle verify
oráculo intacto

$ ac done integracao
etapa 'integracao' fechada
```

## Erros comuns

- Declarar `tests_green` rodando só as suítes de uma frente ou só um runtime.
- Commitar antes do portão — o `ac.py` não roda git e não impede; o portão é o registro da autorização.
- Aprovação simulada não declarada no relatório (L13).
- Achar que o portão `commit` vale só para esta rodada: ele **persiste** entre rodadas (o `round new` não
  limpa `gates`), então `integracao.3` da rodada seguinte já passa. Se cada commit precisa de nova
  autorização, registre o portão de novo e confira a data em `gates.commit.at`.
- Oráculo alterado por uma frente: `oracle verify` recusa; descubra qual frente o tocou antes de qualquer
  `oracle change`.
