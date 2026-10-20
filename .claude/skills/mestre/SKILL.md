---
name: mestre
description: Inicia ou retoma a campanha de RPG. Use no começo de cada sessão de jogo ou quando o jogador pedir para jogar/continuar.
---
# Iniciar / retomar sessão

O hook já injetou o contexto `[RPG]`. Não leia arquivos extras.

**Se "Sem campanha"** — Sessão Zero em duas rodadas curtas, sempre oferecendo opções ("ou eu proponho"):
*Rodada 1 (uma mensagem)*: (a) gênero/tom e nome da campanha — ofereça 3 premissas de 1 linha; (b) limites e véus (lembre que "X" pula a cena); (c) letalidade baixa/média/alta.
*Rodada 2*: (d) personagem: conceito + **código de honra** → `/ficha`; (e) 2–3 facções que disputam o mundo (ou "você inventa"), cada uma com meta própria; (f) ritmo preferido (épico / equilibrado / cotidiano) → `/ajustar` se quiser detalhar.
Depois: `rpg.py x "nova \"<Nome>\"; flag tom=…; flag limites=…; flag letalidade=…; flag ritmo=…"` e escreva 3–5 linhas em `campanha/resumo.md` (premissa, tom, gancho inicial). Crie 1 relógio de ameaça, 1 fio e as facções: `faccao "Nome" rep=0 "meta"` (+ 1 relógio por facção ativa). `provisoes =10` se houver viagens.

**Se a campanha existe**:
1. "Anteriormente…" em 2–3 frases, a partir de RESUMO + ÚLTIMOS.
2. Se `campanha/prep.md` tiver conteúdo, leia-o UMA vez (é a prep da sessão).
3. Comece *in media res* (início forte, 200–350 palavras): escala do mundo, 3–4 detalhes sensoriais, algo acontecendo agora, e termine em "O que você faz?". Se a sessão anterior terminou em clímax, abra com um respiro cotidiano antes do próximo gancho.
