# Campanhas da auto-correcao

Cada frente de desenvolvimento é uma campanha da própria auto-correcao, orquestrada pelo ac.py ESTÁVEL
(`local/ac-estavel/`, nunca o `scripts/ac.py` em edição). Aqui fica só o que prova a entrega e pode ser publicado:
o oráculo (`oraculo/`: testes, `ESPEC.md`, `base.txt` = a medição que falhava antes, `mudanca-oficial/` quando
houver). Ficam FORA do repositório (`.gitignore`): o ledger e o estado (`<campanha>/.auto-correcao/`) e os
`aprovar-*.sh` — têm caminhos e tags de aprovação da máquina onde a campanha rodou.

| Campanha | O quê | Commit de entrega (repo de origem) | Decisão |
|---|---|---|---|
| `ac-v03` | AC-01 remedição aceitava a execução da base; AC-02 status com etapa velha; AC-03 execução com total de qualidade diferente da base; AC-04 aprovação humana forjável por `--by` (tty + desafio, hook global); L17 campanhas sobrepostas (`overlap`) | `5800ed2` (v0.3) | GO — parar: critério atingido (oráculo 27/27, test_ac 22/22 em 3.13 e 3.9, hook selftest 63/63, nenhuma função removida) |
| `ac-v04` | aprovação humana por FRASE-SENHA do founder (tag HMAC por aprovação, `frase conferir`), legado `--assinar-legado`, AC-06 scope com vírgula; mudança oficial seguinte aceita senha forte além de frase | `6e5dc67` (v0.4); `797dc3d` (v0.4.1, mudança oficial) | GO — parar: critério atingido (98 testes nos 2 Pythons, hook selftest 83/83, nada removido) |

Notas:
- Os commits de entrega são do repositório onde a skill morava antes de virar projeto; o primeiro commit deste
  projeto ("auto-correcao v0.4.1 — projeto completo de desenvolvimento") já contém o resultado das duas.
- Os oráculos são históricos: testam a skill pelo caminho instalado (`~/.claude/skills/auto-correcao`). As versões
  integradas na suíte (`scripts/tests/test_v03_oraculo.py`, `test_v04_frase.py`) testam a skill onde estão.
- `ac-v04/oraculo/test_v04_frase.py` teve só o usuário de fixture trocado por "ana" (privacidade); o hash congelado
  no ledger original não confere mais com esta cópia — por isso ela não serve para reabrir aquela campanha.
