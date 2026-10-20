---
name: combate
description: Protocolo de combate tático do RPG (iniciativa, ataques, PV, turnos). Use quando uma luta começar.
---
# Combate

**Abrir** (uma chamada): `rpg.py combate inicio "Nome[xQtd]:caN:hpN|XdY:atkN:danoXdY+Z:desN" …`
Referência rápida de inimigos: capanga ca12 hp2d6 atk3 dano1d6+1 · soldado ca15 hp2d8+2 atk4 dano1d8+2 · bruto ca12 hp4d10+8 atk5 dano2d6+3 · chefe ca16 hp8d10+16 atk7 dano2d8+4. Ajuste ao nível do grupo.
Descreva o campo de batalha em 2–3 frases com 1 elemento tático (cobertura, altura, perigo).

**Turno de PJ**: espere a declaração. Resolva com `ataque <pj> <alvo> [vant|desv]` ou `teste`. Narre 1–3 frases.
**Turnos de inimigos**: resolva TODOS até o próximo PJ numa só chamada: `rpg.py x "ataque goblin1 kael; turno; ataque lobo mira; turno"`. Inimigos agem com inteligência e motivação; podem fugir/render-se com metade dos PV ou o líder caído.
**PJ a 0 PV**: fica Caído — testes de morte `rpg.py rolar 1d20` (10+ sucesso; 3 de cada) ou consequência narrativa conforme `flag letalidade`.
**Fechar**: `rpg.py x "combate fim; pj <id> xp+N; log <resultado em 1 linha>"`. Saque relevante → `pj <id> item+…`.
