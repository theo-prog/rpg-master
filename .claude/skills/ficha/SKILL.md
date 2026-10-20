---
name: ficha
description: Cria, mostra ou sobe de nível uma ficha de personagem do RPG. Use quando o jogador quiser criar personagem, ver ficha ou evoluir.
---
# Fichas

**Criar** (uma pergunta por vez só se faltar informação; aceite "você escolhe"):
1. Conceito, raça, classe. 2. `rpg.py atributos` (ou array padrão 15,14,13,12,10,8) — o jogador distribui.
3. Calcule com a regra d20 leve: PV = dado de vida máx. + mod CON; CA = 10 + DES (ou armadura); `atk` = proficiência(+2) + mod do atributo da arma; `dano` = dado da arma + mod; 2–4 perícias; 2 resistências da classe.
4. Uma chamada: `rpg.py pj novo <Nome> raca=… classe=… FOR=… DES=… CON=… INT=… SAB=… CAR=… hp=… ca=… atk=… dano=… pericias=a,b resist=X,Y itens=a,b po=… tracos="…" notas="laço/medo/segredo"`.
5. Pergunte UM laço com o mundo (pessoa, dívida ou segredo) e transforme em fio ou lore.

**Mostrar**: `rpg.py ficha <id>` e repasse a saída sem enfeitar.

**Subir de nível**: `rpg.py pj <id> nivel+1 hpmax+<dado médio+CON> hp=<novo max>` + novo traço/magia em `tracos`/`magias`. Proficiência é recalculada pelo motor.
