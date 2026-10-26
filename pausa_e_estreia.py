# -*- coding: utf-8 -*-
"""Duas ideias baratas sobre o modelo de margem (26/10/2026), uma de cada vez:

  pausa    time que volta depois de muitos dias parado encolhe para a media
           (r = 1500 + (r-1500)*(1-f), com f crescendo com a pausa, ate fmax);
           pausa longa costuma ser troca de elenco/temporada nova.
  estreia  time novo nao comeca em 1500 em todo tier: comeca no valor do tier
           onde aparece pela primeira vez (S, A, B), escolhido na validacao.
Validacao 2021-2023, TESTE 2024+ uma vez, mapa S/A, regua da casa.
"""
from __future__ import annotations

import sys
from collections import defaultdict

import pandas as pd

import base_elo as be
import variantes as va

K, A = 72, 0.3
VAL = (pd.Timestamp("2021-01-01"), be.INICIO_TESTE)


def rodar(d, meia_vida=None, fmax=0.0, estreia=None):
    r, ult = {}, {}
    fora = {}
    for x in d.itertuples(index=False):
        a, b = x.time1, x.time2
        for t in (a, b):
            if t not in r:
                r[t] = 1500.0 + (estreia or {}).get(x.tier, 0.0)
            elif meia_vida and t in ult:
                dias = (x.dt - ult[t]).days
                f = fmax * (1 - 0.5 ** (dias / meia_vida))
                r[t] = 1500 + (r[t] - 1500) * (1 - f)
            ult[t] = x.dt
        p = 1 / (1 + 10 ** (-(r[a] - r[b]) / 400))
        y = 1 if x.vencedor == 1 else 0
        tot = x.rounds1 + x.rounds2
        s = A * y + (1 - A) * (x.rounds1 / tot if tot > 0 else y)
        fora[(x.pagina, x.data, a, b, x.mapa_n)] = (x.dt, x.tier, p, y)
        r[a] += K * (s - p)
        r[b] -= K * (s - p)
    return fora


def perdas(f, desde, ate=None):
    return {i: be.ll(p, y) for i, (dt, t, p, y) in f.items()
            if dt >= desde and (ate is None or dt < ate) and t in ("S", "A")}


def main() -> int:
    d = be.carregar()
    bt = perdas(rodar(d), be.INICIO_TESTE)
    print(f"base margem {va.media(list(bt.values())):.4f}")
    cand = {"pausa": [{"meia_vida": h, "fmax": f} for h in (30, 60, 120) for f in (0.2, 0.4, 0.6)],
            "estreia": [{"estreia": {"S": s, "A": a, "B": 0.0}} for s in (0, 100, 200) for a in (-50, 0, 50, 100)]}
    for nome, grade in cand.items():
        melhor = min(grade, key=lambda g: va.media(list(perdas(rodar(d, **g), *VAL).values())))
        v = perdas(rodar(d, **melhor), be.INICIO_TESTE)
        g, lo, hi, p, n = va.pareado(bt, v)
        ok = g > 0.002 and p < 0.05 and lo > 0
        print(f"{nome:8s} {str(melhor):45s} {va.media(list(v.values())):.4f} ganho {g:+.4f} "
              f"IC95 [{lo:+.4f}, {hi:+.4f}] p={p:.3f} {'PASSA' if ok else 'nao passa'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
