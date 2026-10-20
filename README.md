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

## Peças
| Arquivo | Papel |
|---|---|
| `CLAUDE.md` | Núcleo do mestre (~600 tok, estável → cache) |
| `tools/rpg.py` | Motor determinístico: dados, fichas, testes, combate, relógios, oráculo, lore, saves (só stdlib) |
| `.claude/settings.json` | Opus 5.5, `effortLevel: low`, compactação em 100k, hook `SessionStart` → `rpg.py boot` |
| `.claude/skills/*` | `/mestre`, `/ficha`, `/combate`, `/preparar` (effort high), `/salvar` — carregadas só quando usadas |
| `campanha/` | Estado da campanha (criado por `rpg.py nova`) |
| `docs/ARQUITETURA.md` | Traços de um bom mestre → mecanismos; hierarquia de memória; modelo de pensamento e custos |

## Motor — exemplos
```bash
python3 tools/rpg.py ajuda
python3 tools/rpg.py x "teste kael furtividade 15 vant; relogio Guarda +1; log Kael entrou no cofre"
python3 tools/rpg.py x 'combate inicio "Goblinx3:ca13:hp2d6:atk4:dano1d6+2:des2"; ataque kael goblin1'
python3 tools/rpg.py oraculo improvavel
```
Sistema padrão: d20 leve compatível com regras estilo 5e (atributos, perícias, resistências, proficiência por nível). `RPG_DIR` muda a pasta da campanha.

Testes: `python3 -m unittest discover -s tests`
