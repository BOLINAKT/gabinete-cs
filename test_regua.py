# -*- coding: utf-8 -*-
"""A regua do plano do CS (Fase 0, 12/11/2026)."""
import json
import tempfile
import unittest
from pathlib import Path

import regua_cs as rg


def _l(pm, pk, y, periodo=0, casa="A", fora="B", dia="2026-11-01"):
    return {"p_modelo_casa": pm, "p_pinnacle_casa": pk, "venceu_casa": y, "periodo": periodo,
            "casa": casa, "fora": fora, "inicio_utc": dia + "T12:00:00Z"}


class TestRegua(unittest.TestCase):
    def test_recorte_mede_modelo_contra_pinnacle(self):
        linhas = [_l(0.9, 0.6, 0)] * 20 + [_l(0.9, 0.6, 1)] * 20      # modelo confiante demais
        r = rg.recorte(linhas)
        self.assertEqual(r["n"], 40)
        self.assertLess(r["vantagem_modelo"], 0)
        self.assertLess(r["inclinacao_modelo"], 0.5)
        self.assertEqual(r["peso_modelo_na_mistura"], 0.0)
        self.assertEqual(rg.recorte([]), {"n": 0})

    def test_casas_dele_so_serie_antes_do_jogo_e_com_valor(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "h.jsonl"
            regs = [
                {"lido_em": "2026-11-01T08:00:00+00:00", "time1": "B", "time2": "A", "inicio_utc": "2026-11-01T12:00:00.000Z",
                 "casa": "stake", "mercado": "Série", "odds": [2.6, 1.5]},
                {"lido_em": "2026-11-01T13:00:00+00:00", "time1": "B", "time2": "A", "inicio_utc": "2026-11-01T12:00:00.000Z",
                 "casa": "stake", "mercado": "Série", "odds": [9.0, 1.01]},          # depois do inicio: fora
                {"lido_em": "2026-11-01T08:00:00+00:00", "time1": "B", "time2": "A", "inicio_utc": "2026-11-01T12:00:00.000Z",
                 "casa": "unibet", "mercado": "Série", "odds": [3.0, 1.4]},          # nao e casa dele
                {"lido_em": "2026-11-01T08:00:00+00:00", "time1": "B", "time2": "A", "inicio_utc": "2026-11-01T12:00:00.000Z",
                 "casa": "stake", "mercado": "Mapa 1", "odds": [3.0, 1.4]}]
            p.write_text("\n".join(json.dumps(r) for r in regs), encoding="utf-8")
            casas = rg.ultima_das_casas(p)
        self.assertEqual(len(casas), 1)
        # A (casa do placar) e o time2 da casa: odd 1,50. Pinnacle 70% -> valor +5%; modelo 62% -> sem valor nos dois lados
        r = rg.casas_dele([_l(0.62, 0.70, 1)], casas)
        self.assertEqual(r["series_com_odd_das_casas"], 1)
        self.assertEqual(r["valor_contra_pinnacle"], {"n": 1, "lucro": 0.5, "roi": 0.5})
        self.assertEqual(r["valor_contra_modelo"]["n"], 0)


if __name__ == "__main__":
    unittest.main()
