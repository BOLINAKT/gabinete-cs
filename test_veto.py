# -*- coding: utf-8 -*-
"""Mapas do veto lidos da Liquipedia e o placar base x sabendo o mapa."""
import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

import tela_cs as tl
import veto_cs as vc

PAG = ("{{Match|opponent1={{TeamOpponent|tl}}|opponent2={{TeamOpponent|legacy}}|date=October 26, 2026 - 14:15"
       "|map1={{Map|map=Mirage|finished=true|t1t=8|t1ct=5|t2t=4|t2ct=4}}"
       "|map2={{Map|map=Nuke|finished=}}|map3={{Map|map=|finished=}}}}")


class TestVeto(unittest.TestCase):
    def test_le_mapas_com_nome_e_vencedor_pelos_rounds(self):
        m = vc.mapas_na_pagina(PAG, {"tl", "liquid"}, {"legacy"})
        self.assertEqual([(x["n"], x["mapa"], x["terminado"], x["vencedor_a"]) for x in m],
                         [(1, "Mirage", True, 1), (2, "Nuke", False, None)])

    def test_vencedor_do_ponto_de_vista_do_time_a(self):
        m = vc.mapas_na_pagina(PAG, {"legacy"}, {"tl"})
        self.assertEqual(m[0]["vencedor_a"], 0)

    def test_sem_o_confronto_nao_inventa(self):
        self.assertEqual(vc.mapas_na_pagina(PAG, {"furia"}, {"legacy"}), [])

    def test_placar_junta_registro_e_resultado(self):
        with tempfile.TemporaryDirectory() as tmp:
            reg, res = Path(tmp) / "r.jsonl", Path(tmp) / "s.jsonl"
            reg.write_text(json.dumps({"jogo": 1, "inicio_utc": "2026-10-26T14:15:00Z", "time_a": "A",
                                       "time_b": "B", "n": 1, "mapa": "Mirage", "p_base": 0.6,
                                       "p_mapa": 0.65}) + "\n", encoding="utf-8")
            res.write_text(json.dumps({"jogo": 1, "n": 1, "mapa": "Mirage", "venceu_a": 1}) + "\n", encoding="utf-8")
            velho = (vc.REGISTRO, vc.RESULTADOS)
            vc.REGISTRO, vc.RESULTADOS = reg, res
            try:
                pl = vc.placar(pd.DataFrame(columns=["dt", "mapa_n", "mapa", "time1", "time2", "vencedor"]))
            finally:
                vc.REGISTRO, vc.RESULTADOS = velho
        self.assertEqual(pl["n"], 1)
        self.assertLess(pl["ll_mapa"], pl["ll_base"])
        self.assertIn("sabendo o mapa", tl.html_placar(pl))

    def test_tela_do_veto(self):
        j = {"casa": "Liquid", "fora": "Legacy"}
        l = [{"n": 1, "mapa": "Mirage", "terminado": True, "vencedor_a": 1, "p_base": 0.4, "p_mapa": 0.42,
              "odd_a": 2.7, "odd_b": 1.5, "vant_mapa_a": 13.4, "vant_mapa_b": -13.0}]
        h = tl.html_veto(j, l, "PGL/2026/Masters")
        self.assertIn("Mirage", h)
        self.assertIn("+13,4%", h)
        self.assertIn("<b>Liquid</b>", h)
        self.assertIn("ainda não estão", tl.html_veto(j, [], None))

    def test_jogo_sem_linha_da_pinnacle_usa_o_p_do_mapa(self):
        """16/11/2026: jogo so da Polymarket nao tem mercado de mapa da Pinnacle; a tabela do veto
        nao pode sair vazia (a tela diria que a Liquipedia nao tem os mapas)."""
        class Est:
            por_mapa = {}
        j = {"casou": [("A", 1.0), ("B", 1.0)], "mercados": [{"periodo": 0, "lados": []}], "p_mapa": 0.6}
        v = {"mapas": [{"n": 1, "mapa": "Mirage", "terminado": False, "vencedor_a": None}]}
        lin = vc.linhas_do_veto(Est(), j, v)
        self.assertEqual(len(lin), 1)
        self.assertAlmostEqual(lin[0]["p_base"], 0.6)
        self.assertIsNone(lin[0]["odd_a"])


class TestMapasClicados(unittest.TestCase):
    """24/11/2026: ele marca os mapas clicando (pick de cada time, ban, decisivo)."""

    def test_ordem_picks_na_ordem_do_clique_decisivo_no_fim(self):
        marcas = {"Mirage": "B", "Inferno": "A", "Nuke": "ban", "Ancient": "decisivo", "Dust2": None}
        ordem = {"Inferno": 1, "Mirage": 2}
        self.assertEqual(vc.ordem_dos_mapas(marcas, ordem), [("Inferno", "A"), ("Mirage", "B"), ("Ancient", None)])

    def test_serie(self):
        self.assertAlmostEqual(vc.p_serie([0.5, 0.5, 0.5], 3), 0.5)
        self.assertAlmostEqual(vc.p_serie([0.8, 0.2, 0.5], 3), 0.8 * 0.2 + 0.8 * 0.8 * 0.5 + 0.2 * 0.2 * 0.5)
        self.assertAlmostEqual(vc.p_serie([0.6], 1), 0.6)
        self.assertGreater(vc.p_serie([0.6] * 5, 5), vc.p_serie([0.6] * 3, 3))   # serie longa favorece o melhor



if __name__ == "__main__":
    unittest.main()
