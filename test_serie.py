# -*- coding: utf-8 -*-
"""A serie coerente do CS (Fase 2, 12/11/2026)."""
import unittest

import serie_cs as sc


class TestSerie(unittest.TestCase):
    def test_tudo_bate_com_a_chance_da_serie(self):
        for bo in (3, 5):
            for k in (None, 6):
                m = sc.mapa_coerente(0.75, bo, k)
                self.assertAlmostEqual(sc.p_serie(m, bo, k), 0.75, places=6)
                self.assertAlmostEqual(sum(sc.placares(m, bo, k).values()), 1.0, places=9)
                mk = sc.mercados(0.75, bo, k)
                self.assertLess(mk["time1 -1.5"], 0.75)
                self.assertGreater(mk["time1 +1.5"], 0.75)

    def test_forma_do_dia_aumenta_a_varrida(self):
        ind = sc.mercados(0.7, 3, None)
        dia = sc.mercados(0.7, 3, 6)
        self.assertGreater(dia["time1 -1.5"], ind["time1 -1.5"])
        self.assertLess(dia["mapas mais de 2.5"], ind["mapas mais de 2.5"])
        self.assertAlmostEqual(dia["time1 -1.5"], dia["placar 2-0"], places=9)

    def test_mercados_da_serie_com_a_pinnacle(self):
        linhas = [
            {"matchup": 7, "periodo": 0, "tipo": "spread", "lado": "home", "pontos": -1.5, "odd": 2.7},
            {"matchup": 7, "periodo": 0, "tipo": "spread", "lado": "away", "pontos": 1.5, "odd": 1.43},
            {"matchup": 7, "periodo": 0, "tipo": "total", "lado": "over", "pontos": 2.5, "odd": 2.02},
            {"matchup": 7, "periodo": 0, "tipo": "total", "lado": "under", "pontos": 2.5, "odd": 1.77},
            {"matchup": 8, "periodo": 0, "tipo": "spread", "lado": "home", "pontos": 1.5, "odd": 1.2},
            {"matchup": 7, "periodo": 1, "tipo": "spread", "lado": "home", "pontos": -3.5, "odd": 1.9}]
        ms = sc.mercados_da_serie(0.6, 3, 6, linhas, 7, "A", "B")
        nomes = [m["mercado"] for m in ms]
        self.assertEqual(nomes, ["Mapas ±1,5", "Mapas ±1,5", "Total de mapas", "Placar exato", "Placar exato"])
        a, b = ms[0]["lados"]
        self.assertEqual((a["rotulo"], b["rotulo"]), ("A −1,5", "B +1,5"))
        self.assertEqual((a["odd_pinnacle"], b["odd_pinnacle"]), (2.7, 1.43))
        self.assertAlmostEqual(a["p_modelo"] + b["p_modelo"], 1.0)
        self.assertAlmostEqual(a["p_pinnacle"] + b["p_pinnacle"], 1.0)
        self.assertIsNone(ms[1]["lados"][0]["odd_pinnacle"])            # A +1,5: a Pinnacle nao abriu
        self.assertEqual(ms[2]["lados"][0]["odd_pinnacle"], 2.02)
        self.assertEqual(sc.mercados_da_serie(0.6, 1, 6, linhas, 7, "A", "B"), [])


if __name__ == "__main__":
    unittest.main()
