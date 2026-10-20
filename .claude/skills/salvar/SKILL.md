---
name: salvar
description: Encerra a sessão de RPG compactando a memória da campanha e salvando snapshot. Use ao fim da sessão ou quando o boot pedir.
---
# Encerrar sessão (compactação de memória)

1. Atualize `campanha/resumo.md` com Edit, integrando os eventos do log desta sessão:
   - Mantenha o cabeçalho (premissa/tom). Seção `## Arco` com 1 parágrafo por sessão ANTIGA comprimido para 1–2 frases; a sessão atual ganha até 4 frases.
   - Seção `## Canon` só com fatos que ainda importam (promessas, inimigos, segredos revelados). Remova o que foi resolvido.
   - Teto: ~450 palavras no arquivo todo. Se passar, comprima as sessões mais antigas.
2. Feche ou adicione fios/relógios conforme a sessão. Registre 1–3 momentos marcantes com `rpg.py feito "…"` (para o `/diario`).
3. `rpg.py x "compactar; salvar fim"`
4. Diga ao jogador, em 1–2 linhas: o gancho para a próxima sessão e a sugestão de `/clear` (o estado está todo em disco; começar limpo reduz o custo de cada turno). Ofereça `/diario` (crônica da sessão) e `/preparar`.
