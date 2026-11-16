# -*- coding: utf-8 -*-
"""Competicao que a Liquipedia nao publica: a tela diz por que os jogos nao estao na base (16/11/2026)."""
import unittest

import precos_core as pc


class TestFonteSemMapas(unittest.TestCase):
    def test_esea_temporada_regular(self):
        self.assertIn("FACEIT", pc.motivo_fonte_sem_mapas("ESEA Advanced Europe Regular Season"))

    def test_outras_competicoes_nao_avisam(self):
        self.assertEqual(pc.motivo_fonte_sem_mapas("PGL Major Singapore Stage 1"), "")
        self.assertEqual(pc.motivo_fonte_sem_mapas("ESEA Season 59 Finals"), "")
        self.assertEqual(pc.motivo_fonte_sem_mapas(None), "")

    def test_imperial_e_o_time_principal(self):
        self.assertEqual(pc.APELIDOS["imperial"], "Imperial Esports")


if __name__ == "__main__":
    unittest.main()
