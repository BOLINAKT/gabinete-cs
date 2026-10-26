# -*- coding: utf-8 -*-
"""Saber O MAPA ajuda, sobre o Elo POR JOGADOR (modelo oficial)? (26/10/2026)

Medido antes so sobre modelos com o bug dos nomes (+0,0005/+0,0007). Aqui:
logit(p') = logit(p_oficial) + peso * (logit(wr_a) - logit(wr_b)), com wr = taxa
do time NAQUELE mapa encolhida para 50% (m jogos-fantasma), so com o passado.
m e peso escolhidos na VALIDACAO 2021-2023; TESTE 2024+ uma vez; mapa S/A.
"""
from __future__ import annotations

import math
import sys
from collections import defaultdict

import pandas as pd

import base_elo as be
import elo_jogador as ej
import troca_elenco as te
import variantes as va

VAL = (pd.Timestamp("2021-01-01"), be.INICIO_TESTE)


def logit(p):
    p = min(max(p, 1e-6), 1 - 1e-6)
    return math.log(p / (1 - p))


def diferencas(d, m_wr):
    """{id do mapa: logit(wr_a) - logit(wr_b)} so com mapas ANTERIORES."""
    vit, jog, fora = defaultdict(float), defaultdict(int), {}
    for x in d.itertuples(index=False):
        a, b, mp = x.time1, x.time2, x.mapa
        wa = (vit[(a, mp)] + 0.5 * m_wr) / (jog[(a, mp)] + m_wr)
        wb = (vit[(b, mp)] + 0.5 * m_wr) / (jog[(b, mp)] + m_wr)
        fora[(x.pagina, x.data, a, b, x.mapa_n)] = logit(wa) - logit(wb)
        y = 1 if x.vencedor == 1 else 0
        jog[(a, mp)] += 1; jog[(b, mp)] += 1
        vit[(a, mp)] += y; vit[(b, mp)] += 1 - y
    return fora


def main() -> int:
    d = be.carregar()
    el = te.carregar_elencos()
    m, _ = ej.rodar(d, el, ej.W_OFICIAL, ej.KJ_OFICIAL)
    sel = lambda a, b=None: [i for i, (dt, t, p, y) in m.items() if dt >= a and (b is None or dt < b) and t in ("S", "A")]
    val, tes = sel(*VAL), sel(be.INICIO_TESTE)
    difs = {mw: diferencas(d, mw) for mw in (5, 10, 20, 40)}

    def perdas(mw, w, ids):
        return {i: be.ll(1 / (1 + math.exp(-(logit(m[i][2]) + w * difs[mw][i]))), m[i][3]) for i in ids}
    grade = [(mw, w) for mw in difs for w in (0.1, 0.2, 0.3, 0.5)]
    mw, w = min(grade, key=lambda g: va.media(list(perdas(*g, val).values())))
    B, V = perdas(5, 0.0, tes), perdas(mw, w, tes)
    g, lo, hi, p, n = va.pareado(B, V)
    ok = g > 0.002 and p < 0.05 and lo > 0
    print(f"m={mw} peso={w}: mapa S/A {va.media(list(B.values())):.4f} -> {va.media(list(V.values())):.4f} "
          f"ganho {g:+.4f} IC95 [{lo:+.4f}, {hi:+.4f}] p={p:.3f} n={n} {'PASSA' if ok else 'nao passa'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
