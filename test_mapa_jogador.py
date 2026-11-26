# -*- coding: utf-8 -*-
"""Nota de mapa por jogador (26/11/2026)."""
import unittest
from types import SimpleNamespace

import pandas as pd

import mapa_jogador as mj


class TestMapaJogador(unittest.TestCase):
    def _dados(self):
        linhas, prev = [], {}
        for i in range(40):                         # A sempre ganha a Mirage de B, apesar de 50% no motor
            dt = pd.Timestamp("2026-01-01") + pd.Timedelta(days=i)
            linhas.append(SimpleNamespace(pagina="p", data=str(dt.date()), time1="A", time2="B", mapa_n=1,
                                          mapa="Mirage", dt=dt))
            prev[("p", str(dt.date()), "A", "B", 1)] = (dt, "S", 0.5, 1)
        d = pd.DataFrame([vars(x) for x in linhas])
        el = {"A": ([pd.Timestamp("2025-01-01")], [frozenset("abcde")]),
              "B": ([pd.Timestamp("2025-01-01")], [frozenset("vwxyz")])}
        return d, el, prev

    def test_aprende_e_jogador_leva_a_nota(self):
        d, el, prev = self._dados()
        dj, dtm = mj.aprender(d, el, prev)
        hoje = pd.Timestamp("2026-03-01")
        self.assertGreater(mj.p_mapa(0.5, dj, dtm, el, "A", "B", "Mirage", hoje), 0.6)
        self.assertAlmostEqual(mj.p_mapa(0.5, dj, dtm, el, "A", "B", "Nuke", hoje), 0.5)
        # o jogador 'a' leva a nota de Mirage para um time novo com elenco a + 4 desconhecidos
        el2 = dict(el, C=([pd.Timestamp("2026-02-01")], [frozenset("a1234")]))
        self.assertGreater(mj.desvio(dj, dtm, el2, "C", "Mirage", hoje), 0)

    def test_previsoes_prequenciais(self):
        d, el, prev = self._dados()
        pv = {}
        mj.aprender(d, el, prev, previsoes=pv)
        qs = [pv[k][2] for k in sorted(pv)]
        self.assertAlmostEqual(qs[0], 0.5)          # o 1o mapa nao sabe nada ainda
        self.assertGreater(qs[-1], qs[0])


if __name__ == "__main__":
    unittest.main()
