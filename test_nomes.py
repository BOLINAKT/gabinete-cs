# -*- coding: utf-8 -*-
"""Nomes canonicos dos times e odd justa da Pinnacle."""
import unittest

import base_elo as be
import precificar_cs as pc
import resolver_times as rt


class TestNomes(unittest.TestCase):
    def test_ler_lote_pega_a_pagina_do_time(self):
        txt = ('@@tl@@<span class="x" data-highlighting-class="Team Liquid"><span>..</span></span>\n'
               '@@semmodelo@@<span class="erro">nada</span>')
        assert rt.ler_lote(txt) == {"tl": "Team Liquid"}


    def test_canonico_nao_funde_o_que_nao_e_o_mesmo_time(self):
        m = {"tl": "Team Liquid", "france.3dmax": "Team France", "x (female team)": "X",
             "furia.fe": "FURIA", "orgless.au": "Orgless"}
        assert be.canonico("tl", m) == "Team Liquid"
        for cru in ("france.3dmax", "x (female team)", "furia.fe", "orgless.au", "desconhecido"):
            assert be.canonico(cru, m) == cru


    def test_justas_tira_a_margem_por_proporcao(self):
        linhas = [{"matchup": 1, "tipo": "moneyline", "alternativa": False, "periodo": 0, "lado": "home", "odd": 1.8},
                  {"matchup": 1, "tipo": "moneyline", "alternativa": False, "periodo": 0, "lado": "away", "odd": 2.0}]
        pc_, pf = pc.justas(linhas, 1)[0]
        assert abs(pc_ + pf - 1) < 1e-9 and pc_ > pf


if __name__ == "__main__":
    unittest.main()
