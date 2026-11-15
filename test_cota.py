# -*- coding: utf-8 -*-
"""A cota da OddsPapi (15/11/2026): 250 chamadas por mes para os tres robos."""
import unittest
from datetime import date

import coletar_casas_cs as cc


class TestCota(unittest.TestCase):
    def test_cota_da_assinatura_ativa(self):
        conta = {"subscriptions": [{"is_active": False, "request_limit": 9, "request_count": 1},
                                   {"is_active": True, "request_limit": 250, "request_count": 301}]}
        self.assertEqual(cc.cota(conta), (250, 301))
        self.assertEqual(cc.cota({}), (None, None))

    def test_orcamento_divide_o_que_resta_pelos_dias_e_esportes(self):
        self.assertEqual(cc.orcamento(250, 0, date(2026, 12, 1)), 2)       # (250-12)/31/3 = 2,5
        self.assertEqual(cc.orcamento(250, 301, date(2026, 11, 15)), 0)    # estourada
        self.assertEqual(cc.orcamento(250, 100, date(2026, 12, 25)), 6)    # sobrou: gasta mais no fim
        self.assertEqual(cc.orcamento(250, 0, date(2026, 12, 1), n_esportes=1), 7)
        self.assertEqual(cc.orcamento(None, None, date(2026, 12, 1)), 2)   # conta fora do ar: o minimo

    def test_plano_jogo_a_jogo_quando_cabe_senao_lotes_de_torneios(self):
        fx = [{"fixtureId": f"f{i}", "tournamentId": 10 + i // 2, "startTime": f"2026-12-01T{10 + i:02d}:00"} for i in range(8)]
        self.assertEqual(cc.plano_de_coleta(fx[:2], 3), ("jogos", fx[:2]))
        modo, lotes = cc.plano_de_coleta(fx, 1)
        self.assertEqual((modo, lotes), ("lotes", [[10, 11, 12]]))          # os torneios com jogo mais cedo
        self.assertEqual(cc.plano_de_coleta(fx, 0), ("nada", []))
        self.assertEqual(cc.plano_de_coleta([], 5), ("nada", []))

    def test_catalogo_versionado(self):
        c = cc.carregar_catalogo()
        self.assertGreater(len(c), 1000)
        tipos = {(v[0], v[1]) for v in c.values() if isinstance(v, tuple)}
        self.assertIn(("maps", "spread"), tipos)
        self.assertIn(("rounds", "total"), tipos)


if __name__ == "__main__":
    unittest.main()
