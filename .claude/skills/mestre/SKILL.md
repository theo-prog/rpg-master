---
name: mestre
description: Inicia ou retoma a campanha de RPG. Use no começo de cada sessão de jogo ou quando o jogador pedir para jogar/continuar.
---
# Iniciar / retomar sessão

O hook já injetou o contexto `[RPG]`. Não leia arquivos extras.

**Se "Sem campanha"** — Sessão Zero, curta (no máximo 4 perguntas numa mensagem só):
1. Gênero/tom (ex.: fantasia sombria, aventura leve, horror, sci-fi) e nome da campanha.
2. Limites e véus (temas proibidos / só fora de cena). Lembre que "X" a qualquer momento pula a cena.
3. Conceito do personagem em 1 frase → depois rode `/ficha`.
4. Nível de letalidade (baixo/médio/alto) → grave com `flag letalidade=…`.
Depois: `rpg.py x "nova \"<Nome>\"; flag tom=…; flag limites=…"` e escreva 3–5 linhas em `campanha/resumo.md` (premissa, tom, gancho inicial). Crie 1 relógio de ameaça e 1 fio.

**Se a campanha existe**:
1. "Anteriormente…" em 2–3 frases, a partir de RESUMO + ÚLTIMOS.
2. Se `campanha/prep.md` tiver conteúdo, leia-o UMA vez (é a prep da sessão).
3. Comece *in media res* (início forte): uma cena com algo acontecendo agora, um detalhe sensorial, e termine em "O que você faz?".
