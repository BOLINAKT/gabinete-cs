# -*- coding: utf-8 -*-
"""Odds de outras casas (OddsPapi): leitura dos mercados e casas dele."""
import unittest

import coletar_casas_cs as cc


def _o(price, active=True):
    return {"players": {"0": {"price": price, "active": active}}}


class TestCasas(unittest.TestCase):
    def test_le_serie_e_mapa_e_ignora_suspensa(self):
        od = {"bookmakerOdds": {
            "bet365": {"bookmakerIsActive": True, "markets": {
                "171": {"outcomes": {"171": _o(1.8), "172": _o(2.0)}},
                "1747": {"outcomes": {"1747": _o(1.7), "1748": _o(2.1)}},
                "999": {"outcomes": {"1": _o(3.0)}}}},
            "blaze": {"bookmakerIsActive": True, "suspended": True, "markets": {
                "171": {"outcomes": {"171": _o(1.9), "172": _o(1.9)}}}},
            "superbet": {"bookmakerIsActive": True, "markets": {
                "171": {"outcomes": {"171": _o(1.9, active=False), "172": _o(1.9)}}}}}}
        p = cc.precos(od)
        self.assertEqual(p, {"bet365": {"171": [1.8, 2.0], "1747": [1.7, 2.1]}})

    def test_casas_dele_pelo_prefixo(self):
        for s in ("bet365.bet.br", "estrelabet.bet.br", "blaze", "polymarket.us", "pinnacle"):
            self.assertTrue(cc.e_casa_dele(s), s)
        self.assertFalse(cc.e_casa_dele("1xbet"))


class TestOutrasCasas(unittest.TestCase):
    def test_orientacao_invertida_e_pinnacle_do_mesmo_instante(self):
        import precos_core as pc

        class E:
            def casar(self, n):
                return ({"Time A": "A", "Time B": "B"}[n], "exato")
        jogo = {"inicio_utc": "2026-10-28T11:00:00Z", "casou": [("A", "exato"), ("B", "exato")],
                "mercados": [{"periodo": 0, "lados": [{"p_pinnacle": 0.9, "p_modelo": 0.6}, {}]}]}
        # na OddsPapi o time1 e o B: tudo tem de ser invertido para a orientacao do app
        casas = [{"time1": "Time B", "time2": "Time A", "inicio_utc": "2026-10-28T11:00:00Z",
                  "casas": {"pinnacle": {"171": [2.0, 2.0]}, "bet365": {"171": [1.8, 2.2]}}}]
        ls = {l["casa"]: l for l in pc.outras_casas(jogo, casas, E())}
        self.assertEqual((ls["bet365"]["odd_casa"], ls["bet365"]["odd_fora"]), (2.2, 1.8))
        # justo da Pinnacle da OddsPapi (50%), nao o do robo (90%): 0,5*2,2-1 = +10%
        self.assertAlmostEqual(ls["bet365"]["valor_pin_casa"], 10.0)
        self.assertAlmostEqual(ls["bet365"]["valor_mod_casa"], 32.0)


if __name__ == "__main__":
    unittest.main()
