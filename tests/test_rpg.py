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
