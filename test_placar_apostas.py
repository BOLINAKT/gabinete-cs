# -*- coding: utf-8 -*-
"""Placar das apostas indicadas (Fase 7, 15/11/2026)."""
import unittest

import apostas_cs as ap
import placar_apostas as pa

SERIE_2x1 = [{"n": 1, "rc": 13, "rf": 9}, {"n": 2, "rc": 8, "rf": 13}, {"n": 3, "rc": 16, "rf": 14}]
SERIE_0x2 = [{"n": 1, "rc": 5, "rf": 13}, {"n": 2, "rc": 11, "rf": 13}]


class TestGanhou(unittest.TestCase):
    def test_cada_mercado(self):
        g = pa.ganhou
        self.assertTrue(g(SERIE_2x1, {"tipo": "venc", "lado": "casa"}))
        self.assertFalse(g(SERIE_2x1, {"tipo": "venc", "lado": "fora"}))
        self.assertFalse(g(SERIE_2x1, {"tipo": "hc_mapas", "lado": "casa", "linha": -1.5}))   # 2-1 nao cobre -1,5
        self.assertTrue(g(SERIE_2x1, {"tipo": "hc_mapas", "lado": "fora", "linha": 1.5}))
        self.assertTrue(g(SERIE_0x2, {"tipo": "hc_mapas", "lado": "fora", "linha": -1.5}))
        self.assertTrue(g(SERIE_2x1, {"tipo": "tot_mapas", "lado": "over", "linha": 2.5}))
        self.assertTrue(g(SERIE_0x2, {"tipo": "tot_mapas", "lado": "under", "linha": 2.5}))
        self.assertTrue(g(SERIE_2x1, {"tipo": "hc_rounds", "lado": "casa", "linha": -3.5, "mapa": 1}))  # 13-9
        self.assertFalse(g(SERIE_2x1, {"tipo": "hc_rounds", "lado": "casa", "linha": -3.5, "mapa": 3}))  # 16-14
        self.assertTrue(g(SERIE_2x1, {"tipo": "hc_rounds", "lado": "fora", "linha": 3.5, "mapa": 3}))
        self.assertIsNone(g(SERIE_0x2, {"tipo": "hc_rounds", "lado": "casa", "linha": -3.5, "mapa": 3}))  # nao jogado
        self.assertIsNone(g(SERIE_2x1, {"tipo": "outro"}))
        self.assertIsNone(g([], {"tipo": "venc", "lado": "casa"}))

    def test_chave_dos_mercados_da_serie(self):
        m = {"mercado": "Mapas ±1,5", "lados": [{"rotulo": "BIG −1,5"}, {"rotulo": "Sangal +1,5"}]}
        self.assertEqual(ap._chave_serie(m, 0), {"tipo": "hc_mapas", "lado": "casa", "linha": -1.5})
        self.assertEqual(ap._chave_serie(m, 1), {"tipo": "hc_mapas", "lado": "fora", "linha": 1.5})
        t = {"mercado": "Total de mapas", "lados": [{"rotulo": "Mais de 2,5 mapas"}, {"rotulo": "Menos de 2,5 mapas"}]}
        self.assertEqual(ap._chave_serie(t, 1), {"tipo": "tot_mapas", "lado": "under", "linha": 2.5})

    def test_ultima_antes_do_jogo_e_resumo(self):
        base = {"jogo": 1, "mercado": "Série", "aposta": "A", "onde": "Polymarket", "inicio_utc": "2026-11-16T12:00:00Z"}
        regs = [dict(base, lido_em="2026-11-16T06:00:00+00:00", odd=1.9),
                dict(base, lido_em="2026-11-16T09:00:00+00:00", odd=1.8),
                dict(base, lido_em="2026-11-16T13:00:00+00:00", odd=1.1)]     # depois do inicio
        u = pa.ultimas(regs)
        self.assertEqual([r["odd"] for r in u], [1.8])
        r = pa.resumo([{"lucro": 0.8, "fonte": "Pinnacle", "destaque": True},
                       {"lucro": -1.0, "fonte": "modelo", "destaque": False}])
        self.assertEqual(r["todas"]["n"], 2)
        self.assertEqual(r["justa_pinnacle"]["roi"], 0.8)
        self.assertEqual(r["justa_modelo"]["acertos"], 0)
        self.assertEqual(pa.resumo([])["todas"], {"n": 0})


if __name__ == "__main__":
    unittest.main()
