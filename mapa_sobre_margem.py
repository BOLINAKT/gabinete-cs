# -*- coding: utf-8 -*-
"""Saber O MAPA ajuda, agora SOBRE o modelo de margem (K=72, a=0.3)? (26/10/2026)

A rodada de mapa_conhecido.py mediu sobre o Elo de vitoria/derrota (+0,0006,
abaixo da regua). Aqui a base e o modelo aceito (margem em rounds). Candidatos,
os mesmos dois jeitos, com o desvio por mapa tambem aprendendo com a margem:
  elo_mapa  global + desvio do time naquele mapa (K_mapa)
  winrate   global + taxa no mapa encolhida para 50% (m), com peso
Escolha na VALIDACAO 2021-2023 (mapa, S/A); TESTE 2024+ lido uma vez.
"""
from __future__ import annotations

import math
import sys
from collections import defaultdict

import pandas as pd

import base_elo as be
import variantes as va

K, A = 72, 0.3
VAL = (pd.Timestamp("2021-01-01"), be.INICIO_TESTE)


def rodar(d, k_mapa=0.0, m_wr=None, peso=0.0):
    r, rm = defaultdict(lambda: 1500.0), defaultdict(float)
    vit, jog = defaultdict(float), defaultdict(int)
    fora = {}
    for x in d.itertuples(index=False):
        a, b, m = x.time1, x.time2, x.mapa
        dif = r[a] - r[b] + rm[(a, m)] - rm[(b, m)]
        if m_wr is not None:
            def lg(t):
                w = (vit[(t, m)] + 0.5 * m_wr) / (jog[(t, m)] + m_wr)
                return math.log(w / (1 - w))
            dif += peso * 400 / math.log(10) * (lg(a) - lg(b))
        p = 1 / (1 + 10 ** (-dif / 400))
        y = 1 if x.vencedor == 1 else 0
        tot = x.rounds1 + x.rounds2
        s = A * y + (1 - A) * (x.rounds1 / tot if tot > 0 else y)
        fora[(x.pagina, x.data, a, b, x.mapa_n)] = (x.dt, x.tier, p, y)
        r[a] += K * (s - p)
        r[b] -= K * (s - p)
        if k_mapa:
            rm[(a, m)] += k_mapa * (s - p)
            rm[(b, m)] -= k_mapa * (s - p)
        jog[(a, m)] += 1; jog[(b, m)] += 1
        vit[(a, m)] += y; vit[(b, m)] += 1 - y
    return fora


def perdas(f, desde, ate=None):
    return {i: be.ll(p, y) for i, (dt, t, p, y) in f.items()
            if dt >= desde and (ate is None or dt < ate) and t in ("S", "A")}


def main() -> int:
    d = be.carregar()
    base = rodar(d)
    bt = perdas(base, be.INICIO_TESTE)
    print(f"base margem: mapa S/A teste {va.media(list(bt.values())):.4f}")
    cand = {"elo_mapa": [{"k_mapa": g} for g in (5, 10, 20, 30)],
            "winrate": [{"m_wr": m, "peso": w} for m in (5, 10, 20) for w in (0.2, 0.4, 0.7)]}
    for nome, grade in cand.items():
        melhor = min(grade, key=lambda g: va.media(list(perdas(rodar(d, **g), *VAL).values())))
        v = perdas(rodar(d, **melhor), be.INICIO_TESTE)
        g, lo, hi, p, n = va.pareado(bt, v)
        ok = g > 0.002 and p < 0.05 and lo > 0
        print(f"{nome:9s} {str(melhor):30s} {va.media(list(v.values())):.4f} ganho {g:+.4f} "
              f"IC95 [{lo:+.4f}, {hi:+.4f}] p={p:.3f} n={n} {'PASSA' if ok else 'nao passa'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
