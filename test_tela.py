# -*- coding: utf-8 -*-
"""O desenho do app do CS: jogo precificado, nao precificado e lista de apostas."""
import unittest

import precos_core as pc
import tela_cs as tl


def _ficha(nome, novo=False):
    return {"time": nome, "forca": 1800, "elo_time": 1790, "mapas_ano": 90, "ultimo": "25/10/26",
            "dias_parado": 1, "elenco_conhecido": True,
            "jogadores": [{"jogador": "a", "nota": 1900, "entrou": "2026-10-13", "novo": novo, "visto": True}]}


def _jogo(precificado=True, novo=False):
    lados = [{"lado": "MIBR", "p_modelo": 0.6, "odd_modelo": 1 / 0.6, "p_pinnacle": 0.55, "odd_pinnacle": 1.9,
              "vantagem": 14.0},
             {"lado": "EF", "p_modelo": 0.4, "odd_modelo": 2.5, "p_pinnacle": 0.45, "odd_pinnacle": 2.0,
              "vantagem": -20.0}]
    return {"id": 1, "liga": "STK", "casa": "MIBR", "fora": "EF", "bo": 3, "inicio_utc": "2026-10-27T18:45:00Z",
            "ja_comecou": False, "casou": [], "fichas": [_ficha("MIBR", novo), _ficha("EF")],
            "precificado": precificado, "avisos": [] if precificado else ["EF: sem dado recente"],
            "mercados": [{"mercado": "Série", "periodo": 0, "lados": lados}] if precificado else []}


class TestTela(unittest.TestCase):
    def test_hora_em_brasilia(self):
        self.assertEqual(tl.hora_br("2026-10-27T18:45:00Z"), "27/10 15:45")

    def test_jogo_precificado_tem_as_duas_colunas_e_verde_no_valor(self):
        h = tl.html_jogo(_jogo())
        self.assertIn("Modelo — odd justa", h)
        self.assertIn("Pinnacle — odd paga", h)
        self.assertIn('class="verde"', h)
        self.assertIn("+14,0%", h)

    def test_nao_precificado_mostra_o_motivo_e_nao_da_numero(self):
        h = tl.html_jogo(_jogo(precificado=False))
        self.assertIn("Não precificado", h)
        self.assertNotIn("odd justa", h)

    def test_jogador_novo_gera_aviso(self):
        self.assertIn("entrou nos últimos 60 dias", tl.html_jogo(_jogo(novo=True)))

    def test_melhores_fica_entre_1_e_20_e_ordena(self):
        lst = pc.melhores([_jogo()])
        self.assertEqual([x["lado"] for x in lst], ["MIBR"])
        self.assertIn("MIBR", tl.html_melhores(lst))


if __name__ == "__main__":
    unittest.main()
