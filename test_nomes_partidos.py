# -*- coding: utf-8 -*-
"""Grafias alternativas do mesmo time e nomes sem letra latina (15/11/2026)."""
import json
import unittest
from pathlib import Path

import auditar_nomes as an
import precos_core as pc


class TestNomes(unittest.TestCase):
    def test_prova_para_unir(self):
        base = {"mapas_b": 807, "elenco_b": 39, "mapas_a": 10, "enfrentaram": 0, "mesmo_dia": 0,
                "janela_a": ["2022-08-31", "2023-02-15"], "janela_b": ["2020-01-12", "2026-11-15"]}
        self.assertTrue(an.prova_basta(base))
        self.assertFalse(an.prova_basta(dict(base, enfrentaram=1)))
        self.assertFalse(an.prova_basta(dict(base, mesmo_dia=2)))
        self.assertFalse(an.prova_basta(dict(base, mapas_a=128)))                   # "Players": outro time
        self.assertFalse(an.prova_basta(dict(base, elenco_b=0)))                    # principal sem elenco
        self.assertFalse(an.prova_basta(dict(base, janela_a=["2019-01-01", "2019-02-01"])))   # fora do periodo

    def test_nome_sem_letra_latina_nao_vira_chave_vazia(self):
        self.assertNotEqual(pc._n("篮球鸡"), pc._n("推土机"))
        self.assertNotEqual(pc._n("Эщкере"), "")
        self.assertEqual(pc._n("Team Liquid"), "teamliquid")
        self.assertEqual(pc._n("HEROIC"), pc._n("Heroic"))

    def test_lista_gravada(self):
        u = json.loads(Path(an.SAIDA).read_text(encoding="utf-8"))["unioes"]
        self.assertEqual(u.get("Heroic"), "HEROIC")
        self.assertFalse(set(u) & set(u.values()))                                  # ninguem e antigo e atual


if __name__ == "__main__":
    unittest.main()
