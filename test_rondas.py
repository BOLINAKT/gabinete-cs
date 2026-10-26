# -*- coding: utf-8 -*-
"""Modelo de rounds: regras do CS2 e as linhas da Pinnacle."""
import unittest

import precos_core as pc
import rondas as rd


class TestRondas(unittest.TestCase):
    def test_placar_soma_1_e_respeita_mr12(self):
        d = rd.placar_q(0.5)
        self.assertAlmostEqual(sum(d.values()), 1.0, places=6)
        self.assertAlmostEqual(rd.p_vence(d), 0.5, places=6)
        for (a, b), v in d.items():
            w, l = max(a, b), min(a, b)
            self.assertTrue((w == 13 and l <= 11) or (w >= 16 and (w - 13) % 3 == 0 and 2 <= w - l <= 4), (a, b))

    def test_tabela_acha_a_chance_do_mapa(self):
        t = rd.Tabela(25)
        self.assertAlmostEqual(rd.p_vence(t.dist(0.65)), 0.65, delta=0.004)

    def test_linhas_da_pinnacle(self):
        dist = {(13, 5): 0.5, (10, 13): 0.5}
        self.assertEqual(pc.p_linha_rounds(dist, "total", "over", 21.5, None), 0.5)     # 23 rounds
        self.assertEqual(pc.p_linha_rounds(dist, "spread", "home", -2.5, None), 0.5)    # 13-5
        self.assertEqual(pc.p_linha_rounds(dist, "spread", "away", 2.5, None), 0.5)     # so no 10-13
        self.assertEqual(pc.p_linha_rounds(dist, "team_total", "over", 11.5, "away"), 0.5)
        self.assertIsNone(pc.p_linha_rounds(dist, "team_total", "over", 11.5, None))


if __name__ == "__main__":
    unittest.main()
