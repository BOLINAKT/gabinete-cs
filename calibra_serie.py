# -*- coding: utf-8 -*-
"""Calibracao da SERIE do Elo por jogador (26/10/2026).

No teste, a serie BO3 sai otimista com o favorito (previsto 0,847 -> real 0,776
na faixa 80-90%): mapas NAO sao independentes. Correcao simetrica (sem
intercepto -- a ordem time1/time2 nao entra): p_mapa' = sigmoide(c * logit(p_mapa))
antes de p_serie; c_serie escolhido na VALIDACAO (serie S/A) e, a parte, c_mapa
para o mercado de mapa. TESTE 2024+ uma vez.
"""
from __future__ import annotations

import math
import sys

import pandas as pd

import base_elo as be
import elo_jogador as ej
import troca_elenco as te
import variantes as va

VAL = (pd.Timestamp("2021-01-01"), be.INICIO_TESTE)


def ajusta(p, c):
    p = min(max(p, 1e-6), 1 - 1e-6)
    return 1 / (1 + math.exp(-c * math.log(p / (1 - p))))


def main() -> int:
    d = be.carregar()
    el = te.carregar_elencos()
    m, s = ej.rodar(d, el, ej.W_OFICIAL, ej.KJ_OFICIAL)
    grade = [x / 100 for x in range(50, 121, 5)]
    com = lambda c: [dict(x, p1=ajusta(x["p1"], c)) for x in s]
    cs = min(grade, key=lambda c: va.media(list(va.por_serie(com(c), *VAL, ("S", "A")).values())))
    for tiers in (("S",), ("S", "A")):
        B, V = va.por_serie(s, be.INICIO_TESTE, tiers=tiers), va.por_serie(com(cs), be.INICIO_TESTE, tiers=tiers)
        g, lo, hi, p, n = va.pareado(B, V)
        ok = g > 0.002 and p < 0.05 and lo > 0
        print(f"SERIE {'/'.join(tiers)} c={cs}: {va.media(list(B.values())):.4f} -> {va.media(list(V.values())):.4f} "
              f"ganho {g:+.4f} IC95 [{lo:+.4f}, {hi:+.4f}] p={p:.3f} {'PASSA' if ok else 'nao passa'}")
    val = [(p, y) for dt, t, p, y in m.values() if VAL[0] <= dt < VAL[1] and t in ("S", "A")]
    cm = min(grade, key=lambda c: va.media([be.ll(ajusta(p, c), y) for p, y in val]))
    B = te.perdas(m, be.INICIO_TESTE)
    V = {i: be.ll(ajusta(p, cm), y) for i, (dt, t, p, y) in m.items() if dt >= be.INICIO_TESTE and t in ("S", "A")}
    g, lo, hi, p, n = va.pareado(B, V)
    ok = g > 0.002 and p < 0.05 and lo > 0
    print(f"MAPA S/A c={cm}: {va.media(list(B.values())):.4f} -> {va.media(list(V.values())):.4f} "
          f"ganho {g:+.4f} IC95 [{lo:+.4f}, {hi:+.4f}] p={p:.3f} {'PASSA' if ok else 'nao passa'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
