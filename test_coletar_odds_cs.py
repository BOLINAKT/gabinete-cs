# -*- coding: utf-8 -*-
"""Leitura dos jogos e linhas de CS2 da resposta da Pinnacle (formato do coletor do LoL)."""
import unittest

from coletar_odds_cs import _decimal, jogos_e_linhas

MATCHUPS = [
    {"id": 1, "league": {"name": "CS2 - PGL Masters Bucharest"}, "bestOfX": 3, "startTime": "2026-10-27T10:00:00Z",
     "participants": [{"alignment": "home", "name": "FURIA"}, {"alignment": "away", "name": "MOUZ"}]},
    {"id": 2, "parentId": 1, "league": {"name": "CS2 - PGL Masters Bucharest"}},
    {"id": 3, "league": {"name": "League of Legends - LCK"}, "participants": []},
]
MERCADOS = [
    {"matchupId": 1, "type": "moneyline", "period": 0, "prices": [{"designation": "home", "price": -150},
                                                                   {"designation": "away", "price": 120}]},
    {"matchupId": 2, "type": "total", "period": 1, "units": "Rounds", "prices": [{"designation": "over", "points": 21.5, "price": 105}]},
    {"matchupId": 3, "type": "moneyline", "period": 0, "prices": [{"designation": "home", "price": 100}]},
]


class TestColetor(unittest.TestCase):

    def test_so_cs2_com_filhos_mapa_a_mapa(self):
        jogos, linhas = jogos_e_linhas(MATCHUPS, MERCADOS)
        self.assertEqual([(j["casa"], j["fora"], j["bo"]) for j in jogos], [("FURIA", "MOUZ", 3)])
        self.assertEqual(len(linhas), 3)
        self.assertEqual({l["jogo"] for l in linhas}, {1})
        self.assertIn("Rounds", {l["unidade"] for l in linhas})

    def test_odd_americana_para_decimal(self):
        self.assertEqual(_decimal(-150), 1.6667)
        self.assertEqual(_decimal(120), 2.2)


if __name__ == "__main__":
    unittest.main()
