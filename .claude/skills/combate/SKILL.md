---
name: combate
description: Protocolo de combate tático do RPG (iniciativa, ataques, PV, turnos). Use quando uma luta começar.
---
# Combate

**Abrir** (uma chamada): bestiário pronto com atalho `@tipoxQTDnNÍVEL`, ex.: `rpg.py combate inicio "@soldadox3n2" "@chefen3"` (tipos: `rpg.py monstro`; nível ≈ nível do grupo). Custom: `"Nome[xQtd]:caN:hpN|XdY:atkN:danoXdY+Z:desN[:dist][:zonafundo]"` (`dist` = ataca à distância).
**Posição**: todos começam na zona `meio`; para um campo mais tático use `mover <nome> frente|meio|fundo|alto…`. Corpo a corpo exige a mesma zona (o motor avisa); ataque `dist` alcança qualquer zona. Descreva o terreno de acordo.
Descreva o campo de batalha em 80–150 palavras: escala, luz, som e 1–2 elementos táticos (cobertura, altura, perigo, terreno que muda). Dê ao inimigo principal uma presença antes do primeiro golpe.

**Turno de PJ**: espere a declaração. Resolva com `ataque <pj> <alvo> [vant|desv] [man=poderoso|certeiro|finalizar] [furtivo]` ou `teste` (condições como Envenenado/Amedrontado/Inspirado já aplicam vantagem/desvantagem). Manobras: poderoso (-3 atk, +5 dano), certeiro (+3 atk, -2 dano), finalizar (alvo ≤ metade dos PV: +2 atk, dados dobrados). Ofereça manobras ao descrever opções do herói. Narre 60–120 palavras: o gesto, o impacto (som, peso, dor), o terreno e a reação do alvo. Crítico/falha crítica = quadro cinematográfico. Turno rotineiro de lacaio pode ser 1–2 frases; o foco é o herói e o inimigo importante.
**Turnos de inimigos**: resolva TODOS até o próximo PJ numa só chamada: `rpg.py x "ataque goblin1 kael; turno; ataque lobo mira; turno"`. Narre-os num único parágrafo vivo (60–150 palavras) com o dano de cada um visível. Inimigos agem com inteligência e motivação; podem fugir/render-se com metade dos PV ou o líder caído.
**PJ a 0 PV**: fica Caído — a cada turno dele `rpg.py morte <pj>` (10+ sucesso; 3 sucessos estabiliza, 3 falhas morre) ou consequência narrativa conforme `flag letalidade`. Cura (`cura <pj> 1d8+3`) levanta o PJ. Mortes são cenas: honre o personagem.
**Honra em combate**: poupar quem se rende, proteger inocentes ou quebrar o código do PJ mexe em `honra`; facção dos inimigos/testemunhas mexe em `faccao`.
**Fechar**: um parágrafo de eco (silêncio, fumaça, o preço pago) antes do respiro. `rpg.py x "combate fim; pj <id> xp+N; log <resultado em 1 linha>"`. Saque relevante → `pj <id> item+…`.
