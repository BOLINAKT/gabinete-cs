# -*- coding: utf-8 -*-
"""ENTROSAMENTO (26/10/2026): elenco recem-montado rende abaixo da media das notas?

Forca do time = media das notas do elenco - beta * (fracao de jogadores que
entraram nos ultimos `dias`). beta e dias na VALIDACAO 2021-2023 (S/A/B);
TESTE 2024+ uma vez. Datas de entrada: elencos.csv (Liquipedia).
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


def entradas(caminho="elencos.csv") -> dict:
    e = pd.read_csv(caminho, dtype=str).fillna("")
    fora = defaultdict(list)
    for t, j, a in zip(e.time, e.jogador, e.entrada):
        if a:
            fora[(t, j)].append(pd.Timestamp(a))
    return fora


def rodar(d, el, ent, beta=0.0, dias=60, kj=ej.KJ_OFICIAL):
    r, pr = defaultdict(lambda: 1500.0), {}
    fora = {}
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
                pr.setdefault(j, r[t])
            novos = 0
            if beta:
                for j in e:
                    datas = [dd for dd in ent.get((t, j), []) if dd <= x.dt]
                    if datas and (x.dt - max(datas)).days <= dias:
                        novos += 1
            forca[t] = sum(pr[j] for j in e) / len(e) - beta * novos / len(e)
        p = 1 / (1 + 10 ** (-(forca[a] - forca[b]) / 400))
        y = 1 if x.vencedor == 1 else 0
        fora[(x.pagina, x.data, a, b, x.mapa_n)] = (x.dt, x.tier, p, y)
        for t, sinal in ((a, 1), (b, -1)):
            r[t] += sinal * ej.K * (y - p)
            if elen[t] is not None:
                for j in elen[t]:
                    pr[j] += sinal * kj * (y - p)
    return fora


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    d = be.carregar()
    el = te.carregar_elencos()
    ent = entradas()
    base = rodar(d, el, ent)
    val = lambda m: va.media([be.ll(p, y) for dt, t, p, y in m.values() if VAL[0] <= dt < VAL[1] and t in T])
    print(f"base validacao {val(base):.4f}")
    notas = []
    for dias in (30, 60, 120):
        for beta in (25, 50, 100):
            m = rodar(d, el, ent, beta, dias)
            notas.append((val(m), beta, dias, m))
            print(f"  dias={dias:3d} beta={beta:3d} validacao {notas[-1][0]:.4f}", flush=True)
    v, beta, dias, m = min(notas, key=lambda x: x[0])
    if v >= val(base):
        print("nenhuma melhora a validacao -> nao vai ao teste")
        return 0
    B = {i: be.ll(p, y) for i, (dt, t, p, y) in base.items() if dt >= be.INICIO_TESTE and t in T}
    V = {i: be.ll(m[i][2], m[i][3]) for i in B}
    g, lo, hi, p, n = va.pareado(B, V)
    print(f"escolhido beta={beta} dias={dias}: MAPA S/A/B {va.media(list(B.values())):.4f} -> {va.media(list(V.values())):.4f} "
          f"ganho {g:+.4f} [{lo:+.4f}, {hi:+.4f}] p={p:.3f} {'PASSA' if g > 0.002 and p < 0.05 and lo > 0 else 'nao passa'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
