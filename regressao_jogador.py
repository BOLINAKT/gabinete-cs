# -*- coding: utf-8 -*-
"""REGRESSAO A MEDIA das notas dos jogadores (26/10/2026).

A calibracao movel mostrou o c caindo mes a mes (serie 0,85 em 2025 -> 0,70 em
2026): o modelo fica cada vez mais confiante do que deveria. Suspeita: a nota
de jogador nunca volta para a media; com os anos o espaco entre os times cresce.
Aqui, a cada MES que passa, toda nota de jogador encolhe uma fracao delta para
1500 (aplicado na hora em que o jogador volta a aparecer, pelo tempo decorrido).
delta na VALIDACAO 2021-2023 (S/A/B); TESTE 2024+ uma vez; mapa e serie.
"""
from __future__ import annotations

import sys
from collections import defaultdict

import pandas as pd

import base_elo as be
import elo_jogador as ej
import troca_elenco as te
import variantes as va

VAL = (pd.Timestamp("2021-01-01"), be.INICIO_TESTE)
T = ("S", "A", "B")


def rodar(d, el, delta=0.0, kj=ej.KJ_OFICIAL, estado=False):
    r, pr, visto = defaultdict(lambda: 1500.0), {}, {}
    fora, series = {}, {}
    for x in d.itertuples(index=False):
        a, b = x.time1, x.time2
        forca, elen = {}, {}
        for t in (a, b):
            e = te.elenco(el, t, x.dt)
            e = e if e is not None and 3 <= len(e) <= 7 else None
            elen[t] = e
            if e is None:
                forca[t] = r[t]
                continue
            for j in e:
                if j not in pr:
                    pr[j] = r[t]
                elif delta and j in visto:
                    meses = (x.dt - visto[j]).days / 30.4
                    if meses > 0:
                        pr[j] = 1500 + (pr[j] - 1500) * (1 - delta) ** meses
                visto[j] = x.dt
            forca[t] = sum(pr[j] for j in e) / len(e)
        p = 1 / (1 + 10 ** (-(forca[a] - forca[b]) / 400))
        y = 1 if x.vencedor == 1 else 0
        fora[(x.pagina, x.data, a, b, x.mapa_n)] = (x.dt, x.tier, p, y)
        ch = (x.pagina, x.data, a, b)
        s = series.setdefault(ch, {"dt": x.dt, "tier": x.tier, "p1": p, "v1": 0, "v2": 0, "id": ch})
        s["v1" if y else "v2"] += 1
        for t, sinal in ((a, 1), (b, -1)):
            r[t] += sinal * ej.K * (y - p)
            if elen[t] is not None:
                for j in elen[t]:
                    pr[j] += sinal * kj * (y - p)
    if estado:
        return r, pr
    return fora, list(series.values())


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    d = be.carregar()
    el = te.carregar_elencos()
    runs = {}
    for delta in (0.0, 0.01, 0.02, 0.04, 0.08):
        runs[delta] = rodar(d, el, delta)
        m = runs[delta][0]
        print(f"  delta={delta:.2f} validacao {va.media([be.ll(p, y) for dt, t, p, y in m.values() if VAL[0] <= dt < VAL[1] and t in T]):.4f}",
              flush=True)
    melhor = min(runs, key=lambda k: va.media([be.ll(p, y) for dt, t, p, y in runs[k][0].values()
                                               if VAL[0] <= dt < VAL[1] and t in T]))
    bm, bs = runs[0.0]
    vm, vs = runs[melhor]
    B = {i: be.ll(p, y) for i, (dt, t, p, y) in bm.items() if dt >= be.INICIO_TESTE and t in T}
    V = {i: be.ll(vm[i][2], vm[i][3]) for i in B}
    g, lo, hi, p, n = va.pareado(B, V)
    print(f"escolhido delta={melhor}: MAPA S/A/B {va.media(list(B.values())):.4f} -> {va.media(list(V.values())):.4f} "
          f"ganho {g:+.4f} [{lo:+.4f}, {hi:+.4f}] p={p:.3f} {'PASSA' if g > 0.002 and p < 0.05 and lo > 0 else 'nao passa'}")
    SB, SV = va.por_serie(bs, be.INICIO_TESTE, tiers=T), va.por_serie(vs, be.INICIO_TESTE, tiers=T)
    g, lo, hi, p, n = va.pareado(SB, SV)
    print(f"SERIE S/A/B {va.media(list(SB.values())):.4f} -> {va.media(list(SV.values())):.4f} "
          f"ganho {g:+.4f} [{lo:+.4f}, {hi:+.4f}] p={p:.3f}")
    for nome, mm in (("sem", bm), ("com", vm)):
        print(f"  {nome}: confianca media no teste (|p-0,5|) {va.media([abs(p - .5) for dt, t, p, y in mm.values() if dt >= be.INICIO_TESTE and t in T]):.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
