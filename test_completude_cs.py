# -*- coding: utf-8 -*-
"""Completude da base do CS2 contra a Liquipedia:Matches (24/11/2026)."""
import unittest
from datetime import datetime, timezone

import pandas as pd

import completude_cs as CC

MAPA = {"pvision": "PARIVISION", "gosh": "BC.Game Esports", "liquid": "Team Liquid"}
canon = lambda n: MAPA.get(str(n).lower(), n)  # noqa: E731
AGORA = datetime(2026, 11, 24, 21, 0, tzinfo=timezone.utc)


def _cartao(ts, a, b, fim=True):
    op = lambda n, pl: (f'<div class="match-ticker-card&#95;&#95;opponent"><div class="block-team"><a href="/x" '  # noqa: E731
                        f'title="{n}">X</a></div><div>{pl}</div></div>')
    return (f'<div class="match-ticker-card" data-match-timestamp="{ts}"><div class="match-ticker-card&#95;&#95;header">'
            f'<span class="timer-object" data-timestamp="{ts}"' + (' data-finished="finished"' if fim else '') + '>x</span>'
            f'</div><div class="match-ticker-card&#95;&#95;opponents">{op(a, 13)}{op(b, 1)}</div>'
            f'<div class="match-ticker-card-tournament"><span class="match-ticker-card-tournament-name">'
            f'<a href="/x" title="PGL/2026/Singapore">PGL Major Singapore 2026</a></span></div></div>')


class TestCompletudeCS(unittest.TestCase):

    def test_le_so_terminadas_com_atributo_no_cartao(self):
        s = CC.ler_terminadas(_cartao(1795496400, "Team Liquid", "GOSH") + _cartao(1795496400, "A", "B", fim=False))
        self.assertEqual([(x["time_a"], x["time_b"], x["placar"]) for x in s], [("Team Liquid", "GOSH", "13-1")])

    def test_nome_da_liquipedia_passa_pelo_tradutor_da_base(self):
        mapas = pd.DataFrame([{"data": "2026-11-24 06:30:00", "time1": "liquid", "time2": "gosh"}])
        s = [{"time_a": "Team Liquid", "time_b": "GOSH", "inicio_utc": "2026-11-24T06:10:00+00:00", "torneio": "PGL"},
             {"time_a": "PVISION", "time_b": "FlyQuest", "inicio_utc": "2026-11-24T08:00:00+00:00", "torneio": "PGL"},
             {"time_a": "X", "time_b": "Y", "inicio_utc": "2026-11-24T18:00:00+00:00", "torneio": "PGL"}]   # < 8 h
        f = CC.conferir(s, mapas, canon, AGORA)
        self.assertEqual([(x["a"], x["b"]) for x in f], [("PVISION", "FlyQuest")])


if __name__ == "__main__":
    unittest.main()
