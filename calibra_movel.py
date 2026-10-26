# -*- coding: utf-8 -*-
"""CALIBRACAO MOVEL (26/10/2026): o c de cada mes vem SO dos 12 meses anteriores.

Com os tiers corrigidos, a validacao fixa (2021-2023) escolhe c=1,0 (serie) e 1,1
(mapa), mas no teste 2024+ o modelo esta confiante demais (c=0,9 seria melhor).
Escolher c pelo teste seria espiar. Aqui o c acompanha o tempo sem espiar: em
cada mes do teste, c = o melhor nos 12 meses ANTERIORES (S/A/B). Contra "sem
calibracao" e contra o c fixo da validacao.
"""
from __future__ import annotations

import sys

import pandas as pd

import base_elo as be
import calibra_serie as cal
import elo_jogador as ej
import troca_elenco as te
import variantes as va

T = ("S", "A", "B")
GRADE = [x / 100 for x in range(70, 116, 5)]


def c_movel(pares, ini, meses=12):
    """pares: [(dt, p, y)]. Melhor c nos `meses` antes de ini."""
    j = [(p, y) for dt, p, y in pares if ini - pd.DateOffset(months=meses) <= dt < ini]
    return min(GRADE, key=lambda c: va.media([be.ll(cal.ajusta(p, c), y) for p, y in j])) if j else 1.0


def c_serie_atual(series: list, hoje, meses: int = 12) -> float:
    """O c da SERIE para usar HOJE: o melhor nas series S/A/B dos `meses` anteriores.
    Aceito 26/10/2026 (teste 2024+: +0,0021, p=0,005)."""
    ini = pd.Timestamp(hoje)
    j = [x for x in series if x["tier"] in T and x["v1"] != x["v2"] and max(x["v1"], x["v2"]) >= 2
         and ini - pd.DateOffset(months=meses) <= x["dt"] < ini]
    if not j:
        return 1.0
    return min(GRADE, key=lambda c: va.media([be.ll(be.p_serie(cal.ajusta(x["p1"], c), max(x["v1"], x["v2"])),
                                                    int(x["v1"] > x["v2"])) for x in j]))


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    d = be.carregar()
    el = te.carregar_elencos()
    m, s = ej.rodar(d, el, ej.W_OFICIAL, ej.KJ_OFICIAL)
    pares = [(dt, p, y) for dt, t, p, y in m.values() if t in T]
    meses = pd.date_range(be.INICIO_TESTE, d.dt.max(), freq="MS")
    cs = {mm: c_movel(pares, mm) for mm in meses}
    print("c do mapa por mes (12 meses antes):", " ".join(f"{mm:%y-%m}:{c}" for mm, c in cs.items()))
    mes = lambda dt: pd.Timestamp(dt.year, dt.month, 1)
    B = {i: be.ll(p, y) for i, (dt, t, p, y) in m.items() if dt >= be.INICIO_TESTE and t in T}
    V = {i: be.ll(cal.ajusta(m[i][2], cs[mes(m[i][0])]), m[i][3]) for i in B}
    g, lo, hi, p, n = va.pareado(B, V)
    print(f"MAPA S/A/B: sem {va.media(list(B.values())):.4f} -> movel {va.media(list(V.values())):.4f} "
          f"ganho {g:+.4f} [{lo:+.4f}, {hi:+.4f}] p={p:.3f} {'PASSA' if g > 0.002 and p < 0.05 and lo > 0 else 'nao passa'}")
    # serie: c da serie tambem movel, medido nas series dos 12 meses anteriores
    ser = [x for x in s if x["tier"] in T and x["v1"] != x["v2"] and max(x["v1"], x["v2"]) >= 2]

    def c_serie(ini):
        j = [x for x in ser if ini - pd.DateOffset(months=12) <= x["dt"] < ini]
        return min(GRADE, key=lambda c: va.media([be.ll(be.p_serie(cal.ajusta(x["p1"], c), max(x["v1"], x["v2"])),
                                                         int(x["v1"] > x["v2"])) for x in j]))
    css = {mm: c_serie(mm) for mm in meses}
    print("c da serie por mes:", " ".join(f"{mm:%y-%m}:{c}" for mm, c in css.items()))
    SB = va.por_serie(s, be.INICIO_TESTE, tiers=T)
    SV = va.por_serie([dict(x, p1=cal.ajusta(x["p1"], css.get(mes(x["dt"]), 1.0))) for x in s], be.INICIO_TESTE, tiers=T)
    g, lo, hi, p, n = va.pareado(SB, SV)
    print(f"SERIE S/A/B: sem {va.media(list(SB.values())):.4f} -> movel {va.media(list(SV.values())):.4f} "
          f"ganho {g:+.4f} [{lo:+.4f}, {hi:+.4f}] p={p:.3f} {'PASSA' if g > 0.002 and p < 0.05 and lo > 0 else 'nao passa'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
