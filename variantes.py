# -*- coding: utf-8 -*-
"""Ideias sobre o Elo de base, UMA DE CADA VEZ, no mesmo teste honesto (26/10/2026).

Mesmo protocolo de base_elo.py: prequencial; hiperparametros escolhidos so na
VALIDACAO (2021-2023); o TESTE (2024+) e lido uma vez por variante, no fim.
Cada variante liga UMA ideia sobre a base; a comparacao e no logloss da SERIE
S-Tier (e S/A) no teste, e o ganho e pareado por serie (bootstrap) -- a mesma
exigencia da casa: ganho > 0,002, p < 0,05, intervalo de confianca acima de 0.

  base       Elo global por time (K da validacao)
  mapa       + ajuste do time POR MAPA (rating do mapa = global + desvio, K_mapa)
  cs2        + no inicio do CS2 (27/09/2023) os ratings encolhem para a media
  tier       + K maior nos jogos S-Tier (o que mais informa) que no B-Tier
"""
from __future__ import annotations

import math
import random
import sys
from collections import defaultdict

import pandas as pd

import base_elo as be

INICIO_CS2 = pd.Timestamp("2023-09-27")


def rodar(d, k=40, k_mapa=0.0, encolhe_cs2=0.0, k_tier=None):
    r = defaultdict(lambda: 1500.0)
    rm = defaultdict(float)                 # (time, mapa) -> desvio
    series, encolheu = {}, False
    for x in d.itertuples(index=False):
        if encolhe_cs2 and not encolheu and x.dt >= INICIO_CS2:
            for t in list(r):
                r[t] = 1500 + (r[t] - 1500) * (1 - encolhe_cs2)
            rm.clear()
            encolheu = True
        a, b, m = x.time1, x.time2, x.mapa
        dif = (r[a] + rm[(a, m)]) - (r[b] + rm[(b, m)])
        p = 1 / (1 + 10 ** (-dif / 400))
        y = 1 if x.vencedor == 1 else 0
        chave = (x.pagina, x.data, a, b)
        s = series.setdefault(chave, {"dt": x.dt, "tier": x.tier, "p1": p, "v1": 0, "v2": 0, "id": chave})
        s["v1" if y else "v2"] += 1
        kk = k if not k_tier else k_tier.get(x.tier, k)
        r[a] += kk * (y - p)
        r[b] -= kk * (y - p)
        if k_mapa:
            rm[(a, m)] += k_mapa * (y - p)
            rm[(b, m)] -= k_mapa * (y - p)
    return list(series.values())


def por_serie(series, desde, ate=None, tiers=("S",)):
    fora = {}
    for x in series:
        if x["dt"] < desde or (ate is not None and x["dt"] >= ate) or x["tier"] not in tiers:
            continue
        precisa = max(x["v1"], x["v2"])
        if precisa < 1 or x["v1"] == x["v2"]:
            continue
        fora[x["id"]] = be.ll(be.p_serie(x["p1"], precisa), 1 if x["v1"] > x["v2"] else 0)
    return fora


def media(v):
    return sum(v) / len(v) if v else float("nan")


def escolher(d, grade, montar):
    """Melhor configuracao da grade pela VALIDACAO (S/A, 2021-2023)."""
    melhor = None
    for g in grade:
        s = rodar(d, **montar(g))
        v = media(list(por_serie(s, pd.Timestamp("2021-01-01"), be.INICIO_TESTE, ("S", "A")).values()))
        if melhor is None or v < melhor[1]:
            melhor = (g, v)
    return melhor[0]


def pareado(base, var, n=2000, semente=7):
    ids = [i for i in base if i in var]
    dif = [base[i] - var[i] for i in ids]          # > 0 = variante melhor
    rnd = random.Random(semente)
    boots = []
    for _ in range(n):
        amostra = [dif[rnd.randrange(len(dif))] for _ in dif]
        boots.append(media(amostra))
    boots.sort()
    ganho = media(dif)
    p = sum(1 for b in boots if b <= 0) / n
    return ganho, boots[int(0.025 * n)], boots[int(0.975 * n)], p, len(ids)


def main() -> int:
    d = be.carregar()
    k = escolher(d, be.KS, lambda g: {"k": g})
    base = rodar(d, k=k)
    variantes = {
        "mapa": (lambda: escolher(d, (5, 10, 20, 30), lambda g: {"k": k, "k_mapa": g}),
                 lambda g: {"k": k, "k_mapa": g}),
        "cs2": (lambda: escolher(d, (0.25, 0.5, 0.75), lambda g: {"k": k, "encolhe_cs2": g}),
                lambda g: {"k": k, "encolhe_cs2": g}),
        "tier": (lambda: escolher(d, ((48, 40, 32), (56, 40, 24), (48, 32, 24)),
                                  lambda g: {"k": k, "k_tier": dict(zip("SAB", g))}),
                 lambda g: {"k": k, "k_tier": dict(zip("SAB", g))}),
    }
    for tiers, nome_t in ((("S",), "S-Tier"), (("S", "A"), "S e A")):
        b = por_serie(base, be.INICIO_TESTE, tiers=tiers)
        print(f"\n== {nome_t}, teste 2024+ · base (K={k}): logloss serie {media(list(b.values())):.4f}  (n={len(b)})")
        for nome, (esc, montar) in variantes.items():
            g = esc()
            v = por_serie(rodar(d, **montar(g)), be.INICIO_TESTE, tiers=tiers)
            ganho, lo, hi, p, n = pareado(b, v)
            passa = ganho > 0.002 and p < 0.05 and lo > 0
            print(f"  {nome:5s} {str(g):16s} logloss {media(list(v.values())):.4f}  ganho {ganho:+.4f} "
                  f"IC95 [{lo:+.4f}, {hi:+.4f}] p={p:.3f}  {'PASSA' if passa else 'nao passa'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
