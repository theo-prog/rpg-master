import os, subprocess, sys, tempfile, unittest
from pathlib import Path

RPG = Path(__file__).resolve().parent.parent / "tools" / "rpg.py"


class TestRPG(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def run_rpg(self, *a):
        env = dict(os.environ, RPG_DIR=self.dir)
        return subprocess.run([sys.executable, str(RPG), *a], capture_output=True, text=True, env=env).stdout

    def test_fluxo_basico(self):
        self.assertIn("criada", self.run_rpg("nova", "Teste"))
        self.run_rpg("pj", "novo", "Ana", "DES=16", "SAB=12", "hp=10", "ca=13", "atk=5", "dano=1d6+3",
                     "pericias=furtividade")
        self.assertIn("+5", self.run_rpg("teste", "ana", "furtividade"))
        out = self.run_rpg("x", "pj ana hp-4 item+Corda; pj ana hp-99")
        self.assertIn("PV6/10", out)
        self.assertIn("PV0/10", out)
        self.assertIn("Caído", out)
        self.assertIn("Teste", self.run_rpg("boot"))

    def test_honra_e_faccoes(self):
        self.run_rpg("nova", "H")
        self.run_rpg("pj", "novo", "Kael", "hp=10", "codigo=Nunca ferir desarmados")
        out = self.run_rpg("x", 'honra kael +2 "poupou o prisioneiro"; honra kael +9; honra kael -99')
        self.assertIn("honra +2 (respeitada)", out)
        self.assertIn("honra +5 (lendária)", out)
        self.assertIn("honra -5 (desonrada)", out)
        out = self.run_rpg("x", 'faccao "Guarda Cinzenta" rep+2 "quer a coroa"; faccao "Guarda Cinzenta" rep-9; faccao')
        self.assertIn("+2 aliada — quer a coroa", out)
        self.assertIn("-3 inimiga jurada", out)
        boot = self.run_rpg("boot")
        self.assertIn("FACÇÕES: Guarda Cinzenta-3", boot)
        self.assertIn("honra-5", boot)
        with open(os.path.join(self.dir, "log.md"), encoding="utf-8") as f:
            self.assertIn("poupou o prisioneiro", f.read())

    def test_heroi_recursos_descanso_nivel(self):
        self.run_rpg("nova", "H")
        out = self.run_rpg("heroi", "Mira", "mago", "raca=elfa")
        self.assertIn("Mago PV8/8", out)
        self.assertIn("slots2/2", out)
        self.assertIn("ERRO", self.run_rpg("x", "recurso mira slots -1; recurso mira slots -1; recurso mira slots -1"))
        self.assertIn("slots 2/2", self.run_rpg("x", "descanso longo; recurso mira"))
        self.assertIn("ERRO", self.run_rpg("subir", "mira"))
        out = self.run_rpg("x", "pj mira xp+300")
        self.assertIn("pode subir de nível", out)
        out = self.run_rpg("subir", "mira")
        self.assertIn("N2", out)
        self.assertIn("slots 3/3", self.run_rpg("recurso", "mira"))

    def test_morte_cura_condicoes(self):
        self.run_rpg("nova", "M")
        self.run_rpg("heroi", "Kael", "guerreiro")
        out = self.run_rpg("x", "pj kael hp-99; cura kael 1d4+4; pj kael cond+Envenenado; teste kael atletismo")
        self.assertIn("Caído", out)
        self.assertNotIn("cond:Caído", out.split("cura")[1])
        self.assertIn("Envenenado→desv", out)
        self.run_rpg("pj", "kael", "hp-99")
        for _ in range(8):
            out = self.run_rpg("morte", "kael")
        self.assertTrue("ESTÁVEL" in out or "MORTO" in out or "já morreu" in out or "estável" in out or "volta" in out)

    def test_combate_zonas_manobras_bestiario(self):
        self.run_rpg("nova", "Z")
        self.run_rpg("heroi", "Zed", "ladino")
        self.run_rpg("heroi", "Kael", "guerreiro")
        self.run_rpg("x", 'combate inicio "@capangax2n2" "Arq:ca10:hp5:atk2:dano1d4:dist:zonafundo"')
        self.assertIn("não alcança", self.run_rpg("ataque", "kael", "arq"))
        self.assertIn("ERRO", self.run_rpg("ataque", "kael", "capanga1", "man=finalizar"))
        self.assertIn("ERRO", self.run_rpg("ataque", "kael", "capanga1", "furtivo"))
        self.assertIn("fundo", self.run_rpg("mover", "kael", "fundo"))
        self.assertIn("Arq", self.run_rpg("ataque", "kael", "arq", "man=poderoso"))
        self.assertIn("ERRO", self.run_rpg("monstro", "dragaozinho"))
        self.assertIn("hp", self.run_rpg("monstro", "soldado", "3", "2"))

    def test_desfazer(self):
        self.run_rpg("nova", "D")
        self.run_rpg("heroi", "Kael", "guerreiro")
        self.run_rpg("pj", "kael", "hp-5")
        self.assertIn("PV7/12", self.run_rpg("ficha", "kael"))
        self.assertIn("desfeito", self.run_rpg("desfazer"))
        self.assertIn("PV12/12", self.run_rpg("ficha", "kael"))
        self.assertIn("ERRO", self.run_rpg("desfazer", "9"))

    def test_mundo(self):
        self.run_rpg("nova", "W")
        self.assertIn("[", self.run_rpg("encontro", "floresta"))
        self.assertIn("ERRO", self.run_rpg("encontro", "lua"))
        self.assertEqual(len(self.run_rpg("nome", "nordico", "4").split(" · ")), 4)
        self.run_rpg("heroi", "A", "bardo")
        out = self.run_rpg("x", "provisoes =3; viagem 4 estrada; provisoes")
        self.assertIn("SEM RAÇÕES", out)
        self.assertIn("GM:", self.run_rpg("rumor"))
        out = self.run_rpg("x", 'npc Brum att+9 div+salvou-o "bebe"; feito "Salvaram a vila"; feito')
        self.assertIn("Brum +3 devoto | deve: salvou-o", out)
        self.assertIn("Salvaram a vila", out)
        self.assertIn("NPCS: Brum+3(deve)", self.run_rpg("boot"))

    def test_boot_preserva_cabecalho(self):
        self.run_rpg("nova", "B")
        with open(os.path.join(self.dir, "resumo.md"), "w", encoding="utf-8") as f:
            f.write("# B\nPREMISSA-E-TOM\n\n## Arco\n" + " ".join(["palavracomum"] * 700) + " FIM")
        boot = self.run_rpg("boot")
        self.assertIn("PREMISSA-E-TOM", boot)
        self.assertIn("FIM", boot)
        self.assertIn("[…]", boot)

    def test_dados(self):
        for _ in range(50):
            t = int(self.run_rpg("rolar", "4d6kh3").rsplit("=", 1)[1])
            self.assertTrue(3 <= t <= 18)
        self.assertIn("ERRO", self.run_rpg("rolar", "abc"))

    def test_combate(self):
        self.run_rpg("nova", "C")
        self.run_rpg("pj", "novo", "Bo", "hp=10", "ca=12", "atk=4", "dano=1d8")
        out = self.run_rpg("x", 'combate inicio "Rato:ca10:hp3:atk2:dano1d4"; ataque bo rato; turno; combate fim')
        self.assertIn("R1", out)
        self.assertIn("encerrado", out)


if __name__ == "__main__":
    unittest.main()
