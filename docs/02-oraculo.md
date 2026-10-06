# 02 — O oráculo

O oráculo é a medida contra a qual o sistema é corrigido: testes, evals com gabarito oculto, gates,
checklist. É a primeira trava da skill: **sem oráculo confiável, não há laço** — autonomia otimiza o que
se mede, e um corretor que mente faz o sistema "melhorar" no placar e piorar na realidade.

Por que isso é a primeira trava: lição **L01** — "O corretor mente com frequência". Evidência: o baseline
dava 1/44 porque o corretor só lia arquivos do próprio sistema; um gate "não medido" por nome de campo
divergente; orçamento de cartão medido de dois jeitos; falsos positivos de negação ("driver" não se usa).

Etapa correspondente: [etapas/oraculo.md](etapas/oraculo.md).

## Achar ou construir

Primeiro procure o que já existe (SKILL.md, `oraculo.1`): suíte de testes, evals, gates do próprio
sistema, checklist. Se não há, construa uma **com gabarito que o sistema nunca vê** (ex.: fixtures com
`GROUND_TRUTH.json` fora do alcance do executor). Registre o comando:

```
$ ac set oracle.command "python3 evals/grader.py <saida> --out grading.json"
ok: oracle.command
```

`oraculo.1` só exige que `oracle.command` exista (`require oracle.command`).

O oráculo deve produzir, por execução, um JSON com o formato que `ac.py run record --grading` lê:

```json
{"summary": {"quality": {"passed": 9, "total": 13}, "structure": {"passed": 22, "total": 40}}}
```

## Calibração

A calibração prova que o oráculo não mente. É feita por um subagente (`ctx: sub`) com o prompt
`verificador_oraculo` de `references/prompts.json5`, resumido:

1. rode o oráculo numa saída **vazia/sem trabalho** — o placar tem de ser ~0;
2. numa saída **boa conhecida** — tem de passar;
3. para cada configuração, escolha **2 asserções** (uma que passou, uma que falhou), abra os arquivos e
   diga se o oráculo acertou;
4. procure **acoplamento a formato** (asserção que só passa se a saída usar a estrutura do próprio
   sistema) e **negação mal lida**;
5. não edite nada; devolva JSON
   `{vazio: {score}, bom: {score}, conferencias: [{assercao, oraculo, correto: bool, evidencia}], acoplamentos: [...], veredito: "confiavel|nao-confiavel"}`.

O orquestrador grava o resultado em `oracle.calibration`:

```bash
ac set oracle.calibration '{"vazio":0.0,"bom":1.0,"configs":2,"conferencias":[
  {"assercao":"q1 sistema","correto":true,"evidencia":"run1/report.md:12"},
  {"assercao":"q2 sistema","correto":true,"evidencia":"run1/report.md:40"},
  {"assercao":"q1 baseline","correto":true,"evidencia":"base1/out.md:7"},
  {"assercao":"q2 baseline","correto":true,"evidencia":"base1/out.md:19"}]}'
```

### O que `chk_calibration` exige exatamente

| Campo | Regra | Mensagem de recusa |
|---|---|---|
| `oracle.calibration` | tem de ser um objeto | `oracle.calibration ausente: ac.py set oracle.calibration '{...}'` |
| `vazio` | número **≤ 0.10** | `saída vazia precisa pontuar ≤0.10 (recebido …)` |
| `bom` | número **≥ 0.90** | `saída boa conhecida precisa pontuar ≥0.90 (recebido …)` |
| `conferencias` | pelo menos **2 × `configs`** itens (`configs` ausente conta como 1) | `conferências à mão: N, mínimo M (2 por configuração)` |
| `conferencias[].correto` | **todas** `true` | `oráculo errou em [...] — corrija via \`oracle change\` e recalibre` |
| `conferencias[].evidencia` | todas preenchidas | `conferências sem evidência: [...]` |

Todas as falhas aparecem juntas, separadas por `;`. Saídas reais da demonstração:

```
$ ac set oracle.calibration '{"vazio":0.3,"bom":1.0,"configs":2,"conferencias":[{"assercao":"a1","correto":true,"evidencia":"out/a.md:3"}]}'
ok: oracle.calibration

$ ac check oraculo.2
NÃO: saída vazia precisa pontuar ≤0.10 (recebido 0.3); conferências à mão: 1, mínimo 4 (2 por configuração)
[exit 1]

$ ac set oracle.calibration '{"vazio":0.0,"bom":1.0,"configs":1,"conferencias":[{"assercao":"cita versao exata","correto":true,"evidencia":"run1/report.md:12"},{"assercao":"nega lib inexistente","correto":false,"evidencia":"run1/report.md:40"}]}'
ok: oracle.calibration

$ ac check oraculo.2
NÃO: oráculo errou em ['nega lib inexistente'] — corrija via `oracle change` e recalibre
[exit 1]
```

Observe o que a regra implica: **uma única conferência em que o oráculo errou bloqueia a etapa**. Não há
"oráculo 90% certo": ou corrige o oráculo (via `oracle change`) e recalibra, ou a campanha não avança.

> Os números de `vazio`, `bom` e o veredito de cada conferência são **declarados** pelo orquestrador via
> `set`; o script confere a coerência, não re-executa o oráculo. A honestidade da calibração depende do
> verificador. Ver [07-limites.md](07-limites.md).

Revalide a calibração quando o sistema mudar o formato de saída (regra de L01).

## Qualidade × estrutura

Lição **L02**: "Separe qualidade (neutra de formato, comparável com baseline) de estrutura (artefatos do
sistema). Misturar infla o ganho." Evidência: o agregado misturado deu +0,56; a qualidade real era +0,23
a +0,31.

- **Qualidade** — asserções que valem para qualquer saída que resolva a tarefa, independentemente do
  formato. Só ela é comparável com o baseline (que não produz os artefatos do sistema).
- **Estrutura** — asserções sobre artefatos próprios do sistema (arquivos, campos, gates internos).
  Baseline costuma dar 0 aqui, e isso não é sinal de que o sistema é melhor.

Registro (`oraculo.3`, `require oracle.split`; o conteúdo é livre, o check só exige que exista):

```
$ ac set oracle.split '{"quality":"13 asserções neutras de formato","structure":"40 asserções de artefatos do sistema"}'
ok: oracle.split
```

A separação reaparece em todo lugar: `run record` grava `quality` e `structure`, `results compare`
mostra as duas colunas e médias separadas, e o relatório ao usuário é sempre "qualidade × estrutura × custo".

## Congelamento por hash

```
$ ac oracle verify
NÃO: oráculo não congelado (ac.py oracle freeze --file ...)
[exit 1]

$ ac oracle freeze --file $T/alvo/evals/grader.py
oráculo congelado: 811352ff8338

$ ac oracle verify
oráculo intacto
```

Como o hash é calculado (`sha_files`): para cada arquivo em ordem alfabética do caminho absoluto, o
SHA-256 acumula o caminho e o SHA-256 do conteúdo. Mudar conteúdo, renomear ou trocar a lista de arquivos
muda o hash. `--file` pode ser repetido; todos os arquivos têm de existir.

Proteções em volta do hash:

```
$ ac set oracle.hash abc
erro: use `oracle freeze` / `oracle change` para o oráculo
[exit 2]

$ ac oracle freeze --file $T/alvo/evals/grader.py      # segunda vez
erro: oráculo já congelado — mudança só por `oracle change --why --evidence`
[exit 2]
```

O hash é conferido em `oraculo.4` e de novo em `integracao.2` (depois que as frentes mexeram no sistema).
O `plan check` também recusa frente que escreve num arquivo do oráculo (ver
[03-frentes-paralelas.md](03-frentes-paralelas.md)).

### Adulteração detectada (saída real)

```
$ echo '# fazer passar' >> $T/alvo/evals/grader.py
$ ac oracle verify
NÃO: oráculo mudou fora de `oracle change` (hash 80b3009a55d7 ≠ congelado 811352ff8338)
[exit 1]
```

## `oracle change` — quando é legítimo

Mudar o oráculo é um evento separado, nunca parte de uma frente de correção (trava 2). É legítimo quando
há **evidência conferida à mão** de que o oráculo erra — por exemplo, um defeito de classe `oraculo` no
diagnóstico, ou uma conferência com `correto: false` na calibração. Não é legítimo para "fazer o sistema
passar".

```
$ ac oracle change --why "fazer passar"
erro: mudar o oráculo exige --why e --evidence (conferência manual que prova o erro do oráculo)
[exit 2]

$ ac oracle change --why "negação lida como afirmação" --evidence "conferido à mão: run1/report.md:40 diz 'não usa X' e o grader contou X"
oráculo recongelado: 80b3009a55d7 (mudança registrada; toda medição anterior deve ser recorrigida)

$ ac oracle verify
oráculo intacto
```

O que acontece:
- recalcula o hash sobre os `--file` passados ou, sem `--file`, sobre os arquivos já congelados;
- acrescenta em `oracle.changes` `{at, why, evidence, from, to, round}` e grava o evento
  `oracle-change` no ledger;
- **toda medição anterior deve ser recorrigida** com o oráculo novo (o script avisa, mas não faz isso:
  você roda o oráculo de novo nas execuções antigas e registra de novo).

Depois de mudar, recalibre (`oraculo.2`).

## Sinais de que o oráculo mente

Tirados de L01, L02, L08 e do prompt `verificador_oraculo`:

- **Saída vazia pontua acima de ~0.** O corretor está premiando forma, não conteúdo.
- **Saída boa conhecida não passa.** Ex.: baseline dando 1/44 porque o corretor só lia arquivos do sistema.
- **Asserção acoplada a formato** — só passa se a saída usar a estrutura do próprio sistema.
- **Negação mal lida** — "X não existe" contado como citação de X (ex.: 'playwright' citado para dizer
  que NÃO existe; 13 respostas certas reprovadas por regex de "nenhum").
- **Nome de campo divergente** — um gate fica "não medido" porque o corretor procura outro nome.
- **A mesma grandeza medida de dois jeitos** em lugares diferentes.
- **Reprovação vinda do ambiente da prova**, não do sistema (ex.: perguntas sobre sha sem `.git` no exame).
- **Ganho agregado muito maior que o ganho em qualidade** — mistura de qualidade com estrutura.

Quando aparecer um desses, classifique o defeito como `oraculo` no diagnóstico (L08: "metade dos NO-GO
vinha do oráculo ou do gerador de provas, não do sistema") e trate via `oracle change`, fora das frentes.
