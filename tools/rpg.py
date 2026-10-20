#!/usr/bin/env python3
"""rpg.py — motor determinístico do Mestre. Só stdlib.

Toda matemática, dado e estado mora aqui; o modelo só narra.
Saídas são deliberadamente curtas (cada caractere vira token de entrada).
Vários comandos numa chamada: rpg.py x "rolar 1d20+3; pj kael hp-4; log Kael caiu"
"""
import json, os, random, re, shlex, shutil, sys, tarfile, time
from pathlib import Path

ROOT = Path(os.environ.get("RPG_DIR", Path(__file__).resolve().parent.parent / "campanha"))
ATR = ["FOR", "DES", "CON", "INT", "SAB", "CAR"]
PERICIAS = {
    "acrobacia": "DES", "arcanismo": "INT", "atletismo": "FOR", "atuacao": "CAR",
    "enganacao": "CAR", "furtividade": "DES", "historia": "INT", "intimidacao": "CAR",
    "intuicao": "SAB", "investigacao": "INT", "lidar": "SAB", "medicina": "SAB",
    "natureza": "INT", "percepcao": "SAB", "persuasao": "CAR", "prestidigitacao": "DES",
    "religiao": "INT", "sobrevivencia": "SAB",
}
OUT = []


def say(*a):
    OUT.append(" ".join(str(x) for x in a))


def die(msg):
    raise SystemExit(f"ERRO: {msg}")


# ---------- persistência ----------
def jload(p, default):
    p = ROOT / p
    return json.loads(p.read_text("utf-8")) if p.exists() else default


def jsave(p, data):
    p = ROOT / p
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), "utf-8")
    tmp.replace(p)


def est():
    if not (ROOT / "estado.json").exists():
        die("sem campanha. Use: rpg.py nova \"Nome\"")
    return jload("estado.json", {})


def slug(s):
    s = s.lower()
    for a, b in zip("áàâãéêíóôõúç", "aaaaeeiooouc"):
        s = s.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def mod(v):
    return (int(v) - 10) // 2


def sg(n):
    return f"+{n}" if n >= 0 else str(n)


# ---------- dados ----------
TERM = re.compile(r"([+-]?)(\d*)d(\d+)(?:(kh|kl)(\d+))?(!)?|([+-]?)(\d+)")


def roll(expr, quiet=False):
    """Suporta 2d6+3, 4d6kh3, 2d20kl1, 1d6! (explode), d%. Retorna (total, texto)."""
    e = expr.replace(" ", "").replace("d%", "d100").lower()
    if not e or not re.fullmatch(r"([+-]?(\d*d\d+(k[hl]\d+)?!?|\d+))+", e):
        die(f"expressão inválida: {expr}")
    total, parts = 0, []
    for m in TERM.finditer(e):
        if m.group(3):
            sign = -1 if m.group(1) == "-" else 1
            n, f = int(m.group(2) or 1), int(m.group(3))
            if n > 100 or f > 1000:
                die("dados demais")
            rs = []
            for _ in range(n):
                r = random.randint(1, f)
                rs.append(r)
                while m.group(6) and r == f and len(rs) < 50:
                    r = random.randint(1, f)
                    rs.append(r)
            kept = rs
            if m.group(4):
                k = int(m.group(5))
                kept = sorted(rs, reverse=m.group(4) == "kh")[:k]
            s = sum(kept) * sign
            total += s
            parts.append(f"{'-' if sign < 0 else ''}{n}d{f}{m.group(4) or ''}{m.group(5) or ''}{rs}")
        else:
            v = int(m.group(8)) * (-1 if m.group(7) == "-" else 1)
            total += v
            parts.append(sg(v))
    return total, f"{' '.join(parts)}={total}"


def d20(vd=None):
    a, b = random.randint(1, 20), random.randint(1, 20)
    if vd == "vant":
        return max(a, b), f"d20v[{a},{b}]"
    if vd == "desv":
        return min(a, b), f"d20d[{a},{b}]"
    return a, f"d20({a})"


# ---------- condições ----------
COND_EF = {"envenenado": "desv", "amedrontado": "desv", "cego": "desv", "exausto": "desv",
           "enfraquecido": "desv", "inspirado": "vant", "abencoado": "vant", "escondido": "vant"}
COND_ALVO = {"atordoado", "paralisado", "contido", "cego", "caido", "inconsciente"}  # dão vantagem a quem ataca


def vd_final(vd, p, alvo=None):
    """Combina vant/desv explícito com condições do portador (e do alvo). Vant+desv se anulam."""
    fs, notas = ([vd] if vd else []), []
    for c in p.get("cond", []):
        ef = COND_EF.get(slug(c))
        if ef:
            fs.append(ef)
            notas.append(f"{c}→{ef}")
    for c in (alvo or {}).get("cond", []):
        if slug(c) in COND_ALVO:
            fs.append("vant")
            notas.append(f"alvo {c}→vant")
    r = None if ("vant" in fs and "desv" in fs) else "vant" if "vant" in fs else "desv" if "desv" in fs else None
    return r, (" (" + ", ".join(notas) + ")" if notas else "")


# ---------- heróis prontos (classes) ----------
# ca: (tipo, base) — fixo | des | desmax2 | barb ; arma/dano/atr = ataque básico
CLASSES = {
    "guerreiro": dict(hd=10, ordem="FOR CON DES SAB CAR INT", ca=("fixo", 16), arma="espada longa", dano="1d8", atr="FOR",
                      alc="corpo", per="atletismo,intimidacao,percepcao", res="FOR,CON",
                      tracos="Retomar Fôlego (curto: cura 1d10+nível); Estilo de Luta (use man=poderoso/certeiro)",
                      rec={"folego": [1, 1, "c"]}, itens="espada longa,cota de malha,escudo,corda",
                      desc="tanque e dano físico confiável"),
    "ladino": dict(hd=8, ordem="DES CON INT CAR SAB FOR", ca=("des", 11), arma="rapieira", dano="1d8", atr="DES",
                   alc="corpo", per="furtividade,prestidigitacao,percepcao,enganacao", res="DES,INT",
                   tracos="Ataque Furtivo (token 'furtivo' no ataque: +nível/2 d6, com vantagem ou aliado perto); Gíria de Ladrão",
                   rec={}, itens="rapieira,adaga,ferramentas de ladrão,couro", desc="furtivo, perícias e golpes decisivos"),
    "mago": dict(hd=6, ordem="INT CON DES SAB CAR FOR", ca=("des", 10), arma="raio arcano", dano="1d10", atr="INT",
                 alc="dist", per="arcanismo,historia,investigacao", res="INT,SAB",
                 tracos="Raio Arcano (truque, à vontade)", rec={"slots": [2, 2, "l"]},
                 magias="Mísseis Mágicos (1 slot: 3d4+3 sem erro); Escudo Arcano (1 slot: +5 CA); Sono (1 slot)",
                 itens="cajado,grimório,pergaminho,adaga", desc="magia versátil, frágil de perto"),
    "clerigo": dict(hd=8, ordem="SAB CON FOR CAR DES INT", ca=("fixo", 16), arma="maça sagrada", dano="1d6", atr="FOR",
                    alc="corpo", per="medicina,religiao,intuicao", res="SAB,CAR",
                    tracos="Canalizar Fé; Armadura Pesada", rec={"slots": [2, 2, "l"]},
                    magias="Curar Ferimentos (1 slot: 1d8+SAB); Bênção (1 slot: aliados com vantagem em 1 teste); Chama Sagrada (truque 1d8)",
                    itens="maça,cota de malha,escudo,símbolo sagrado", desc="cura, suporte e fé"),
    "patrulheiro": dict(hd=10, ordem="DES SAB CON FOR INT CAR", ca=("desmax2", 13), arma="arco longo", dano="1d8", atr="DES",
                        alc="dist", per="sobrevivencia,furtividade,percepcao,natureza", res="FOR,DES",
                        tracos="Inimigo Favorito; Explorador Natural (sem perder-se, forrageio)", rec={},
                        itens="arco longo,espada curta,couro batido,aljava", desc="rastreador e atirador"),
    "bardo": dict(hd=8, ordem="CAR DES CON SAB INT FOR", ca=("des", 11), arma="rapieira", dano="1d8", atr="DES",
                  alc="corpo", per="atuacao,persuasao,enganacao,historia", res="DES,CAR",
                  tracos="Inspiração (reação: aliado ganha 'inspirado' = vantagem em 1 teste)", rec={"inspiracao": [3, 3, "l"], "slots": [2, 2, "l"]},
                  magias="Palavras de Cura (1 slot: 1d4+CAR); Sussurros Dissonantes (1 slot: 3d6)",
                  itens="rapieira,alaúde,couro,disfarce", desc="rosto da equipe, apoio e magia"),
    "paladino": dict(hd=10, ordem="FOR CAR CON SAB DES INT", ca=("fixo", 16), arma="espada longa", dano="1d8", atr="FOR",
                     alc="corpo", per="persuasao,atletismo,religiao", res="SAB,CAR",
                     tracos="Cura pelas Mãos (reserva 5 PV/longo); Sentido Divino; Juramento (o código importa: honra)",
                     rec={"maos": [5, 5, "l"], "slots": [1, 1, "l"]}, itens="espada longa,cota de malha,escudo,símbolo",
                     desc="guerreiro sagrado movido por juramento"),
    "barbaro": dict(hd=12, ordem="FOR CON DES SAB CAR INT", ca=("barb", 10), arma="machado grande", dano="1d12", atr="FOR",
                    alc="corpo", per="atletismo,sobrevivencia,intimidacao", res="FOR,CON",
                    tracos="Fúria (2x/longo: +2 dano, resiste dano físico, 1 min)", rec={"furia": [2, 2, "l"]},
                    itens="machado grande,machadinhas,couro", desc="fúria, resistência e dano bruto"),
}
ARRAY_PADRAO = [15, 14, 13, 12, 10, 8]
XP_NIVEL = [0, 300, 900, 2700, 6500, 14000, 23000, 34000, 48000, 64000, 85000, 100000, 120000, 140000,
            165000, 195000, 225000, 265000, 305000, 355000]

# ---------- bestiário (base de nível 1; escala com n) ----------
# tipo: (ca, hp, atk, dano, des, dist)
BEST = {
    "capanga": (12, "2d6", 3, "1d6+1", 1, 0), "soldado": (15, "2d8+2", 4, "1d8+2", 1, 0),
    "bruto": (12, "4d10+8", 5, "2d6+3", 0, 0), "chefe": (16, "8d10+16", 7, "2d8+4", 2, 0),
    "arqueiro": (13, "2d8", 4, "1d8+2", 3, 1), "feiticeiro": (12, "3d8", 5, "2d8", 2, 1),
    "fera": (13, "3d10+3", 5, "1d10+3", 2, 0), "morto-vivo": (11, "3d8+6", 4, "1d8+2", 0, 0),
    "cultista": (12, "2d8", 4, "1d8", 1, 0), "assassino": (15, "4d8", 6, "1d8+4", 4, 0),
    "gigante": (14, "10d12+30", 8, "3d8+5", -1, 0),
}

# ---------- tabelas do mundo ----------
NOMES = {
    "nordico": (["Bjor", "Hald", "Sig", "Ulf", "Ragn", "Thor", "Ing", "Eir", "Gunn", "Sven", "Astr", "Frey"],
                ["n", "ric", "vald", "a", "dis", "mund", "hild", "ar", "gerd", "ulf", "run", "ek"]),
    "silvestre": (["Ael", "Syl", "Ith", "Lor", "Fae", "Ney", "Cael", "Thal", "Vael", "Ori"],
                  ["ndra", "riel", "wen", "thas", "nor", "ivar", "isse", "amir", "oren", "ael"]),
    "anao": (["Dur", "Brom", "Thrun", "Gar", "Kaz", "Bor", "Mor", "Hald", "Rok", "Dwal"],
             ["in", "gar", "dak", "ni", "grim", "bek", "dum", "rik", "ald", "orn"]),
    "mediterraneo": (["Ma", "Lu", "Cas", "Ber", "Ro", "Vi", "Tul", "Ser", "Ata", "Nic"],
                     ["rcello", "cia", "ndro", "lia", "drigo", "torio", "nza", "vio", "nora", "landro"]),
    "deserto": (["Ka", "Za", "Hass", "Tar", "Ish", "Nur", "Ra", "Sah", "Yas", "Fa"],
                ["mil", "hira", "nar", "dim", "'ad", "zeem", "bir", "mah", "lun", "qar"]),
    "tribal": (["Gr", "Uk", "Zug", "Mog", "Ba", "Krag", "Throk", "Ogg", "Rak", "Dru"],
               ["ash", "ak", "oth", "ra", "uk", "ul", "nar", "goth", "gga", "zul"]),
    "sombrio": (["Mor", "Vex", "Nyx", "Cor", "Ash", "Mal", "Seth", "Drav", "Ves", "Ul"],
                ["thain", "ra", "ion", "vek", "dris", "naz", "mora", "kar", "eth", "zar"]),
}
NOMES_COMUNS = ["Joan", "Marta", "Bento", "Lena", "Tiago", "Rosa", "Otto", "Nina", "Caio", "Dora", "Pedro", "Ana",
                "Gil", "Vera", "Hugo", "Tereza", "Duarte", "Iná", "Lupe", "Zeca"]
EPITETOS = ["o Manco", "Mão-de-Ferro", "a Sem-Sorte", "Olho-de-Corvo", "o Devedor", "a Risonha", "Pé-de-Lã",
            "o Velho", "Sete-Dedos", "a Calada", "o Honesto", "Língua-de-Prata", "Sombra-Curta", "o Cinzento"]
ENCONTROS = {
    "floresta": [("perigo", "lobos famintos seguem o grupo à distância"), ("perigo", "armadilha de caçador escondida no mato"),
                 ("social", "lenhadores bloqueiam o caminho e pedem pedágio"), ("descoberta", "clareira com altar quebrado coberto de musgo"),
                 ("cotidiano", "carvoeiros oferecem sopa junto à fogueira"), ("cotidiano", "chuva fina; todos se abrigam sob um carvalho oco")],
    "estrada": [("perigo", "bandidos fingem ser viajantes feridos"), ("perigo", "ponte podre sobre um riacho fundo"),
                ("social", "caravana de mercadores quer escolta por um trecho"), ("descoberta", "marco de pedra com símbolo de uma facção recém-riscado"),
                ("cotidiano", "feira de beira de estrada, cheiro de pão e fumaça"), ("cotidiano", "um carroceiro conta fofocas do reino em troca de carona")],
    "montanha": [("perigo", "deslizamento de pedras no desfiladeiro"), ("perigo", "ventania cortante exige abrigo ou corda"),
                 ("social", "pastores desconfiados guardam a única passagem"), ("descoberta", "caverna com entalhes antigos e pegadas frescas"),
                 ("cotidiano", "mosteiro isolado serve chá e silêncio"), ("cotidiano", "um mineiro aposentado ensina um atalho em troca de histórias")],
    "deserto": [("perigo", "tempestade de areia se levanta no horizonte"), ("perigo", "poço envenenado ou seco onde devia haver água"),
                ("social", "nômades oferecem água em troca de uma tarefa"), ("descoberta", "esqueleto de um navio enterrado nas dunas"),
                ("cotidiano", "oásis lotado de viajantes, jogos e barganhas"), ("cotidiano", "caravana dança ao pôr do sol, noite fria e estrelada")],
    "cidade": [("perigo", "batedor de carteiras escolhe o PJ mais distraído"), ("perigo", "briga de taverna que pode virar motim"),
               ("social", "oficial da guarda faz perguntas demais"), ("descoberta", "bilhete escondido no forro de uma capa comprada"),
               ("cotidiano", "mercado ao amanhecer: peixe, especiarias, gritos"), ("cotidiano", "criança vende rumores por uma moeda de cobre")],
    "masmorra": [("perigo", "laje solta ativa um mecanismo ao fundo"), ("perigo", "criaturas famintas cercam a única saída"),
                 ("social", "prisioneiro pede ajuda; talvez minta"), ("descoberta", "diário de um explorador morto com um mapa parcial"),
                 ("cotidiano", "acampamento seguro: gotejar distante, pedra morna"), ("cotidiano", "o grupo acha uma fonte limpa; hora de remendar o equipamento")],
    "pantano": [("perigo", "areia movediça escondida sob folhas"), ("perigo", "névoa e luzes falsas guiam para águas fundas"),
                ("social", "pescador solitário sabe algo e não quer falar"), ("descoberta", "cabana abandonada com símbolos de proteção invertidos"),
                ("cotidiano", "mosquitos, bota encharcada e uma sopa de enguia surpreendentemente boa"), ("cotidiano", "barqueiro canta para espantar o silêncio")],
    "mar": [("perigo", "tempestade repentina, hora de baixar velas"), ("perigo", "navio sem bandeira acompanha a distância"),
            ("social", "pescadores trocam peixe por notícias da costa"), ("descoberta", "destroços ainda quentes de uma batalha recente"),
            ("cotidiano", "calmaria, jogo de dados no convés, conto de marujo"), ("cotidiano", "cozinheiro desafia o grupo a adivinhar o ingrediente secreto")],
}
CLIMAS = {
    "temperado": ["céu limpo e vento fraco", "garoa fina e constante", "neblina baixa colando nos tornozelos",
                  "calor pesado antes de trovoada", "vento forte arrancando folhas", "chuva grossa, lama nas estradas",
                  "manhã gelada, tarde clara", "nuvens altas e luz dourada"],
    "frio": ["neve fina silenciosa", "vento cortante e céu de chumbo", "nevasca: visibilidade quase nula", "geada e sol pálido",
             "frio seco, respiração em fumaça", "gelo rachando ao longe", "céu limpo e gelado, estrelas duras", "degelo e lama"],
    "deserto": ["sol impiedoso, ar tremendo", "vento quente levantando areia", "noite gélida, céu enorme", "tempestade de areia",
                "calmaria abafada", "mirage no horizonte", "madrugada fresca e azul", "nuvem rara, sombra preciosa"],
    "tropical": ["abafado, mosquitos", "aguaceiro repentino", "névoa quente na mata", "sol forte entre nuvens",
                 "trovoada distante", "umidade grudando na pele", "manhã clara e barulhenta de pássaros", "chuva morna e contínua"],
    "mar": ["brisa constante, mar manso", "ondas altas e céu cinza", "calmaria total", "neblina densa, sinos ao longe",
            "vento de popa", "tempestade com raios", "maresia e sol forte", "garoa e mar espelhado"],
}
RUMORES = [
    "{fac} anda comprando {coisa} em segredo.", "{fac} e {fac2} se encontraram à noite e saiu sangue.",
    "{npc} deve dinheiro a quem não perdoa.", "Há luzes estranhas perto de {lugar} desde a última lua.",
    "Um forasteiro pagou o dobro por {coisa} e sumiu.", "Ninguém mais passa por {lugar} depois do pôr do sol.",
    "{fac} teme algo que {npc} sabe.", "O preço de {coisa} dobrou; alguém está estocando.",
    "{npc} não é quem diz ser.", "Um símbolo de {fac} foi pintado em {lugar}.",
]
COISAS = ["sal", "aço", "velas", "cavalos", "pergaminhos antigos", "vinho", "corda", "ervas raras", "tochas", "cinzas"]
LUGARES = ["a ponte velha", "o moinho", "a torre do norte", "o poço seco", "a estalagem do cruzamento", "o cemitério"]
ATT_NOMES = {-3: "inimigo", -2: "hostil", -1: "frio", 0: "neutro", 1: "simpático", 2: "amigo", 3: "devoto"}
MANOBRAS = {"poderoso": (-3, "+5"), "certeiro": (3, "-2"), "finalizar": (2, "")}


# ---------- personagens ----------
def pj_path(i):
    return f"pjs/{slug(i)}.json"


def pj_load(i):
    p = jload(pj_path(i), None)
    if p is None:
        cb = est().get("combate") or {}
        for c in cb.get("ordem", []):
            if slug(c["nome"]) == slug(i):
                return c
        die(f"personagem '{i}' não existe")
    return p


def prof(p):
    return 2 + (int(p.get("nivel", 1)) - 1) // 4


def bonus(p, chave):
    """Bônus de teste para atributo, perícia ou salvaguarda (ex.: 'SAB', 'percepcao', 'res-DES')."""
    k = chave.lower()
    per = [slug(x) for x in p.get("pericias", [])]
    if k.startswith("res-"):
        a = k[4:].upper()
        b = mod(p.get(a, 10))
        if a in [x.upper() for x in p.get("resist", [])]:
            b += prof(p)
        return b, f"Res.{a}"
    if k.upper() in ATR:
        return mod(p.get(k.upper(), 10)), k.upper()
    k = slug(k)
    if k in PERICIAS:
        b = mod(p.get(PERICIAS[k], 10)) + (prof(p) if k in per else 0)
        return b, k.capitalize()
    die(f"perícia/atributo '{chave}' desconhecido")


def ficha_curta(p):
    hp = f"{p.get('hp', '?')}/{p.get('hpmax', '?')}"
    at = " ".join(f"{a}{p[a]}({sg(mod(p[a]))})" for a in ATR if a in p)
    extra = []
    if p.get("cond"):
        extra.append("cond:" + ",".join(p["cond"]))
    if "honra" in p:
        extra.append(f"honra{sg(int(p['honra']))}")
    if p.get("rec"):
        extra.append("rec:" + ",".join(f"{k}{a}/{m}" for k, (a, m, _) in p["rec"].items()))
    return f"{p['nome']} N{p.get('nivel', 1)} {p.get('raca', '')} {p.get('classe', '')} PV{hp} CA{p.get('ca', '?')} | {at}" + (
        " | " + " ".join(extra) if extra else "")


def cmd_pj(args):
    """pj novo <nome> k=v...  |  pj <id> campo±valor ...  |  pj <id> campo=valor"""
    if not args:
        die("uso: pj novo <nome> k=v... | pj <id> hp-5 po+10 item+Corda cond+Caído")
    if args[0] == "novo":
        nome = args[1]
        p = {"nome": nome, "nivel": 1, "xp": 0, "po": 0, "itens": [], "cond": [], "pericias": [], "resist": [], "honra": 0}
        for kv in args[2:]:
            k, v = kv.split("=", 1)
            p[k if k.upper() not in ATR else k.upper()] = (
                v.split(",") if k in ("pericias", "resist", "itens") else int(v) if v.lstrip("-").isdigit() else v)
        p.setdefault("hpmax", p.get("hp", 10))
        p.setdefault("hp", p["hpmax"])
        jsave(pj_path(nome), p)
        return say("criado:", ficha_curta(p))
    p = pj_load(args[0])
    is_pc = (ROOT / pj_path(args[0])).exists()
    for op in args[1:]:
        m = re.fullmatch(r"(\w+)([+\-=])(.*)", op)
        if not m:
            die(f"op inválida '{op}'")
        k, o, v = m.groups()
        k = k.upper() if k.upper() in ATR else {"item": "itens", "pv": "hp"}.get(k, k)
        cur = p.get(k)
        if isinstance(cur, list) or k in ("itens", "cond", "pericias", "resist"):
            lst = p.setdefault(k, [])
            if o == "+":
                lst.append(v)
            elif o == "-":
                hit = [x for x in lst if slug(x) == slug(v)]
                if not hit:
                    die(f"{k} não contém '{v}'")
                lst.remove(hit[0])
            else:
                p[k] = v.split(",") if v else []
        elif o == "=":
            p[k] = int(v) if v.lstrip("-").isdigit() else v
        else:
            n = int(v) if v.lstrip("-").isdigit() else roll(v)[0]
            p[k] = int(cur or 0) + (n if o == "+" else -n)
            if k == "hp":
                p["hp"] = max(0, min(p["hp"], int(p.get("hpmax", p["hp"]))))
                if p["hp"] == 0 and "Caído" not in p.setdefault("cond", []):
                    p["cond"].append("Caído")
                elif p["hp"] > 0:
                    p["cond"] = [c for c in p.get("cond", []) if c not in ("Caído", "Estável")]
                    p.pop("morte", None)
    if is_pc:
        jsave(pj_path(args[0]), p)
    else:  # combatente temporário
        e = est()
        for i, c in enumerate(e["combate"]["ordem"]):
            if slug(c["nome"]) == slug(p["nome"]):
                e["combate"]["ordem"][i] = p
        jsave("estado.json", e)
    say(ficha_curta(p) if is_pc else f"{p['nome']} PV{p['hp']}/{p.get('hpmax')}" + (" CAÍDO" if p["hp"] == 0 else ""))
    if is_pc and any(o.lower().startswith("xp") for o in args[1:]) and int(p.get("nivel", 1)) < 20 \
            and int(p.get("xp", 0)) >= XP_NIVEL[int(p.get("nivel", 1))]:
        say(f"⬆ {p['nome']} pode subir de nível: rpg.py subir {slug(p['nome'])}")
    if is_pc and p.get("hp", 1) == 0 and "Morto" not in p.get("cond", []):
        say(f"→ {p['nome']} caído: rpg.py morte {slug(p['nome'])} a cada turno dele")


def cmd_ficha(args):
    """ficha | ficha <id>  (sem id: 1 linha por PJ)"""
    if not args:
        for f in sorted((ROOT / "pjs").glob("*.json")):
            say(ficha_curta(json.loads(f.read_text("utf-8"))))
        return
    p = pj_load(args[0])
    say(ficha_curta(p))
    per = ", ".join(f"{x}{sg(bonus(p, x)[0])}" for x in p.get("pericias", []))
    if per:
        say("Perícias:", per)
    for k in ("ataques", "magias", "tracos"):
        if p.get(k):
            say(f"{k.capitalize()}:", p[k] if isinstance(p[k], str) else "; ".join(p[k]))
    say(f"Itens: {', '.join(p.get('itens', [])) or '-'} | PO {p.get('po', 0)} | XP {p.get('xp', 0)}")
    if p.get("codigo"):
        say("Código:", p["codigo"])
    if "honra" in p:
        say(f"Honra {sg(int(p['honra']))} ({honra_nivel(int(p['honra']))})")
    if p.get("notas"):
        say("Notas:", p["notas"])


def cmd_atributos(args):
    """Rola 4d6kh3 seis vezes (padrão clássico)."""
    vals = []
    for _ in range(6):
        t, s = roll("4d6kh3")
        vals.append(t)
        say(s)
    say("Atributos:", sorted(vals, reverse=True), "| soma", sum(vals))


def cmd_teste(args):
    """teste <pj> <perícia|ATR|res-ATR> [cd] [vant|desv] [+N]"""
    if len(args) < 2:
        die("uso: teste <pj> <pericia> [cd] [vant|desv] [+N]")
    p = pj_load(args[0])
    b, nome = bonus(p, args[1])
    cd, vd, extra = None, None, 0
    for a in args[2:]:
        if a in ("vant", "desv"):
            vd = a
        elif a[0] in "+-":
            extra += int(a)
        else:
            cd = int(a)
    vd, nota = vd_final(vd, p)
    r, s = d20(vd)
    tot = r + b + extra
    res = "" if cd is None else (" ✓" if tot >= cd else " ✗")
    crit = " CRÍTICO" if r == 20 else " FALHA CRÍTICA" if r == 1 else ""
    say(f"{p['nome']} {nome} {s}{sg(b + extra)}={tot}" + (f" vs CD{cd}" if cd else "") + res + crit + nota)


def cmd_rolar(args):
    """rolar 2d6+3,4d6kh3,2d20kl1,1d6!,d%  (vírgula = várias)"""
    expr = "".join(args) or "1d20"
    for e in expr.split(","):
        say(roll(e)[1])


def cmd_oraculo(args):
    """oraculo [provavel|improvavel] | oraculo reacao  — decide incertezas sem deliberar"""
    if args and args[0] == "reacao":
        t, s = roll("2d6")
        r = ("hostil" if t <= 2 else "desconfiado" if t <= 5 else "neutro/indeciso" if t <= 8
             else "amigável" if t <= 11 else "entusiasmado")
        return say(f"reação {s} → {r}")
    alvo = {"provavel": 7, "improvavel": 15}.get(args[0] if args else "", 11)
    r = random.randint(1, 20)
    res = "SIM" if r >= alvo else "NÃO"
    if r == 20 or r == 1:
        res += ", e de forma extrema"
    elif abs(r - alvo) <= 1:
        res += ", mas com ressalva"
    say(f"oráculo d20({r}) alvo {alvo} → {res}")


# ---------- estado / mundo ----------
def cmd_nova(args):
    """nova "Nome da campanha" [--forcar]"""
    if (ROOT / "estado.json").exists() and "--forcar" not in args:
        die("já existe campanha; use --forcar para sobrescrever")
    nome = args[0] if args else "Campanha"
    for d in ("pjs", "mundo"):
        (ROOT / d).mkdir(parents=True, exist_ok=True)
    jsave("estado.json", {"campanha": nome, "sessao": 1, "dia": 1, "hora": "manhã", "local": "",
                          "cena": "", "fios": [], "relogios": {}, "faccoes": {}, "flags": {}, "combate": None})
    for f, t in (("resumo.md", f"# {nome}\n"), ("log.md", ""), ("prep.md", "")):
        if not (ROOT / f).exists():
            (ROOT / f).write_text(t, "utf-8")
    say(f"campanha '{nome}' criada em {ROOT}")


def cmd_cena(args):
    """cena "texto" local=X dia+1 hora=noite"""
    e = est()
    for a in args:
        m = re.fullmatch(r"(local|hora|dia|sessao)([+=])(.*)", a)
        if m:
            k, o, v = m.groups()
            e[k] = int(e.get(k, 0)) + int(v) if o == "+" else (int(v) if v.isdigit() else v)
        else:
            e["cena"] = a
    jsave("estado.json", e)
    say(f"S{e['sessao']} D{e['dia']} {e['hora']} @{e['local']}: {e['cena']}")


def cmd_fio(args):
    """fio + "texto" | fio - N | fio  (fios = ganchos/missões abertas)"""
    e = est()
    if args and args[0] == "+":
        e["fios"].append(" ".join(args[1:]))
    elif args and args[0] == "-":
        e["fios"].pop(int(args[1]) - 1)
    jsave("estado.json", e)
    for i, f in enumerate(e["fios"], 1):
        say(f"{i}. {f}")


def cmd_relogio(args):
    """relogio "Nome" +1 [/6]  — relógios de facção/perigo (estilo Blades)."""
    e = est()
    if not args:
        for k, (a, m) in e["relogios"].items():
            say(f"{k} [{a}/{m}]")
        return
    nome, a, m = args[0], *e["relogios"].get(args[0], [0, 4])
    for x in args[1:]:
        if x.startswith("/"):
            m = int(x[1:])
        elif x == "x":
            e["relogios"].pop(nome, None)
            jsave("estado.json", e)
            return say(f"{nome} removido")
        else:
            a = max(0, a + int(x))
    e["relogios"][nome] = [a, m]
    jsave("estado.json", e)
    say(f"{nome} [{a}/{m}]" + (" COMPLETO!" if a >= m else ""))


def cmd_flag(args):
    """flag chave=valor ... (valor vazio apaga)"""
    e = est()
    for kv in args:
        k, v = kv.split("=", 1)
        if v == "":
            e["flags"].pop(k, None)
        else:
            e["flags"][k] = v
    jsave("estado.json", e)
    say(" ".join(f"{k}={v}" for k, v in e["flags"].items()) or "(sem flags)")


def cmd_log(args):
    """log texto  — 1 linha factual por evento relevante"""
    e = est()
    with open(ROOT / "log.md", "a", encoding="utf-8") as f:
        f.write(f"S{e['sessao']}D{e['dia']}: {' '.join(args)}\n")
    say("ok")


def cmd_lore(args):
    """lore | lore <id> | lore + <id> "resumo 1 linha" [corpo] | lore ? termo"""
    d = ROOT / "mundo"
    d.mkdir(parents=True, exist_ok=True)
    if not args:
        for f in sorted(d.glob("*.md")):
            say(f"{f.stem}: {f.read_text('utf-8').splitlines()[0][:90]}")
        return
    if args[0] == "+":
        f = d / f"{slug(args[1])}.md"
        if f.exists():
            with open(f, "a", encoding="utf-8") as h:
                h.write("\n" + " ".join(args[2:]))
            return say(f"{f.stem} += nota")
        f.write_text("\n".join(args[2:]) + "\n", "utf-8")
        return say(f"{f.stem} criado")
    if args[0] == "?":
        t = slug(" ".join(args[1:]))
        for f in sorted(d.glob("*.md")):
            for ln in f.read_text("utf-8").splitlines():
                if t in slug(ln):
                    say(f"{f.stem}: {ln[:120]}")
        return
    f = d / f"{slug(args[0])}.md"
    say(f.read_text("utf-8").strip() if f.exists() else f"'{args[0]}' não existe")


# ---------- honra e facções ----------
HONRA_MIN, HONRA_MAX = -5, 5
REP_MIN, REP_MAX = -3, 3
REP_NOMES = {-3: "inimiga jurada", -2: "hostil", -1: "desconfiada", 0: "neutra", 1: "simpática",
             2: "aliada", 3: "devota"}


def honra_nivel(h):
    return ("lendária" if h >= 4 else "respeitada" if h >= 2 else "comum" if h >= 0
            else "manchada" if h >= -2 else "desonrada")


def cmd_honra(args):
    """honra <pj> [+N|-N|=N] [motivo...]  — honra/reputação pessoal (-5..+5) ligada ao código do PJ"""
    if not args:
        die("uso: honra <pj> +1 \"cumpriu o juramento\"  (sem delta: mostra)")
    p = pj_load(args[0])
    if not (ROOT / pj_path(args[0])).exists():
        die("honra só vale para PJs")
    h = int(p.get("honra", 0))
    if len(args) > 1 and re.fullmatch(r"[+\-=]\d+", args[1]):
        op, n = args[1][0], int(args[1][1:])
        h = n if op == "=" else h + n if op == "+" else h - n
        h = max(HONRA_MIN, min(HONRA_MAX, h))
        p["honra"] = h
        jsave(pj_path(args[0]), p)
        if len(args) > 2:
            cmd_log([f"[honra {p['nome']} {args[1]}]"] + args[2:])
    say(f"{p['nome']} honra {sg(h)} ({honra_nivel(h)})" + (f" | código: {p['codigo']}" if p.get("codigo") else ""))


def cmd_faccao(args):
    """faccao | faccao "Nome" [rep+1|rep-1|rep=N] ["desejo/meta 1 linha"] | faccao "Nome" x"""
    e = est()
    fs = e.setdefault("faccoes", {})
    if not args:
        for k, f in fs.items():
            say(f"{k} {sg(f['rep'])} {REP_NOMES[f['rep']]}" + (f" — {f['meta']}" if f.get("meta") else ""))
        return say("(sem facções)") if not fs else None
    nome = args[0]
    f = fs.setdefault(nome, {"rep": 0, "meta": ""})
    for x in args[1:]:
        m = re.fullmatch(r"rep([+\-=])(\d+)", x)
        if x == "x":
            fs.pop(nome, None)
            jsave("estado.json", e)
            return say(f"{nome} removida")
        if m:
            o, n = m.group(1), int(m.group(2))
            f["rep"] = n if o == "=" else f["rep"] + n if o == "+" else f["rep"] - n
            f["rep"] = max(REP_MIN, min(REP_MAX, f["rep"]))
        else:
            f["meta"] = x
    jsave("estado.json", e)
    say(f"{nome} {sg(f['rep'])} {REP_NOMES[f['rep']]}" + (f" — {f['meta']}" if f["meta"] else ""))


# ---------- combate ----------
def cmd_combate(args):
    """combate inicio "Goblin:ca13:hp7:atk4:dano1d6+2:des2" ... | combate | combate fim"""
    e = est()
    if args and args[0] == "inicio":
        ordem = []
        for f in sorted((ROOT / "pjs").glob("*.json")):
            p = json.loads(f.read_text("utf-8"))
            if p.get("hp", 0) > 0:
                r = random.randint(1, 20)
                ordem.append({"nome": p["nome"], "pj": True, "ini": r + mod(p.get("DES", 10)), "d": r, "zona": "meio"})
        for spec in args[1:]:
            if spec.startswith("@"):
                m = re.fullmatch(r"@([a-z\-]+?)(?:x(\d+))?(?:n(\d+))?", spec.lower())
                if not m:
                    die(f"atalho inválido '{spec}' (ex.: @soldadox3n2)")
                spec = monstro_spec(m.group(1), int(m.group(3) or 1), int(m.group(2) or 1))
            parts = spec.split(":")
            base, qtd = re.fullmatch(r"(.+?)(?:x(\d+))?", parts[0]).groups()
            qtd = qtd or "1"
            dist = "dist" in parts[1:]
            zona = next((x[4:] for x in parts[1:] if x.startswith("zona")), "meio")
            stats = dict(re.match(r"([a-z]+)(.*)", s).groups() for s in parts[1:] if s != "dist" and not s.startswith("zona"))
            for i in range(int(qtd)):
                nome = base if int(qtd) == 1 else f"{base}{i + 1}"
                hp = roll(stats["hp"])[0] if "d" in stats.get("hp", "") else int(stats.get("hp", 5))
                r = random.randint(1, 20)
                ordem.append({"nome": nome, "pj": False, "hp": hp, "hpmax": hp, "ca": int(stats.get("ca", 10)),
                              "atk": int(stats.get("atk", 2)), "dano": stats.get("dano", "1d6"),
                              "alcance": "dist" if dist else "corpo", "zona": zona,
                              "ini": r + int(stats.get("des", 0)), "d": r})
        ordem.sort(key=lambda c: (-c["ini"], -c["d"]))
        e["combate"] = {"rodada": 1, "vez": 0, "ordem": ordem}
        jsave("estado.json", e)
        return _status(e)
    if args and args[0] == "fim":
        cb = e.get("combate") or {}
        caidos = [c["nome"] for c in cb.get("ordem", []) if not c.get("pj") and c["hp"] <= 0]
        e["combate"] = None
        jsave("estado.json", e)
        return say("combate encerrado. derrotados:", ", ".join(caidos) or "-")
    if not e.get("combate"):
        return say("sem combate ativo")
    _status(e)


def _hp(c):
    if c.get("pj"):
        p = jload(pj_path(c["nome"]), {})
        return p.get("hp", 0), p.get("hpmax", 0)
    return c["hp"], c["hpmax"]


def _comb(e, nome):
    for c in (e.get("combate") or {}).get("ordem", []):
        if slug(c["nome"]) == slug(nome):
            return c


def cmd_mover(args):
    """mover <nome> <zona>  — posição no combate (ex.: frente, meio, fundo, alto); corpo a corpo exige a mesma zona"""
    if len(args) < 2:
        die("uso: mover <nome> <zona>")
    e = est()
    c = _comb(e, args[0]) or die(f"'{args[0]}' não está no combate")
    c["zona"] = slug(args[1])
    jsave("estado.json", e)
    say(f"{c['nome']} → {c['zona']}")


def _status(e):
    cb = e["combate"]
    linha = []
    zonas = {c.get("zona", "meio") for c in cb["ordem"]}
    for i, c in enumerate(cb["ordem"]):
        hp, mx = _hp(c)
        mark = "▶" if i == cb["vez"] else ""
        z = f"@{c.get('zona', 'meio')}" if len(zonas) > 1 else ""
        linha.append(f"{mark}{c['nome']}({c['ini']}){z} {hp}/{mx}" + ((" caído" if c.get("pj") else "✝") if hp <= 0 else ""))
    say(f"R{cb['rodada']}: " + " | ".join(linha))


def cmd_turno(args):
    """turno  — passa a vez (pula caídos)"""
    e = est()
    cb = e.get("combate") or die("sem combate")
    n = len(cb["ordem"])
    for _ in range(n):
        cb["vez"] += 1
        if cb["vez"] >= n:
            cb["vez"], cb["rodada"] = 0, cb["rodada"] + 1
        if _hp(cb["ordem"][cb["vez"]])[0] > 0:
            break
    jsave("estado.json", e)
    _status(e)


def cmd_ataque(args):
    """ataque <atacante> <alvo> [vant|desv] [+N] [dano=1d8+3] [man=poderoso|certeiro|finalizar] [furtivo]"""
    if len(args) < 2:
        die("uso: ataque <atacante> <alvo> [vant|desv] [+N] [dano=XdY+Z] [man=…] [furtivo]")
    a, t = pj_load(args[0]), pj_load(args[1])
    e = est()
    ca_, ct = _comb(e, args[0]), _comb(e, args[1])
    if ca_ and ct and a.get("alcance", "corpo") != "dist" and ca_.get("zona", "meio") != ct.get("zona", "meio"):
        return say(f"{a['nome']} ({ca_.get('zona')}) não alcança {t['nome']} ({ct.get('zona')}): mover antes ou usar ataque à distância")
    vd, nota = vd_final(next((x for x in args[2:] if x in ("vant", "desv")), None), a, t)
    extra = sum(int(x) for x in args[2:] if x[0] in "+-" and x[1:].isdigit())
    dano = next((x.split("=", 1)[1] for x in args[2:] if x.startswith("dano=")), a.get("dano", "1d6"))
    man = next((x.split("=", 1)[1] for x in args[2:] if x.startswith("man=")), None)
    tag = ""
    if man:
        if man not in MANOBRAS:
            die(f"manobra '{man}' desconhecida: {', '.join(MANOBRAS)}")
        if man == "finalizar" and t["hp"] * 2 > int(t.get("hpmax", t["hp"])):
            die("finalizar exige alvo com metade dos PV ou menos")
        extra += MANOBRAS[man][0]
        dano += MANOBRAS[man][1]
        tag = f" [{man}]"
    if "furtivo" in args[2:]:
        if "furtivo" not in slug(str(a.get("tracos", ""))):
            die(f"{a['nome']} não tem Ataque Furtivo")
        dano += f"+{(int(a.get('nivel', 1)) + 1) // 2}d6"
        tag += " [furtivo]"
    atk = int(a.get("atk", prof(a) + max(mod(a.get("FOR", 10)), mod(a.get("DES", 10))))) + extra
    r, s = d20(vd)
    tot = r + atk
    ca = int(t.get("ca", 10))
    if r == 1 or (tot < ca and r != 20):
        return say(f"{a['nome']}→{t['nome']} {s}{sg(atk)}={tot} vs CA{ca} ERROU{tag}{nota}")
    if r == 20 or man == "finalizar":  # crítico/finalização: dobra os dados
        dano = re.sub(r"(\d*)d(\d+)", lambda m: f"{int(m.group(1) or 1) * 2}d{m.group(2)}", dano)
    dn, ds = roll(dano)
    dn = max(1, dn)
    say(f"{a['nome']}→{t['nome']} {s}{sg(atk)}={tot} vs CA{ca} {'CRÍTICO' if r == 20 else 'ACERTOU'}{tag} dano {ds}{nota}")
    cmd_pj([args[1], f"hp-{dn}"])


# ---------- heróis, recursos, descanso, nível ----------
def _pcs():
    return [json.loads(f.read_text("utf-8")) for f in sorted((ROOT / "pjs").glob("*.json"))]


def _pc(i):
    if not (ROOT / pj_path(i)).exists():
        die(f"'{i}' não é PJ")
    return pj_load(i)


def _save_pc(p):
    jsave(pj_path(p["nome"]), p)


def cmd_heroi(args):
    """heroi <Nome> <classe> [raca=X] [codigo="…"] [notas=…] [FOR=N…]  — cria PJ pronto; sem args lista classes"""
    if len(args) < 2:
        for k, c in CLASSES.items():
            say(f"{k}: {c['desc']}")
        return say("uso: heroi <Nome> <classe> raca=… codigo=\"…\"  (array 15,14,13,12,10,8 já distribuído)")
    nome, cl = args[0], slug(args[1])
    if cl not in CLASSES:
        die(f"classe '{args[1]}' desconhecida (heroi sem args lista)")
    if (ROOT / pj_path(nome)).exists() and "--forcar" not in args:
        die(f"{nome} já existe (--forcar para recriar)")
    c = CLASSES[cl]
    p = {"nome": nome, "nivel": 1, "xp": 0, "po": 15, "cond": [], "honra": 0, "classe": {"clerigo": "Clérigo", "barbaro": "Bárbaro"}.get(cl, cl.capitalize()),
         "hd": c["hd"], "alcance": c["alc"], "pericias": c["per"].split(","), "resist": c["res"].split(","),
         "itens": c["itens"].split(","), "tracos": c["tracos"], "rec": {k: list(v) for k, v in c["rec"].items()}}
    if c.get("magias"):
        p["magias"] = c["magias"]
    for a, v in zip(c["ordem"].split(), ARRAY_PADRAO):
        p[a] = v
    for kv in args[2:]:
        if "=" in kv:
            k, v = kv.split("=", 1)
            p[k.upper() if k.upper() in ATR else k] = int(v) if v.lstrip("-").isdigit() else v
    m = {a: mod(p[a]) for a in ATR}
    kind, base = c["ca"]
    ca = base + (m["DES"] if kind == "des" else min(2, m["DES"]) if kind == "desmax2"
                 else m["DES"] + m["CON"] if kind == "barb" else 0)
    p["ca"] = ca
    p["hpmax"] = p["hp"] = c["hd"] + m["CON"]
    p["atk"] = 2 + m[c["atr"]]
    p["dano"] = f"{c['dano']}{sg(m[c['atr']]) if m[c['atr']] else ''}"
    p["ataques"] = f"{c['arma']} +{p['atk']} / {p['dano']} ({c['alc']})"
    _save_pc(p)
    say("criado:", ficha_curta(p))
    say("distribuição padrão da classe; ajuste com pj <id> FOR=… se o jogador quiser")


def cmd_recurso(args):
    """recurso <pj> [nome ±N|=N|max=N [c|l]]  — usos limitados (slots, fôlego…); c=curto l=longo"""
    if not args:
        die("uso: recurso <pj> slots -1 | recurso <pj> furia max=2 l")
    p = _pc(args[0])
    rec = p.setdefault("rec", {})
    if len(args) >= 2:
        n = slug(args[1])
        novo = n not in rec
        r = rec.setdefault(n, [0, 0, "l"])
        for x in args[2:]:
            m = re.fullmatch(r"([+\-=])(\d+)", x)
            if x in ("c", "l"):
                r[2] = x
            elif x.startswith("max="):
                r[1] = int(x[4:])
                if novo:
                    r[0] = r[1]
            elif m:
                o, v = m.groups()
                nv = int(v) if o == "=" else r[0] + int(v) if o == "+" else r[0] - int(v)
                if nv < 0:
                    die(f"sem usos de {n} ({r[0]}/{r[1]}) — falha para frente: ofereça outra saída")
                r[0] = min(nv, r[1])
            else:
                die(f"op inválida '{x}'")
        _save_pc(p)
    say(f"{p['nome']}: " + (", ".join(f"{k} {a}/{m}" for k, (a, m, _) in rec.items()) or "sem recursos"))


def cmd_descanso(args):
    """descanso curto|longo  — recupera PV/usos de todos os PJs (longo: +1 dia, manhã)"""
    tipo = args[0] if args else die("uso: descanso curto|longo")
    if tipo not in ("curto", "longo"):
        die("uso: descanso curto|longo")
    for p in _pcs():
        if "Morto" in p.get("cond", []):
            continue
        if tipo == "longo":
            p["hp"] = p.get("hpmax", p.get("hp", 1))
            p["cond"] = []
            for r in p.get("rec", {}).values():
                r[0] = r[1]
            p.pop("morte", None)
            say(f"{p['nome']} PV{p['hp']}/{p['hpmax']}")
        else:
            if p.get("hp", 0) > 0:
                g = max(1, roll(f"1d{p.get('hd', 8)}")[0] + mod(p.get("CON", 10)))
                p["hp"] = min(p["hpmax"], p["hp"] + g)
                say(f"{p['nome']} +{g} PV ({p['hp']}/{p['hpmax']})")
            for r in p.get("rec", {}).values():
                if r[2] == "c":
                    r[0] = r[1]
        _save_pc(p)
    if tipo == "longo":
        e = est()
        e["dia"] += 1
        e["hora"] = "manhã"
        jsave("estado.json", e)
        say(f"D{e['dia']} manhã")


def cmd_cura(args):
    """cura <pj> 1d8+3  — rola e aplica cura (levanta quem está Caído)"""
    if len(args) < 2:
        die("uso: cura <pj> 1d8+3")
    t, s = roll(args[1])
    say(f"cura {s}")
    cmd_pj([args[0], f"hp+{max(0, t)}"])


def cmd_morte(args):
    """morte <pj>  — teste de morte (10+ sucesso; 3 sucessos estabiliza; 3 falhas morre; 1=2 falhas; 20=levanta c/ 1 PV)"""
    p = _pc(args[0] if args else die("uso: morte <pj>"))
    if p.get("hp", 0) > 0:
        die(f"{p['nome']} não está caído")
    if "Morto" in p.get("cond", []):
        die(f"{p['nome']} já morreu")
    if "Estável" in p.get("cond", []):
        return say(f"{p['nome']} está estável (0 PV, inconsciente)")
    m = p.setdefault("morte", [0, 0])
    r = random.randint(1, 20)
    if r == 20:
        p["hp"], p["morte"] = 1, [0, 0]
        p["cond"] = [c for c in p["cond"] if c != "Caído"]
        txt = "20! volta com 1 PV"
    else:
        if r == 1:
            m[1] += 2
        elif r >= 10:
            m[0] += 1
        else:
            m[1] += 1
        txt = f"sucessos {m[0]}/3, falhas {m[1]}/3"
        if m[0] >= 3:
            p["cond"].append("Estável")
            txt += " → ESTÁVEL"
        elif m[1] >= 3:
            p["cond"].append("Morto")
            txt += " → MORTO (honre a cena)"
    _save_pc(p)
    say(f"{p['nome']} morte d20({r}): {txt}")


def cmd_subir(args):
    """subir <pj>  — sobe 1 nível se o XP permitir (PV pela média do dado de vida; +1 slot)"""
    p = _pc(args[0] if args else die("uso: subir <pj>"))
    n = int(p.get("nivel", 1))
    if n >= 20:
        die("nível máximo")
    if int(p.get("xp", 0)) < XP_NIVEL[n]:
        die(f"{p['nome']} precisa de mais {XP_NIVEL[n] - int(p.get('xp', 0))} XP para o nível {n + 1}")
    ganho = max(1, int(p.get("hd", 8)) // 2 + 1 + mod(p.get("CON", 10)))
    p["nivel"] = n + 1
    p["hpmax"] = int(p.get("hpmax", 10)) + ganho
    p["hp"] = int(p.get("hp", 0)) + ganho
    if "slots" in p.get("rec", {}):
        p["rec"]["slots"][0] += 1
        p["rec"]["slots"][1] += 1
    _save_pc(p)
    say(f"{p['nome']} → N{n + 1} PV+{ganho} (prof +{prof(p)}). Escolha um novo traço/magia: pj {p['nome']} tracos=…")


# ---------- NPCs, feitos ----------
def cmd_npc(args):
    """npc | npc <id> [att±N|att=N] [div+texto] [div-N] [nota…]  — atitude (-3..+3) e dívidas de NPCs com o grupo"""
    e = est()
    ns = e.setdefault("npcs", {})
    if not args:
        for k, n in ns.items():
            say(f"{n['nome']} {sg(n['att'])} {ATT_NOMES[n['att']]}" + (f" | deve: {'; '.join(n['div'])}" if n["div"] else ""))
        return say("(sem NPCs)") if not ns else None
    n = ns.setdefault(slug(args[0]), {"nome": args[0], "att": 0, "div": []})
    for x in args[1:]:
        m = re.fullmatch(r"att([+\-=])(\d+)", x)
        if m:
            o, v = m.group(1), int(m.group(2))
            n["att"] = max(-3, min(3, v if o == "=" else n["att"] + v if o == "+" else n["att"] - v))
        elif x.startswith("div+"):
            n["div"].append(x[4:])
        elif re.fullmatch(r"div-\d+", x):
            n["div"].pop(int(x[4:]) - 1)
        else:
            cmd_lore(["+", args[0], x])
    jsave("estado.json", e)
    say(f"{n['nome']} {sg(n['att'])} {ATT_NOMES[n['att']]}" + (f" | deve: {'; '.join(n['div'])}" if n["div"] else ""))


def cmd_feito(args):
    """feito "texto"  — grava feito épico/decisão marcante em feitos.md (matéria-prima do /diario); sem args lista os últimos"""
    f = ROOT / "feitos.md"
    if not args:
        ls = f.read_text("utf-8").strip().splitlines() if f.exists() else []
        return say("\n".join(ls[-10:]) or "(sem feitos)")
    e = est()
    with open(f, "a", encoding="utf-8") as h:
        h.write(f"S{e['sessao']}D{e['dia']}: {' '.join(args)}\n")
    say("ok")


# ---------- tabelas do mundo ----------
def cmd_nome(args):
    """nome <cultura|comum> [n]  — sugere nomes (nordico, silvestre, anao, mediterraneo, deserto, tribal, sombrio)"""
    cul = slug(args[0]) if args else "comum"
    n = int(args[1]) if len(args) > 1 else 5
    out = []
    for _ in range(n):
        if cul == "comum":
            nm = random.choice(NOMES_COMUNS)
        elif cul in NOMES:
            a, b = NOMES[cul]
            nm = random.choice(a) + random.choice(b)
        else:
            die(f"cultura '{args[0]}' desconhecida: comum, {', '.join(NOMES)}")
        out.append(nm + (f" {random.choice(EPITETOS)}" if random.random() < .5 else ""))
    say(" · ".join(out))


def cmd_encontro(args):
    """encontro <terreno> [perigo|social|descoberta|cotidiano]  — evento de viagem/exploração"""
    t = slug(args[0]) if args else die(f"uso: encontro <{'|'.join(ENCONTROS)}> [categoria]")
    if t not in ENCONTROS:
        die(f"terreno desconhecido: {', '.join(ENCONTROS)}")
    pool = [x for x in ENCONTROS[t] if len(args) < 2 or x[0] == args[1]] or ENCONTROS[t]
    c, tx = random.choice(pool)
    say(f"[{c}] {tx}")


def cmd_clima(args):
    """clima [temperado|frio|deserto|tropical|mar]  — clima do dia"""
    k = slug(args[0]) if args else "temperado"
    if k not in CLIMAS:
        die(f"clima desconhecido: {', '.join(CLIMAS)}")
    say(random.choice(CLIMAS[k]))


def cmd_rumor(args):
    """rumor [n]  — rumores ligados às facções/NPCs/lugares da campanha, com veracidade secreta (para o GM)"""
    e = est() if (ROOT / "estado.json").exists() else {}
    facs = list(e.get("faccoes", {})) or ["a Guilda", "o Culto da Aurora", "a Guarda"]
    npcs = [n["nome"] for n in e.get("npcs", {}).values()] or [random.choice(NOMES_COMUNS) for _ in range(3)]
    lugares = ([e["local"]] if e.get("local") else []) + LUGARES
    for _ in range(int(args[0]) if args else 1):
        f1 = random.choice(facs)
        f2 = random.choice([x for x in facs if x != f1] or facs)
        tx = random.choice(RUMORES).format(fac=f1, fac2=f2, npc=random.choice(npcs),
                                           lugar=random.choice(lugares), coisa=random.choice(COISAS))
        r = random.randint(1, 6)
        say(f"“{tx}” (GM: {'verdadeiro' if r <= 3 else 'meia-verdade' if r <= 5 else 'falso'})")


def cmd_provisoes(args):
    """provisoes [±N|=N]  — rações do grupo"""
    e = est()
    p = e.setdefault("provisoes", 0)
    for x in args:
        m = re.fullmatch(r"([+\-=])(\d+)", x)
        if m:
            o, v = m.group(1), int(m.group(2))
            p = max(0, v if o == "=" else p + v if o == "+" else p - v)
    e["provisoes"] = p
    jsave("estado.json", e)
    say(f"rações {p}")


def cmd_viagem(args):
    """viagem <dias> <terreno> [clima]  — rola clima/eventos por dia, gasta rações (1/PJ/dia), avança o calendário"""
    if len(args) < 2:
        die("uso: viagem <dias> <terreno> [clima]")
    dias, terr, cl = int(args[0]), slug(args[1]), (slug(args[2]) if len(args) > 2 else "temperado")
    if not 1 <= dias <= 30 or terr not in ENCONTROS or cl not in CLIMAS:
        die(f"dias 1–30; terreno: {', '.join(ENCONTROS)}; clima: {', '.join(CLIMAS)}")
    e = est()
    npj = max(1, sum(1 for p in _pcs() if p.get("hp", 0) > 0))
    for _ in range(dias):
        e["dia"] += 1
        ev = random.choice(ENCONTROS[terr]) if random.randint(1, 6) <= 2 else None
        e["provisoes"] = e.get("provisoes", 0) - npj
        say(f"D{e['dia']}: {random.choice(CLIMAS[cl])} | " + (f"[{ev[0]}] {ev[1]}" if ev else "sem incidentes"))
    if e["provisoes"] < 0:
        say("SEM RAÇÕES: fome — desvantagem em FOR/CON; exaustão após 2 dias assim (cond+Exausto)")
        e["provisoes"] = 0
    jsave("estado.json", e)
    say(f"rações {e['provisoes']}")


def cmd_monstro(args):
    """monstro [tipo [nível] [qtd]]  — bestiário escalado; em combate inicio use '@tipoxQTDnNÍVEL' (ex.: @soldadox3n2)"""
    if not args:
        return say("tipos: " + ", ".join(BEST) + " | atalho no combate: @soldadox3n2")
    tipo = slug(args[0])
    say(monstro_spec(tipo, int(args[1]) if len(args) > 1 else 1, int(args[2]) if len(args) > 2 else 1))


def monstro_spec(tipo, nivel=1, qtd=1):
    if tipo not in BEST:
        die(f"monstro '{tipo}' desconhecido: {', '.join(BEST)}")
    ca, hp, atk, dano, des, dist = BEST[tipo]
    k = nivel - 1
    m = re.fullmatch(r"(\d+)d(\d+)(?:\+(\d+))?", hp)
    n, f, z = int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)
    n, z = n + n * k * 2 // 5, z + z * k * 2 // 5
    nome = tipo.capitalize() + (f"x{qtd}" if qtd > 1 else "")
    return f"{nome}:ca{ca + k // 3}:hp{n}d{f}+{z}:atk{atk + k // 2}:dano{dano}+{k // 2}:des{des}" + (":dist" if dist else "")


def cmd_ctx(args):
    """ctx  — (hook UserPromptSubmit) estima o contexto pelo transcript e avisa perto do limite"""
    try:
        d = json.load(sys.stdin)
        tp = d["transcript_path"]
        raw = Path(tp).read_bytes()
    except Exception:
        return
    i = max(raw.rfind(b"isCompactSummary"), raw.rfind(b"compact_boundary"))
    tok = (len(raw) - (i if i > 0 else 0)) // 3  # estimativa grosseira (JSONL tem sobrecarga)
    lim = int(os.environ.get("RPG_CTX_AVISO", "90000"))
    marca = Path(tp).with_suffix(".rpgctx")
    try:
        ult = int(marca.read_text()) if marca.exists() else 0
    except ValueError:
        ult = 0
    if tok >= lim and tok // 10000 > ult:
        try:
            marca.write_text(str(tok // 10000))
        except OSError:
            pass
        say(f"[RPG] contexto ≈{tok // 1000}k tokens (estimativa). No próximo respiro natural, sugira ao jogador "
            "/salvar e depois /clear (o estado fica em disco).")


# ---------- sessão / memória ----------
def resumo_boot(t, lim=3000):
    """Cabe no limite preservando o cabeçalho (premissa/tom) e cortando o miolo mais antigo."""
    if len(t) <= lim:
        return t
    i = t.find("\n## ")
    head = t[:i] if 0 < i < 800 else t[:400]
    tail = t[-(lim - len(head) - 10):]
    k = tail.find("\n")
    return head + "\n[…]\n" + (tail[k + 1:] if 0 <= k < 200 else tail)


def cmd_boot(args):
    """Contexto mínimo para o início da sessão (usado pelo hook SessionStart)."""
    if not (ROOT / "estado.json").exists():
        return say("[RPG] Sem campanha. Use /mestre para criar uma.")
    e = est()
    say(f"[RPG] {e['campanha']} | S{e['sessao']} D{e['dia']} {e['hora']} @{e['local']}")
    say("CENA:", e["cena"] or "-")
    say("RESUMO:", resumo_boot((ROOT / "resumo.md").read_text("utf-8").strip()))
    cmd_ficha([])
    if e["fios"]:
        say("FIOS:", " | ".join(f"{i}.{f}" for i, f in enumerate(e["fios"][:8], 1)) + (f" (+{len(e['fios']) - 8})" if len(e["fios"]) > 8 else ""))
    if e.get("faccoes"):
        fs = sorted(e["faccoes"].items(), key=lambda kv: -abs(kv[1]["rep"]))[:6]
        say("FACÇÕES:", " | ".join(f"{k}{sg(f['rep'])}({REP_NOMES[f['rep']]})" for k, f in fs))
    ns = [n for n in e.get("npcs", {}).values() if n["att"] or n["div"]]
    if ns:
        ns.sort(key=lambda n: -abs(n["att"]))
        say("NPCS:", " ".join(f"{n['nome']}{sg(n['att'])}" + ("(deve)" if n["div"] else "") for n in ns[:8]))
    if e.get("provisoes"):
        say("RAÇÕES:", e["provisoes"])
    if e["relogios"]:
        say("RELÓGIOS:", " | ".join(f"{k}[{a}/{m}]" for k, (a, m) in e["relogios"].items()))
    if e["flags"]:
        say("FLAGS:", " ".join(f"{k}={v}" for k, v in e["flags"].items()))
    log = (ROOT / "log.md").read_text("utf-8").strip().splitlines()
    if log:
        say("ÚLTIMOS:", " / ".join(l.split(": ", 1)[-1] for l in log[-6:]))
    lore = sorted(f.stem for f in (ROOT / "mundo").glob("*.md"))
    if lore:
        say("LORE(ids):", ", ".join(lore[:30]) + (f" (+{len(lore) - 30}; lore ? termo)" if len(lore) > 30 else ""))
    if e.get("combate"):
        _status(e)
    mem = sum(len(x) for x in OUT) // 4
    say(f"(boot≈{mem} tok; log={len(log)} linhas" + (" — rode /salvar p/ compactar)" if len(log) > 60 else ")"))


def cmd_salvar(args):
    """Snapshot do estado em .saves/ (mantém 10). 'salvar fim' também avança a sessão."""
    e = est()
    if args and args[0] == "fim":
        e["sessao"] += 1
        jsave("estado.json", e)
    sv = ROOT / ".saves"
    sv.mkdir(exist_ok=True)
    nome = sv / f"{time.strftime('%Y%m%d-%H%M%S')}-S{e['sessao']}.tgz"
    with tarfile.open(nome, "w:gz") as t:
        for f in ROOT.iterdir():
            if f.name not in (".saves", ".undo"):
                t.add(f, arcname=f.name)
    for old in sorted(sv.glob("*.tgz"))[:-10]:
        old.unlink()
    say("salvo:", nome.name)


def cmd_carregar(args):
    """carregar | carregar N  — lista/restaura snapshot"""
    sv = sorted((ROOT / ".saves").glob("*.tgz"))
    if not args:
        for i, f in enumerate(sv, 1):
            say(f"{i}. {f.name}")
        return
    f = sv[int(args[0]) - 1]
    with tarfile.open(f) as t:
        t.extractall(ROOT, filter="data")
    say("carregado:", f.name)


def cmd_compactar(args):
    """compactar  → move log.md para arquivo/S<n>.md e zera (rode após atualizar resumo.md)."""
    log = ROOT / "log.md"
    arq = ROOT / "arquivo"
    arq.mkdir(exist_ok=True)
    e = est()
    with open(arq / f"S{e['sessao']}.md", "a", encoding="utf-8") as f:
        f.write(log.read_text("utf-8"))
    log.write_text("", "utf-8")
    say(f"log arquivado em arquivo/S{e['sessao']}.md")


READONLY = {"boot", "ficha", "rolar", "r", "oraculo", "ajuda", "-h", "desfazer", "ctx", "nome", "encontro",
            "clima", "rumor", "monstro", "teste", "t"}


def snapshot_undo():
    if not (ROOT / "estado.json").exists():
        return
    u = ROOT / ".undo"
    u.mkdir(exist_ok=True)
    with tarfile.open(u / f"{time.time_ns()}.tgz", "w:gz") as t:
        for f in ROOT.iterdir():
            if f.name not in (".saves", ".undo"):
                t.add(f, arcname=f.name)
    for old in sorted(u.glob("*.tgz"))[:-8]:
        old.unlink()


def precisa_snapshot(argv):
    if not argv:
        return False
    partes = [shlex.split(p) for p in " ".join(argv[1:]).split(";")] if argv[0] == "x" else [argv]
    return any(p and p[0] not in READONLY for p in partes)


def cmd_desfazer(args):
    """desfazer [N]  — volta o estado ao antes das últimas N alterações (até 8)"""
    n = int(args[0]) if args else 1
    snaps = sorted((ROOT / ".undo").glob("*.tgz")) if (ROOT / ".undo").exists() else []
    if not snaps or n > len(snaps):
        die(f"nada para desfazer (disponíveis: {len(snaps)})")
    alvo = snaps[-n]
    for f in list(ROOT.iterdir()):
        if f.name not in (".saves", ".undo"):
            shutil.rmtree(f) if f.is_dir() else f.unlink()
    with tarfile.open(alvo) as t:
        t.extractall(ROOT, filter="data")
    for old in snaps[-n:]:
        old.unlink()
    say(f"desfeito ({n}); restam {len(snaps) - n} níveis de desfazer")


CMDS = {
    "nova": cmd_nova, "rolar": cmd_rolar, "r": cmd_rolar, "atributos": cmd_atributos, "pj": cmd_pj,
    "ficha": cmd_ficha, "teste": cmd_teste, "t": cmd_teste, "cena": cmd_cena, "fio": cmd_fio,
    "relogio": cmd_relogio, "flag": cmd_flag, "log": cmd_log, "lore": cmd_lore, "combate": cmd_combate,
    "turno": cmd_turno, "oraculo": cmd_oraculo, "ataque": cmd_ataque, "a": cmd_ataque, "boot": cmd_boot, "salvar": cmd_salvar,
    "honra": cmd_honra, "heroi": cmd_heroi, "recurso": cmd_recurso, "descanso": cmd_descanso, "cura": cmd_cura,
    "morte": cmd_morte, "subir": cmd_subir, "npc": cmd_npc, "feito": cmd_feito, "nome": cmd_nome, "encontro": cmd_encontro,
    "clima": cmd_clima, "rumor": cmd_rumor, "provisoes": cmd_provisoes, "viagem": cmd_viagem, "monstro": cmd_monstro,
    "mover": cmd_mover, "desfazer": cmd_desfazer, "ctx": cmd_ctx, "faccao": cmd_faccao, "carregar": cmd_carregar, "compactar": cmd_compactar,
}


def run(argv):
    if not argv or argv[0] in ("-h", "ajuda"):
        for k, f in CMDS.items():
            if f.__doc__ and k not in ("r", "t", "a"):
                say(f"{k}: {f.__doc__.strip().splitlines()[0]}")
        return
    if argv[0] == "x":  # lote: "cmd1; cmd2"
        for part in " ".join(argv[1:]).split(";"):
            if part.strip():
                try:
                    run(shlex.split(part))
                except SystemExit as ex:  # um erro não aborta o lote
                    OUT.append(str(ex.code))
        return
    c = CMDS.get(argv[0]) or die(f"comando '{argv[0]}' desconhecido (rpg.py ajuda)")
    c(argv[1:])


if __name__ == "__main__":
    try:
        if precisa_snapshot(sys.argv[1:]):
            snapshot_undo()
    except Exception:
        pass
    try:
        run(sys.argv[1:])
    except SystemExit as ex:
        if ex.code not in (None, 0):
            OUT.append(str(ex.code))
    if OUT:
        print("\n".join(OUT))
