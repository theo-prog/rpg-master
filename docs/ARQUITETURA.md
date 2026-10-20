# Arquitetura — Mestre de RPG de baixo custo no Claude Code (Opus 5.5)

## 1. O que faz um bom mestre — e como cada traço vira mecanismo

| Traço do bom mestre | Risco num LLM | Mecanismo no projeto |
|---|---|---|
| **Continuidade** (lembra de nomes, promessas, ferimentos) | Esquece ou inventa ao longo de sessões | Estado em disco (`campanha/`), canon registrado na hora (`lore +`, `log`), resumo rolante |
| **Dados justos e transparentes** | Modelo "escolhe" resultados dramáticos, erra conta | Todo número sai de `rpg.py`; resultado mostrado em uma linha 🎲 |
| **Agência do jogador** | Narra o que o PJ faz/sente | Regra explícita no núcleo; turno sempre termina numa escolha |
| **Rolar só quando importa** | Rola para tudo, ou nunca | Passo 2 do loop: incerteza **e** consequência |
| **Falhar para frente** | Falha = beco sem saída | Passo 3: falha avança com complicação |
| **Mundo vivo** | Mundo congela fora de cena | Relógios de facção/perigo (estilo *Blades in the Dark*) |
| **NPCs memoráveis** | NPCs genéricos e iguais | Fórmula desejo + tique + voz, guardada em 1 linha de lore |
| **Ritmo e foco** | Paredes de texto, resumos, menus | Teto de palavras por tipo de turno; sem listas na narração |
| **Mistérios solucionáveis** | Pista única perdida trava a trama | Regra das 3 pistas; "segredos e pistas" soltos na prep |
| **Preparar situações, não roteiros** | Trilhos ou improviso caro | `/preparar` no método do *Mestre Preguiçoso* (8 passos) |
| **Telegrafar perigo / letalidade combinada** | Mortes "injustas" | `flag letalidade`, aviso antes de punir |
| **Segurança à mesa** | Conteúdo indesejado | Sessão zero com limites e véus; "X" pula cena |
| **Abrir forte, fechar com gancho** | Começos mornos | `/mestre` abre *in media res*; `/salvar` fecha com gancho |

## 2. Hierarquia de memória (o que entra no contexto e quando)

```
L0 Núcleo   CLAUDE.md (~700 tok)            sempre; estável → fica em cache
L1 Boot     hook SessionStart → rpg.py boot  1×/sessão (~200–900 tok): cena, resumo, fichas, fios, relógios
L2 Sob demanda  rpg.py lore <id>, ficha <id>, prep.md   só quando a cena pede
L3 Arquivo  arquivo/S<n>.md, .saves/         nunca relido pelo modelo
Skills      /mestre /ficha /combate /preparar /salvar  — só a descrição fica no contexto até serem chamadas
```

Princípio: **o contexto é descartável, o estado é durável.** Como tudo que importa está em disco, `/clear` entre sessões não perde nada — e o hook re-injeta o boot também após `/clear` e após compactação automática.

A memória de longo prazo é um **resumo rolante com teto** (~450 palavras): a cada `/salvar` as sessões antigas são recomprimidas (sessão recente 4 frases → antigas 1–2 frases). O custo de lembrar a campanha fica constante, seja na sessão 3 ou na 80.

## 3. Modelo de pensamento (custo por resposta)

### 3.1 Por que é o lever certo no Opus 5.5
- Preço: **$4/M entrada, $20/M saída, $0,20/M leitura de cache**. Saída (inclui o raciocínio) custa 5× a entrada e 100× a leitura de cache. → **O que mais custa é pensar e escrever demais.**
- No Opus 5.5 o raciocínio **não pode ser desligado**; o controle é o `effort` (padrão `medium`). O projeto fixa `effortLevel: "low"` em `.claude/settings.json` — o raciocínio adaptativo ainda aprofunda sozinho quando o turno é difícil.
- Contexto acumulado é relido (do cache) a cada chamada. A 100k tokens isso é ~$0,02 por chamada; por isso `autoCompactWindow: 100000` e `/clear` a cada sessão.

### 3.2 "Pensar caro uma vez, narrar barato sempre"
O raciocínio caro é **movido para fora do turno**:

| Momento | Effort | O que pensa | Frequência |
|---|---|---|---|
| `/preparar` | high (frontmatter da skill) | Segredos, cenas, NPCs, ameaças → `prep.md` + lore | 1× entre sessões |
| Turno de jogo | low | Só o loop de 5 passos, consultando a prep | toda mensagem |
| `/salvar` | low | Compressão do resumo | 1× por sessão |

Durante o jogo, a criatividade "pesada" já está pronta na prep; o turno só **seleciona e encena**.

### 3.3 O loop de 5 passos (andaime de raciocínio)
Em vez de deliberação aberta, o núcleo impõe um checklist curto — Intenção → Rolagem? → Consequência → Mundo reage → Narre e devolva. Cada passo tem resposta de poucas palavras. Decisões que um mestre humano tomaria "no feeling" viram **chamadas baratas e determinísticas**:

- Números, acerto, dano, PV, iniciativa → `rpg.py` (o modelo nunca faz conta no raciocínio).
- "O guarda sabe disso?" → `oraculo`; "Como o NPC reage?" → `oraculo reacao`.
- "O culto age?" → `relogio`.

### 3.4 Classes de turno e orçamento de saída

| Classe | Exemplo | Ferramenta | Narração |
|---|---|---|---|
| T0 Fora do jogo | "quanto de PV eu tenho?" | 0–1 chamada | ≤ 40 palavras, sem narrar |
| T1 Ação simples / diálogo | conversar, andar, olhar | 0–1 | 60–120 palavras |
| T2 Ação arriscada / combate | furtar, atacar | 1 chamada em lote | 1–3 frases por ação |
| T3 Cena-chave | revelação, chegada, clímax | 0–1 | até ~250 palavras |

### 3.5 Higiene de ferramentas
- **Uma chamada por turno**: `rpg.py x "cmd1; cmd2; cmd3"`. Cada chamada extra é mais uma ida ao modelo (com seu próprio raciocínio e saída).
- Saídas do motor são telegráficas (`Kael Furtividade d20(14)+5=19 vs CD15 ✓`): cada caractere de resultado vira token de entrada pelo resto da sessão.
- Nunca reler arquivo que o boot já trouxe; lore só por id.

### 3.6 Estimativa (ordem de grandeza, por turno)

| | Sem arquitetura | Com arquitetura |
|---|---|---|
| Raciocínio | 1–3k (contas, deliberação, effort medium) | 100–400 (effort low, loop curto) |
| Narração | 300–600 | 100–250 |
| Chamadas de ferramenta | 2–4 + releitura de arquivos | 1 em lote |
| Contexto relido | cresce sem limite | ≤ 100k, zerado por sessão |
| **Custo aproximado** | **~$0,05–0,10** | **~$0,01–0,02** |

São estimativas para orientar; meça na sua mesa (`/cost` no Claude Code) e ajuste os tetos de palavras e o `effort`.

### 3.7 Botões de ajuste
- Cena épica pedindo mais? `/effort medium` momentaneamente, depois volte para `low`.
- Narração curta demais? Suba os tetos no núcleo (o maior custo continua sendo saída).
- Campanha muito grande? Baixe o teto do resumo e confie no `lore ?` para buscas.
