# Etapa `oraculo`

**Objetivo** (`ciclo.json5`): medida existente ou construída, calibrada e congelada por hash.

Rodada: 0 (não repete). Anterior: [intake](intake.md). Próxima: [base](base.md).
Guia completo: [02-oraculo.md](../02-oraculo.md).

## Por que existe

- **L01** — "O corretor mente com frequência. Antes de confiar num número, confira à mão uma amostra e
  rode uma saída vazia."
- **L02** — "Separe qualidade (neutra de formato, comparável com baseline) de estrutura (artefatos do
  sistema). Misturar infla o ganho."
- Trava 1 do SKILL.md: sem oráculo confiável, não há laço. Trava 2: quem corrige o sistema não corrige o
  oráculo — por isso o congelamento.

## Sub-etapas

| ID | ctx | O que fazer | Check | Recusa quando |
|---|---|---|---|---|
| `oraculo.1` | main | localizar ou construir o oráculo (testes, evals com gabarito oculto, gates) | `require oracle.command` | `oracle.command` ausente |
| `oraculo.2` | sub | calibrar: saída vazia ≈0, saída boa conhecida passa, ≥2 asserções/config conferidas à mão | `calibration` | vazio > 0.10; bom < 0.90; < 2×configs conferências; alguma `correto: false`; alguma sem `evidencia` |
| `oraculo.3` | main | separar qualidade (neutra de formato) de estrutura (artefatos próprios) | `require oracle.split` | `oracle.split` ausente |
| `oraculo.4` | main | congelar (hash dos arquivos do oráculo) | `oracle verify` | não congelado; arquivo sumiu; hash mudou |

`oraculo.2` é `sub`: despache um subagente com o prompt `verificador_oraculo` (`references/prompts.json5`),
que não edita nada e devolve JSON com `vazio`, `bom`, `conferencias`, `acoplamentos`, `veredito`.

## Comandos

```bash
ac load oraculo
ac set oracle.command "<comando do oráculo>"
ac set oracle.calibration '{"vazio":0.0,"bom":1.0,"configs":2,"conferencias":[{"assercao":"...","correto":true,"evidencia":"arq:linha"}, ...]}'
ac check oraculo.2
ac set oracle.split '{"quality":"...","structure":"..."}'
ac oracle freeze --file <arquivo do oráculo> [--file ...]
ac done oraculo --handoff "..."
```

## Artefatos

`state.json`: `oracle.command`, `oracle.calibration`, `oracle.split`, `oracle.files`, `oracle.hash`,
`oracle.frozen_at` (e `oracle.changes` se houver `oracle change`).

## Exemplo real

```
$ ac load base
NÃO: etapa 'oraculo' não fechou — conclua-a antes (ac.py load oraculo)
[exit 1]

$ ac set oracle.command "python3 evals/grader.py <saida> --out grading.json"
ok: oracle.command

$ ac done oraculo
NÃO: etapa 'oraculo' não fecha:
  oraculo.2: oracle.calibration ausente: ac.py set oracle.calibration '{"vazio":0.0,"bom":1.0,"conferencias":[{"assercao":"...","correto":true,"evidencia":"arq:linha"}],"configs":2}'
  oraculo.3: faltando: oracle.split
  oraculo.4: oráculo não congelado (ac.py oracle freeze --file ...)
[exit 1]

$ ac set oracle.calibration '{"vazio":0.3,"bom":1.0,"configs":2,"conferencias":[{"assercao":"a1","correto":true,"evidencia":"out/a.md:3"}]}'
ok: oracle.calibration
$ ac check oraculo.2
NÃO: saída vazia precisa pontuar ≤0.10 (recebido 0.3); conferências à mão: 1, mínimo 4 (2 por configuração)
[exit 1]

$ ac set oracle.calibration '{"vazio":0.0,"bom":1.0,"configs":2,"conferencias":[{"assercao":"q1 sistema","correto":true,"evidencia":"run1/report.md:12"},{"assercao":"q2 sistema","correto":true,"evidencia":"run1/report.md:40"},{"assercao":"q1 baseline","correto":true,"evidencia":"base1/out.md:7"},{"assercao":"q2 baseline","correto":true,"evidencia":"base1/out.md:19"}]}'
ok: oracle.calibration
$ ac check oraculo.2
ok: oraculo.2

$ ac set oracle.split '{"quality":"13 asserções neutras de formato","structure":"40 asserções de artefatos do sistema"}'
ok: oracle.split

$ ac oracle freeze --file $T/alvo/evals/grader.py
oráculo congelado: 811352ff8338
$ ac oracle verify
oráculo intacto

$ ac done oraculo
etapa 'oraculo' fechada
```

Adulteração e mudança legítima: ver [02-oraculo.md](../02-oraculo.md#adulteração-detectada-saída-real).

## Erros comuns

- Confiar no número do oráculo sem calibrar ("o grader.py diz 20% e eu acho que está errado" — eval 3 da
  skill: a calibração detecta, o defeito é classe `oraculo`, a mudança vai por `oracle change`).
- `configs` subestimado para precisar de menos conferências: com sistema + baseline são 2 configurações,
  logo ≥4 conferências.
- Conferência só de asserções que passaram — o prompt pede uma que passou e uma que falhou por config.
- Congelar antes de calibrar e depois precisar corrigir: aí é `oracle change --why --evidence`, não
  um novo `freeze` (que é recusado).
- Esquecer arquivos auxiliares do oráculo (gabarito, fixtures, regex) no `freeze`: só o que está em
  `--file` é protegido pelo hash e pelo `plan check`.
