# -*- coding: utf-8 -*-
"""Placar modelo x Pinnacle: fechamento antes do inicio e resultado da serie/mapa."""
import unittest

import pandas as pd

import placar_pinnacle as pp
import registrar_previsoes as rp


def _reg(lido, p=0.6, per=0, merc="Série"):
    return {"lido_em": lido, "jogo": 1, "inicio_utc": "2026-10-27T18:45:00Z", "bo": 3, "liga": "x",
            "casa": "MIBR", "fora": "EF", "time_casa": "MIBR", "time_fora": "Eternal Fire",
            "mercado": merc, "periodo": per, "p_modelo_casa": p, "p_pinnacle_casa": 0.55,
            "odd_casa": 1.9, "odd_fora": 2.0}


D = pd.DataFrame({"pagina": ["P"] * 3, "time1": ["Eternal Fire"] * 3, "time2": ["MIBR"] * 3,
                  "mapa_n": [1, 2, 3], "vencedor": [2, 1, 2],
                  "dt": pd.to_datetime(["2026-10-27 18:50"] * 3)})


class TestPlacar(unittest.TestCase):
    def test_fechamento_e_a_ultima_leitura_antes_do_inicio(self):
        regs = [_reg("2026-10-27T12:00:00+00:00", 0.6), _reg("2026-10-27T18:00:00+00:00", 0.7),
                _reg("2026-10-27T19:00:00+00:00", 0.9)]   # depois do inicio: fora
        f = pp.fechamento(regs)
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0]["p_modelo_casa"], 0.7)

    def test_resultado_com_times_invertidos_na_liquipedia(self):
        self.assertEqual(pp.resultado(D, _reg("x")), 1)                     # MIBR 2x1
        self.assertEqual(pp.resultado(D, _reg("x", per=2, merc="Mapa 2")), 0)  # EF levou o mapa 2

    def test_placar_conta_aposta_com_vantagem(self):
        pl = pp.placar(D, [_reg("2026-10-27T18:00:00+00:00", 0.6)])   # 0,6*1,9 = +14%
        self.assertEqual((pl["n"], pl["apostas"]), (1, 1))
        self.assertAlmostEqual(pl["lucro"], 0.9)

    def test_registro_so_de_jogo_precificado_e_nao_comecado(self):
        jogos = [{"precificado": True, "ja_comecou": False, "id": 1, "inicio_utc": "t", "bo": 3, "liga": "l",
                  "casa": "A", "fora": "B", "casou": [("A", "exato"), ("B", "exato")],
                  "mercados": [{"mercado": "Série", "periodo": 0, "lados": [
                      {"p_modelo": 0.6, "p_pinnacle": 0.5, "odd_pinnacle": 1.9},
                      {"p_modelo": 0.4, "p_pinnacle": 0.5, "odd_pinnacle": 1.9}]}]},
                 {"precificado": False, "ja_comecou": False}, {"precificado": True, "ja_comecou": True}]
        self.assertEqual(len(rp.linhas_da_leitura(jogos, "agora")), 1)


if __name__ == "__main__":
    unittest.main()
