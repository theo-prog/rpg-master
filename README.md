# rpg-master

Transforma o Claude Code num **Mestre de RPG** para campanhas longas, gastando o mínimo de tokens por resposta. Pensado para o **Opus 5.5** (narração rica), com o raciocínio caro empurrado para fora dos turnos de jogo.

## Como jogar
```bash
cd rpg-master
claude            # o hook injeta o estado da campanha automaticamente
> /mestre         # sessão zero (1ª vez) ou retomar
> /ficha          # criar personagem
...jogue...
> /salvar         # fim da sessão: compacta a memória e salva snapshot
> /preparar       # (opcional) prep da próxima sessão, effort alto
> /clear          # começa a próxima sessão com contexto limpo
```

## Primeira sessão em 5 minutos
1. `claude` na pasta e `/mestre`: responda a sessão zero (tom, limites, letalidade; depois personagem, **código de honra** e facções). Pode dizer "você escolhe" em qualquer pergunta.
2. `/ficha` → "caminho rápido": escolha uma classe e o motor monta o herói inteiro.
3. Jogue em prosa: diga o que o personagem **tenta**, não o resultado ("tento convencer o guarda de que somos peregrinos"). Fora do jogo: `(entre parênteses)` ou `ooc:`. "X" pula uma cena.
4. Se algo saiu errado no estado (PV, item, rolagem mal lida), peça `desfazer`.
5. Mais combate, mais intriga ou mais respiro? `/ajustar`. Fim da sessão: `/salvar`, depois `/diario` (crônica) e `/preparar`.

## Peças
| Arquivo | Papel |
|---|---|
| `CLAUDE.md` | Núcleo do mestre (~1k tok, estável → cache): loop, honra/facções, estilo épico+cotidiano |
| `tools/rpg.py` | Motor determinístico: dados, fichas, testes, combate, relógios, **honra**, **facções**, oráculo, lore, saves (só stdlib) |
| `.claude/settings.json` | Opus 5.5, `effortLevel: low`, compactação em 100k, hook `SessionStart` → `rpg.py boot` |
| `.claude/skills/*` | `/mestre`, `/ficha`, `/combate`, `/preparar` (effort high), `/salvar`, `/diario`, `/ajustar` — carregadas só quando usadas |
| `campanha/` | Estado da campanha (criado por `rpg.py nova`) |
| `docs/ARQUITETURA.md` | Traços de um bom mestre → mecanismos; hierarquia de memória; modelo de pensamento e custos |

## Motor — exemplos
```bash
python3 tools/rpg.py ajuda
python3 tools/rpg.py x "teste kael furtividade 15 vant; relogio Guarda +1; log Kael entrou no cofre"
python3 tools/rpg.py x 'combate inicio "Goblinx3:ca13:hp2d6:atk4:dano1d6+2:des2"; ataque kael goblin1'
python3 tools/rpg.py oraculo improvavel
python3 tools/rpg.py x 'honra kael +1 "poupou o prisioneiro"; faccao "Guarda Cinzenta" rep-1 "quer a coroa"'
```
Mais comandos: `heroi` (8 classes prontas), `recurso`/`descanso`/`cura`/`morte`/`subir` (progressão), `honra`/`faccao`/`npc`/`feito` (mundo social), `nome`/`encontro`/`rumor`/`clima`/`viagem`/`provisoes`/`monstro` (tabelas e bestiário), `mover` (zonas de combate), `desfazer` (até 8 níveis). Combate: `ataque a b man=poderoso`, `furtivo`, `combate inicio "@soldadox3n2"`.

Sistema padrão: d20 leve compatível com regras estilo 5e (atributos, perícias, resistências, proficiência por nível). `RPG_DIR` muda a pasta da campanha.

Testes: `python3 -m unittest discover -s tests`
