# -*- coding: utf-8 -*-
"""Melhores apostas nas casas dele (Fases 4 e 6, 15/11/2026)."""
import unittest

import apostas_cs as ap


def _jogo(p_pin=0.60, p_mod=0.70, **k):
    lados = [{"lado": "A", "p_modelo": p_mod, "p_pinnacle": p_pin},
             {"lado": "B", "p_modelo": 1 - p_mod, "p_pinnacle": None if p_pin is None else 1 - p_pin}]
    j = {"precificado": True, "casa": "A", "fora": "B", "liga": "X", "inicio_utc": "2026-11-16T12:00:00Z",
         "mercados": [{"mercado": "Série", "periodo": 0, "lados": lados}], "situacao": "a jogar", "ja_comecou": False}
    j.update(k)
    return j


class TestApostas(unittest.TestCase):
    def test_justa_e_a_pinnacle_e_a_odd_e_a_de_compra(self):
        # Polymarket: A a 0,53 no meio, spread 0,04 -> compra a 0,55 -> odd 1,818; justa Pinnacle 60%
        j = _jogo(poly={"p_a": 0.53, "p_b": 0.47, "spread": 0.04, "invertido": False})
        c = ap.candidatos(j)
        a = next(x for x in c if x["aposta"] == "A")
        self.assertAlmostEqual(a["odd"], 1 / 0.55, places=6)
        self.assertEqual(a["fonte"], "Pinnacle")
        self.assertAlmostEqual(a["valor"], (0.60 / 0.55 - 1) * 100, places=6)
        self.assertAlmostEqual(a["valor_modelo"], (0.70 / 0.55 - 1) * 100, places=6)
        self.assertTrue(a["destaque"])                             # justa 1,67 < 1,72
        m = ap.melhores_nas_casas(c)
        self.assertEqual([x["aposta"] for x in m], ["A"])          # B nao tem valor

    def test_invertido_sem_pinnacle_livro_vazio_e_teto(self):
        j = _jogo(p_pin=None, p_mod=0.55, poly={"p_a": 0.40, "p_b": 0.60, "spread": 0.02, "invertido": True})
        a = next(x for x in ap.candidatos(j) if x["aposta"] == "A")   # A e o time_b da Polymarket: 0,61
        self.assertAlmostEqual(a["odd"], 1 / 0.61, places=6)
        self.assertEqual(a["fonte"], "modelo")
        self.assertEqual(ap.candidatos(_jogo(poly={"p_a": 0.5, "p_b": 0.5, "spread": 0.5, "invertido": False})), [])
        absurdo = ap.candidatos(_jogo(p_pin=0.9, poly={"p_a": 0.5, "p_b": 0.5, "spread": 0.02, "invertido": False}))
        self.assertEqual(ap.melhores_nas_casas(absurdo), [])        # +76%: dado errado
        self.assertEqual(ap.candidatos({"precificado": False}), [])

    def test_ordem_regua_destaque_valor_e_stake(self):
        com = _jogo(poly={"p_a": 0.53, "p_b": 0.47, "spread": 0.04, "invertido": False})
        sem = _jogo(p_pin=None, p_mod=0.75, poly={"p_a": 0.66, "p_b": 0.34, "spread": 0.02, "invertido": False})
        stake = [{"casa": "Stake", "periodo": 0, "odd_casa": 1.75, "odd_fora": 2.1},
                 {"casa": "Stake", "periodo": 1, "odd_casa": 9.0, "odd_fora": 9.0},
                 {"casa": "Betano", "periodo": 0, "odd_casa": 9.0, "odd_fora": 9.0}]
        c = ap.candidatos(com, stake=stake) + ap.candidatos(sem)
        m = ap.melhores_nas_casas(c)
        self.assertEqual([(x["casa"], x["fonte"]) for x in m],
                         [("Polymarket", "Pinnacle"), ("Stake", "Pinnacle"), ("Polymarket", "modelo")])
        ja = _jogo(poly={"p_a": 0.53, "p_b": 0.47, "spread": 0.04, "invertido": False}, ja_comecou=True)
        self.assertEqual(ap.melhores_nas_casas(ap.candidatos(ja)), [])


if __name__ == "__main__":
    unittest.main()
