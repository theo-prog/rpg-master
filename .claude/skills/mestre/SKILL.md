---
name: mestre
description: Inicia ou retoma a campanha de RPG. Use no começo de cada sessão de jogo ou quando o jogador pedir para jogar/continuar.
---
# Iniciar / retomar sessão

O hook já injetou o contexto `[RPG]`. Não leia arquivos extras.

**Se "Sem campanha"** — Sessão Zero, curta (no máximo 5 perguntas numa mensagem só):
1. Gênero/tom (ex.: fantasia sombria, aventura leve, horror, sci-fi) e nome da campanha.
2. Limites e véus (temas proibidos / só fora de cena). Lembre que "X" a qualquer momento pula a cena.
3. Conceito do personagem em 1 frase **e seu código de honra** (o que ele jamais faz / jura cumprir) → depois rode `/ficha`.
3b. Poderes do mundo: 2–3 facções (ou "você inventa"), cada uma com meta própria.
4. Nível de letalidade (baixo/médio/alto) → grave com `flag letalidade=…`.
Depois: `rpg.py x "nova \"<Nome>\"; flag tom=…; flag limites=…"` e escreva 3–5 linhas em `campanha/resumo.md` (premissa, tom, gancho inicial). Crie 1 relógio de ameaça, 1 fio e as facções: `faccao "Nome" rep=0 "meta"` (+ 1 relógio por facção ativa).

**Se a campanha existe**:
1. "Anteriormente…" em 2–3 frases, a partir de RESUMO + ÚLTIMOS.
2. Se `campanha/prep.md` tiver conteúdo, leia-o UMA vez (é a prep da sessão).
3. Comece *in media res* (início forte, 200–350 palavras): escala do mundo, 3–4 detalhes sensoriais, algo acontecendo agora, e termine em "O que você faz?". Se a sessão anterior terminou em clímax, abra com um respiro cotidiano antes do próximo gancho.
