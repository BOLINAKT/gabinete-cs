# -*- coding: utf-8 -*-
"""Tela de ML do CS (25/11/2026): ciclo do clique no mapa, nome curto, serie com mapas na mesma base do topo,
logo do infobox, HTML do confronto."""
import unittest
from collections import defaultdict
from types import SimpleNamespace

import imagens_cs as ic
import tela_ml_cs as tm
import veto_cs as vc


class TestCiclo(unittest.TestCase):
    def test_um_clique_por_estado(self):
        v, vistos = None, []
        for _ in range(5):
            v = tm.proximo_estado(v)
            vistos.append(v)
        self.assertEqual(vistos, ["A", "B", "ban", "decisivo", None])

    def test_estado_estranho_vira_pick_a(self):
        self.assertEqual(tm.proximo_estado("—"), "A")

    def test_nome_curto(self):
        self.assertEqual(tm.curto("Team Vitality"), "Vitality")
        self.assertEqual(tm.curto("Natus Vincere"), "Natus")
        self.assertEqual(tm.curto("FURIA"), "FURIA")


def _est(mapas_a=None, mapas_b=None):
    pm = defaultdict(list)
    for (t, m), h in (mapas_a or {}).items():
        pm[(t, m)] = h
    for (t, m), h in (mapas_b or {}).items():
        pm[(t, m)] = h
    return SimpleNamespace(por_mapa=pm, pool=["Mirage", "Nuke"])


class TestSerieComMapas(unittest.TestCase):
    def test_sem_mapas_da_o_md_do_topo(self):
        j = {"casou": [("A", "exato"), ("B", "exato")], "p_mapa": 0.62, "p_mapa_serie": 0.58}
        self.assertAlmostEqual(vc.serie_com_mapas(_est(), j, [], 3), vc.p_serie([0.58], 3))

    def test_mapa_bom_para_a_sobe_a_serie(self):
        est = _est({("A", "Mirage"): [(None, 1, 5)] * 30}, {("B", "Mirage"): [(None, 0, -5)] * 30})
        j = {"casou": [("A", "exato"), ("B", "exato")], "p_mapa": 0.55, "p_mapa_serie": 0.55}
        self.assertGreater(vc.serie_com_mapas(est, j, ["Mirage"], 3), vc.serie_com_mapas(est, j, [], 3))


class TestLogo(unittest.TestCase):
    def test_tema_escuro_primeiro(self):
        txt = "{{Infobox team\n|image=X lightmode.png\n|imagedark=X darkmode.png\n}}"
        self.assertEqual(ic.campo_logo(txt), "X darkmode.png")

    def test_so_image(self):
        self.assertEqual(ic.campo_logo("|image=Y.png\n|name=Y"), "Y.png")

    def test_sem_logo(self):
        self.assertEqual(ic.campo_logo("|name=Z"), "")


class TestHtml(unittest.TestCase):
    def _j(self, bo, p):
        f = {"forca": 2000, "mapas_ano": 50, "ultimo": "20/11/26"}
        return {"casa": "Alpha", "fora": "Beta", "casou": [("Alpha", "exato"), ("Beta", "exato")],
                "fichas": [f, f], "precificado": True, "p_mapa": 0.6, "pouco_dado": [],
                "mercados": [{"lados": [{"p_modelo": p}, {"p_modelo": 1 - p}]}]}

    def test_confronto_tem_as_tres_odds(self):
        h = tm.html_confronto(self._j(3, 0.65), self._j(5, 0.7))
        for txt in ("Mapa (sem saber qual)", "Série MD3", "Série MD5", "1.67", "1.54", "1.43", "rating"):
            self.assertIn(txt, h)

    def test_sem_preco_mostra_aviso(self):
        j = self._j(3, 0.5)
        j.update(precificado=False, avisos=["Beta: nao achei o time nos dados"])
        self.assertIn("nao achei", tm.html_confronto(j, j))


class TestIdentidade(unittest.TestCase):
    def test_casamento_aproximado_avisa(self):
        j = {"casa": "PVISION", "fora": "FaZe", "casou": [("PARIVISION", "parecido"), ("FaZe Clan", "exato")],
             "fichas": [None, None]}
        av = tm.avisos_identidade(j, so_casamento=True)
        self.assertEqual(len(av), 1)
        self.assertIn("PARIVISION", av[0][1])

    def test_jogador_novo(self):
        f = {"jogadores": [{"jogador": "x", "novo": True, "entrou": "2026-11-10"}, {"jogador": "y", "novo": False}],
             "elenco_conhecido": True, "dias_parado": 2, "ultimo": "25/11/26"}
        av = tm.avisos_identidade({"casa": "A", "fora": "B", "casou": [("A", "exato"), ("B", "exato")],
                                   "fichas": [f, None]})
        self.assertTrue(any("x (desde 10/11)" in t for _n, t in av))


if __name__ == "__main__":
    unittest.main()
