#!/usr/bin/env python3
"""rpg.py — motor determinístico do Mestre. Só stdlib.

Toda matemática, dado e estado mora aqui; o modelo só narra.
Saídas são deliberadamente curtas (cada caractere vira token de entrada).
Vários comandos numa chamada: rpg.py x "rolar 1d20+3; pj kael hp-4; log Kael caiu"
"""
import json, os, random, re, shlex, sys, tarfile, time
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
    return f"{p['nome']} N{p.get('nivel', 1)} {p.get('raca', '')} {p.get('classe', '')} PV{hp} CA{p.get('ca', '?')} | {at}" + (
        " | " + " ".join(extra) if extra else "")


def cmd_pj(args):
    """pj novo <nome> k=v...  |  pj <id> campo±valor ...  |  pj <id> campo=valor"""
    if not args:
        die("uso: pj novo <nome> k=v... | pj <id> hp-5 po+10 item+Corda cond+Caído")
    if args[0] == "novo":
        nome = args[1]
        p = {"nome": nome, "nivel": 1, "xp": 0, "po": 0, "itens": [], "cond": [], "pericias": [], "resist": []}
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
    if is_pc:
        jsave(pj_path(args[0]), p)
    else:  # combatente temporário
        e = est()
        for i, c in enumerate(e["combate"]["ordem"]):
            if slug(c["nome"]) == slug(p["nome"]):
                e["combate"]["ordem"][i] = p
        jsave("estado.json", e)
    say(ficha_curta(p) if is_pc else f"{p['nome']} PV{p['hp']}/{p.get('hpmax')}" + (" CAÍDO" if p["hp"] == 0 else ""))


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
    r, s = d20(vd)
    tot = r + b + extra
    res = "" if cd is None else (" ✓" if tot >= cd else " ✗")
    crit = " CRÍTICO" if r == 20 else " FALHA CRÍTICA" if r == 1 else ""
    say(f"{p['nome']} {nome} {s}{sg(b + extra)}={tot}" + (f" vs CD{cd}" if cd else "") + res + crit)


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
                          "cena": "", "fios": [], "relogios": {}, "flags": {}, "combate": None})
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
                ordem.append({"nome": p["nome"], "pj": True, "ini": r + mod(p.get("DES", 10)), "d": r})
        for spec in args[1:]:
            parts = spec.split(":")
            base, qtd = re.fullmatch(r"(.+?)(?:x(\d+))?", parts[0]).groups()
            qtd = qtd or "1"
            stats = dict(re.match(r"([a-z]+)(.*)", s).groups() for s in parts[1:])
            for i in range(int(qtd)):
                nome = base if int(qtd) == 1 else f"{base}{i + 1}"
                hp = roll(stats["hp"])[0] if "d" in stats.get("hp", "") else int(stats.get("hp", 5))
                r = random.randint(1, 20)
                ordem.append({"nome": nome, "pj": False, "hp": hp, "hpmax": hp, "ca": int(stats.get("ca", 10)),
                              "atk": int(stats.get("atk", 2)), "dano": stats.get("dano", "1d6"),
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


def _status(e):
    cb = e["combate"]
    linha = []
    for i, c in enumerate(cb["ordem"]):
        hp, mx = _hp(c)
        mark = "▶" if i == cb["vez"] else ""
        linha.append(f"{mark}{c['nome']}({c['ini']}) {hp}/{mx}" + ((" caído" if c.get("pj") else "✝") if hp <= 0 else ""))
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
    """ataque <atacante> <alvo> [vant|desv] [+N] [dano=1d8+3]  (PJ usa campo atk/dano da ficha)"""
    if len(args) < 2:
        die("uso: ataque <atacante> <alvo> [vant|desv] [+N] [dano=XdY+Z]")
    a, t = pj_load(args[0]), pj_load(args[1])
    vd = next((x for x in args[2:] if x in ("vant", "desv")), None)
    extra = sum(int(x) for x in args[2:] if x[0] in "+-" and x[1:].isdigit())
    dano = next((x.split("=", 1)[1] for x in args[2:] if x.startswith("dano=")), a.get("dano", "1d6"))
    atk = int(a.get("atk", prof(a) + max(mod(a.get("FOR", 10)), mod(a.get("DES", 10))))) + extra
    r, s = d20(vd)
    tot = r + atk
    ca = int(t.get("ca", 10))
    if r == 1 or (tot < ca and r != 20):
        return say(f"{a['nome']}→{t['nome']} {s}{sg(atk)}={tot} vs CA{ca} ERROU")
    if r == 20:  # crítico: dobra os dados
        dano = re.sub(r"(\d*)d(\d+)", lambda m: f"{int(m.group(1) or 1) * 2}d{m.group(2)}", dano)
    dn, ds = roll(dano)
    dn = max(1, dn)
    say(f"{a['nome']}→{t['nome']} {s}{sg(atk)}={tot} vs CA{ca} {'CRÍTICO' if r == 20 else 'ACERTOU'} dano {ds}")
    cmd_pj([args[1], f"hp-{dn}"])


# ---------- sessão / memória ----------
def cmd_boot(args):
    """Contexto mínimo para o início da sessão (usado pelo hook SessionStart)."""
    if not (ROOT / "estado.json").exists():
        return say("[RPG] Sem campanha. Use /mestre para criar uma.")
    e = est()
    say(f"[RPG] {e['campanha']} | S{e['sessao']} D{e['dia']} {e['hora']} @{e['local']}")
    say("CENA:", e["cena"] or "-")
    resumo = (ROOT / "resumo.md").read_text("utf-8").strip()
    say("RESUMO:", resumo[-2400:] if len(resumo) > 2400 else resumo)
    cmd_ficha([])
    if e["fios"]:
        say("FIOS:", " | ".join(f"{i}.{f}" for i, f in enumerate(e["fios"], 1)))
    if e["relogios"]:
        say("RELÓGIOS:", " | ".join(f"{k}[{a}/{m}]" for k, (a, m) in e["relogios"].items()))
    if e["flags"]:
        say("FLAGS:", " ".join(f"{k}={v}" for k, v in e["flags"].items()))
    log = (ROOT / "log.md").read_text("utf-8").strip().splitlines()
    if log:
        say("ÚLTIMOS:", " / ".join(l.split(": ", 1)[-1] for l in log[-6:]))
    lore = sorted(f.stem for f in (ROOT / "mundo").glob("*.md"))
    if lore:
        say("LORE(ids):", ", ".join(lore))
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
            if f.name != ".saves":
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


CMDS = {
    "nova": cmd_nova, "rolar": cmd_rolar, "r": cmd_rolar, "atributos": cmd_atributos, "pj": cmd_pj,
    "ficha": cmd_ficha, "teste": cmd_teste, "t": cmd_teste, "cena": cmd_cena, "fio": cmd_fio,
    "relogio": cmd_relogio, "flag": cmd_flag, "log": cmd_log, "lore": cmd_lore, "combate": cmd_combate,
    "turno": cmd_turno, "oraculo": cmd_oraculo, "ataque": cmd_ataque, "a": cmd_ataque, "boot": cmd_boot, "salvar": cmd_salvar,
    "carregar": cmd_carregar, "compactar": cmd_compactar,
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
        run(sys.argv[1:])
    except SystemExit as ex:
        if ex.code not in (None, 0):
            OUT.append(str(ex.code))
    print("\n".join(OUT))
