---
name: ficha
description: Cria, mostra ou sobe de nível uma ficha de personagem do RPG. Use quando o jogador quiser criar personagem, ver ficha ou evoluir.
---
# Fichas

**Criar — caminho rápido (padrão)**: `rpg.py heroi` lista as classes (guerreiro, ladino, mago, clérigo, patrulheiro, bardo, paladino, bárbaro). Ofereça 3–4 conceitos prontos ("quem você quer ser?"), pergunte nome, raça (só texto) e **código de honra**, e crie numa chamada:
`rpg.py heroi <Nome> <classe> raca=… codigo="…" notas="laço/medo/segredo"` — o motor distribui o array padrão, calcula PV, CA, ataque, dano, perícias, recursos e traços. Se o jogador quiser outro atributo mais alto, `rpg.py pj <id> FOR=… DES=…` (recalcule PV/CA/atk com o motor se mudar CON/DES).

**Criar — manual (classe fora da lista)**: `rpg.py atributos` ou array 15,14,13,12,10,8; PV = dado de vida máx. + mod CON; CA = 10 + DES (ou armadura); `atk` = prof(+2) + mod; `dano` = dado + mod. Uma chamada: `rpg.py pj novo <Nome> raca=… classe=… FOR=… hp=… ca=… atk=… dano=… pericias=a,b resist=X,Y itens=a,b tracos="…" codigo="…" notas="…"`; recursos com `recurso <id> slots max=2 l`.

**Sempre depois**: pergunte UM laço com o mundo (pessoa, dívida, segredo ou facção) e transforme em `npc`, `faccao`, `fio` ou `lore +`.

**Honra**: `rpg.py honra <id> ±N "motivo"` (-5..+5). Em nível novo, pergunte se o código do PJ mudou.

**Mostrar**: `rpg.py ficha <id>` e repasse a saída sem enfeitar.

**Subir de nível**: quando `pj xp+N` avisar "pode subir", rode `rpg.py subir <id>` (PV, proficiência e +1 slot automáticos) e peça um novo traço/magia → `pj <id> tracos=…`. **Descanso**: `rpg.py descanso curto|longo`. **Usos limitados**: `recurso <id> nome -1`.
