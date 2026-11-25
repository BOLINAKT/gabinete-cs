# -*- coding: utf-8 -*-
"""c movel do MAPA (25/11/2026): confiante demais -> c < 1; so os 12 meses anteriores; so S/A/B."""
import random
import unittest

import pandas as pd

import calibra_movel as cm


class TestCMapa(unittest.TestCase):

    def test_confiante_demais_da_c_menor_que_1_e_respeita_janela_e_tier(self):
        rnd = random.Random(1)
        mapas = {}
        for i in range(3000):          # o modelo diz 80% mas o time ganha 65%
            mapas[i] = (pd.Timestamp("2026-03-01") + pd.Timedelta(hours=i), "A", 0.8, int(rnd.random() < 0.65))
        c = cm.c_mapa_atual(mapas, "2026-08-01")
        self.assertLess(c, 0.9)
        self.assertEqual(cm.c_mapa_atual(mapas, "2026-02-01"), 1.0)          # nada antes de fev: c = 1
        so_c = {k: (dt, "C", p, y) for k, (dt, _t, p, y) in mapas.items()}
        self.assertEqual(cm.c_mapa_atual(so_c, "2026-08-01"), 1.0)           # tier C nao conta


if __name__ == "__main__":
    unittest.main()
