# -*- coding: utf-8 -*-
"""Atualizador diario: tier pela pagina, torneio ativo, troca das linhas relidas."""
import unittest
from datetime import date

import pandas as pd

import atualizar_dados as ad

IDX = {"PGL/2027/Bucharest": {"tier": "S"}, "PGL/2027/Bucharest/Qualifier": {"tier": "B"}}


class TestAtualizar(unittest.TestCase):
    def test_tier_do_torneio_mais_especifico(self):
        self.assertEqual(ad.tier_da_pagina("PGL/2027/Bucharest/Qualifier/Open/1", IDX), "B")
        self.assertEqual(ad.tier_da_pagina("PGL/2027/Bucharest/Playoffs", IDX), "S")
        self.assertEqual(ad.tier_da_pagina("Outro/2026", IDX, "A"), "A")

    def test_ativo(self):
        hoje = date(2026, 10, 26)
        self.assertTrue(ad.ativo({"inicio": "2026-10-24", "fim": "2026-10-31"}, hoje))
        self.assertTrue(ad.ativo({"inicio": "2026-10-13", "fim": "2026-10-20"}, hoje))   # fim ha 6 dias
        self.assertFalse(ad.ativo({"inicio": "2026-08-06", "fim": "2026-08-16"}, hoje))
        self.assertFalse(ad.ativo({"inicio": "2026-11-11", "fim": "2026-11-15"}, hoje))
        self.assertFalse(ad.ativo({"inicio": None, "fim": None}, hoje))

    def test_substitui_so_as_paginas_relidas(self):
        cols = ["pagina", "tier", "data", "time1", "time2", "mapa_n", "mapa", "rounds1", "rounds2",
                "lado_inicial1", "vencedor", "prorrogacoes", "hltv"]
        velho = pd.DataFrame([["A", "S", "d1", "x", "y", "1", "Nuke", "13", "5", "t", "1", "0", ""],
                              ["B", "S", "d2", "x", "z", "1", "Nuke", "13", "5", "t", "1", "0", ""]], columns=cols)
        novo = [dict(zip(cols, ["A", "S", "d1", "x", "y", "1", "Nuke", "13", "7", "t", "1", "0", ""]))]
        out = ad.substituir_paginas(velho, novo, {"A"})
        self.assertEqual(len(out), 2)
        self.assertEqual(out[out.pagina == "A"].rounds2.tolist(), ["7"])   # placar corrigido


if __name__ == "__main__":
    unittest.main()


class TestAgenda(unittest.TestCase):
    def test_proximos_so_os_nao_decididos_e_hora_em_utc(self):
        import extrator as ex
        txt = ("{{Match|opponent1={{TeamOpponent|mongolz}}|opponent2={{TeamOpponent|nemiga}}"
               "|date=October 28, 2026 - 13:00 {{Abbr/EET}}|map1={{Map|map=|finished=}}|map2={{Map|map=}}|map3={{Map|map=}}}}"
               "{{Match|opponent1={{TeamOpponent|tl}}|opponent2={{TeamOpponent|legacy}}|finished=true"
               "|date=October 26, 2026 - 13:00 {{Abbr/EET}}}}"
               "{{Match|opponent1={{TeamOpponent|}}|opponent2={{TeamOpponent|navi}}|date=October 29, 2026 - 13:00}}")
        p = ex.proximos_da_pagina(txt, pagina="PGL/2026/Masters", tier="S")
        self.assertEqual([(j["time1"], j["time2"], j["inicio_utc"], j["bo"]) for j in p],
                         [("mongolz", "nemiga", "2026-10-28T11:00:00Z", 3)])

    def test_cst_pelo_contexto_da_pagina(self):
        import extrator as ex
        self.assertEqual(ex.data_utc("July 5, 2026 - 20:00 {{Abbr/CST}}", "IEM/2026/China"), "2026-07-05T12:00:00Z")
        self.assertEqual(ex.data_utc("July 5, 2026 - 20:00 {{Abbr/CST}}", "IEM/2026/Dallas"), "2026-07-06T02:00:00Z")
