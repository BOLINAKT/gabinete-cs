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


if __name__ == "__main__":
    unittest.main()
