# -*- coding: utf-8 -*-
"""Linhas das casas dele no CS2 (12/11/2026, Fase 1): serie e mapa, do catalogo da OddsPapi."""
import json
import unittest
from pathlib import Path

import coletar_casas_cs as cc


def _m(mid, nome, periodo, handicap, outs, n=2):
    return {"marketId": mid, "marketName": nome, "period": periodo, "handicap": handicap, "marketLength": n,
            "outcomes": [{"outcomeId": i, "outcomeName": o} for i, o in outs]}


def _o(price):
    return {"players": {"0": {"price": price}}}


CAT = [
    _m(1, "Maps Handicap", "result", -1.5, [(11, "1"), (12, "2")]),
    _m(2, "Total Maps Over Under", "result", 2.5, [(21, "Over"), (22, "Under")]),
    _m(3, "Correct Map Score", "result", 0.0, [(31, "2:0"), (32, "2:1"), (33, "1:2"), (34, "0:2")], n=0),
    _m(4, "Total Rounds First Map", "p1", 21.5, [(41, "Over"), (42, "Under")]),
    _m(5, "Rounds Handicap Second Map", "p2", -3.5, [(51, "1"), (52, "2")]),
    _m(6, "Team 2 Total Rounds Third Map", "p3", 10.5, [(61, "Over"), (62, "Under")]),
    _m(7, "Will There Be Overtime First Map", "p1", 0.0, [(71, "Yes"), (72, "No")]),
    _m(8, "Winner First Map Round 1", "p1r1", 0.0, [(81, "1"), (82, "2")]),
    _m(9, "Headshots - Over Under First Map", "p1", 30.5, [(91, "Over"), (92, "Under")]),
    _m(10, "Kills - Over Under Team 1 First Map", "p1", 70.5, [(101, "Over"), (102, "Under")]),
]


class TestCatalogo(unittest.TestCase):
    def test_serie_e_mapa(self):
        c = cc.catalogo_de_linhas(CAT)
        self.assertEqual(c["1"], ("maps", "spread", 0, -1.5, ("11", "12"), None))
        self.assertEqual(c["2"], ("maps", "total", 0, 2.5, ("21", "22"), None))
        self.assertEqual(sorted(x[3] for x in c["3"]), [20.0, 21.0])        # 2:0 e 2:1
        self.assertEqual(c["4"], ("rounds", "total", 1, 21.5, ("41", "42"), None))
        self.assertEqual(c["5"], ("rounds", "spread", 2, -3.5, ("51", "52"), None))
        self.assertEqual(c["6"], ("rounds", "team_total", 3, 10.5, ("61", "62"), 2))
        self.assertEqual(c["7"], ("overtime", "simnao", 1, 0.0, ("71", "72"), None))
        self.assertEqual(c["10"], ("kills", "team_total", 1, 70.5, ("101", "102"), 1))
        self.assertNotIn("8", c)        # vencedor de round: fora
        self.assertNotIn("9", c)        # headshots: fora

    def test_linhas_so_das_casas_dele(self):
        c = cc.catalogo_de_linhas(CAT)
        od = {"bookmakerOdds": {
            "stake": {"markets": {"1": {"outcomes": {"11": _o(2.2), "12": _o(1.62)}},
                                  "3": {"outcomes": {"31": _o(3.1), "34": _o(5.0), "32": _o(4.0), "33": _o(4.5)}},
                                  "4": {"outcomes": {"41": _o(1.85), "42": _o(1.0)}}}},
            "unibet": {"markets": {"1": {"outcomes": {"11": _o(2.2), "12": _o(1.6)}}}}}}
        lin = cc.linhas_das_casas(od, c)
        self.assertEqual(list(lin), ["stake"])
        self.assertIn(["maps", "spread", 0, -1.5, 2.2, 1.62, None], lin["stake"])
        self.assertIn(["maps", "placar", 0, 20.0, 3.1, 5.0, None], lin["stake"])
        self.assertFalse(any(l[0] == "rounds" for l in lin["stake"]))       # odd 1.0 = sem preco
        r = cc.resumo_do_catalogo(CAT, [od])
        self.assertEqual(r[0]["casas"], ["stake"])

    def test_linha_principal(self):
        self.assertTrue(cc.linha_principal([1.85, 1.95]))
        self.assertFalse(cc.linha_principal([1.08, 7.5]))

    def test_catalogo_real_da_sonda(self):
        p = Path(__file__).with_name("sonda_oddspapi.json")
        if not p.exists():
            self.skipTest("sem a sonda local")
        c = cc.catalogo_de_linhas(json.loads(p.read_text(encoding="utf-8"))["markets_CS2"])
        tipos = {(v[0], v[1], v[2] > 0) for v in c.values() if not isinstance(v, list)}
        for esperado in (("maps", "spread", False), ("maps", "total", False), ("rounds", "total", True),
                         ("rounds", "spread", True), ("rounds", "team_total", True), ("overtime", "simnao", True)):
            self.assertIn(esperado, tipos)
        self.assertTrue(any(isinstance(v, list) for v in c.values()))        # placar exato


if __name__ == "__main__":
    unittest.main()
