# -*- coding: utf-8 -*-
"""Os pontos do ranking da Valve ajudam o Elo por jogador? (26/10/2026)

logit(p') = logit(p_elo_jogador) + beta * (pontos_a - pontos_b) / 100
Pontos da classificacao global publicada ANTES do dia do jogo (data do arquivo
+ 1 dia <= jogo). Time casado pelo ELENCO (3+ jogadores em comum, sem depender
de nome); time com elenco conhecido mas fora da lista = pontos minimos daquela
data (esta abaixo do corte); sem elenco conhecido = sem ajuste.
O ranking global so existe desde 08/2024: beta escolhido em 06/08/2024-30/06/2025,
TESTE 01/07/2025+ uma vez, contra o modelo atual na mesma janela.
"""
from __future__ import annotations

import bisect
import math
import sys
from collections import defaultdict

import pandas as pd

import base_elo as be
import calibra_serie as cal
import elo_jogador as ej
import troca_elenco as te
import variantes as va

ESCOLHA = (pd.Timestamp("2024-08-07"), pd.Timestamp("2025-07-01"))
TESTE = pd.Timestamp("2025-07-01")


def carregar_vrs():
    v = pd.read_csv("vrs.csv", dtype={"elenco": str}).fillna("")
    datas, fotos = [], []
    for dd, g in v.groupby("data"):
        por_jog = defaultdict(list)
        lista = []
        for pts, el in zip(g.pontos, g.elenco):
            js = frozenset(j.lower() for j in el.split(";") if j)
            lista.append((pts, js))
            for j in js:
                por_jog[j].append(len(lista) - 1)
        datas.append(pd.Timestamp(dd) + pd.Timedelta(days=1))
        fotos.append((lista, por_jog, int(g.pontos.min())))
    return datas, fotos


def pontos(vrs, elenco, dt):
    datas, fotos = vrs
    i = bisect.bisect_right(datas, dt) - 1
    if i < 0 or elenco is None or len(elenco) < 3:
        return None
    lista, por_jog, minimo = fotos[i]
    el = {j.lower() for j in elenco}
    cont = defaultdict(int)
    for j in el:
        for k in por_jog.get(j, ()):
            cont[k] += 1
    if cont:
        k, n = max(cont.items(), key=lambda x: x[1])
        if n >= 3:
            return lista[k][0]
    return minimo


def main() -> int:
    d = be.carregar()
    el = te.carregar_elencos()
    vrs = carregar_vrs()
    m, s = ej.rodar(d, el, ej.W_OFICIAL, ej.KJ_OFICIAL)
    dif = {}
    for x in d[d.dt >= ESCOLHA[0]].itertuples(index=False):
        pa = pontos(vrs, te.elenco(el, x.time1, x.dt), x.dt)
        pb = pontos(vrs, te.elenco(el, x.time2, x.dt), x.dt)
        if pa is not None and pb is not None:
            dif[(x.pagina, x.data, x.time1, x.time2, x.mapa_n)] = (pa - pb) / 100
    print(f"mapas com pontos dos dois lados desde 08/2024: {len(dif)}")

    def com(beta, ids):
        fora = {}
        for i in ids:
            dt, t, p, y = m[i]
            p = min(max(p, 1e-6), 1 - 1e-6)
            z = math.log(p / (1 - p)) + beta * dif.get(i, 0.0)
            fora[i] = be.ll(1 / (1 + math.exp(-z)), y)
        return fora

    sel = lambda a, b=None: [i for i, (dt, t, p, y) in m.items()
                             if dt >= a and (b is None or dt < b) and t in ("S", "A")]
    esc, tes = sel(*ESCOLHA), sel(TESTE)
    grade = [b / 100 for b in range(0, 41, 5)]
    for b in grade:
        print(f"  beta={b:.2f} escolha {va.media(list(com(b, esc).values())):.4f}")
    beta = min(grade, key=lambda b: va.media(list(com(b, esc).values())))
    B, V = com(0.0, tes), com(beta, tes)
    g, lo, hi, p, n = va.pareado(B, V)
    ok = g > 0.002 and p < 0.05 and lo > 0
    print(f"MAPA S/A beta={beta}: {va.media(list(B.values())):.4f} -> {va.media(list(V.values())):.4f} "
          f"ganho {g:+.4f} IC95 [{lo:+.4f}, {hi:+.4f}] p={p:.3f} n={n} {'PASSA' if ok else 'nao passa'}")
    # serie (com a calibracao oficial c=0,9): p do mapa 1 com o ajuste
    def series(beta):
        fora = []
        for x in s:
            i = (*x["id"], 1)
            p = min(max(x["p1"], 1e-6), 1 - 1e-6)
            z = math.log(p / (1 - p)) + beta * dif.get(i, 0.0)
            fora.append(dict(x, p1=cal.ajusta(1 / (1 + math.exp(-z)), 0.9)))
        return fora
    for tiers in (("S",), ("S", "A")):
        B, V = va.por_serie(series(0.0), TESTE, tiers=tiers), va.por_serie(series(beta), TESTE, tiers=tiers)
        g, lo, hi, p, n = va.pareado(B, V)
        ok = g > 0.002 and p < 0.05 and lo > 0
        print(f"SERIE {'/'.join(tiers)}: {va.media(list(B.values())):.4f} -> {va.media(list(V.values())):.4f} "
              f"ganho {g:+.4f} IC95 [{lo:+.4f}, {hi:+.4f}] p={p:.3f} n={n} {'PASSA' if ok else 'nao passa'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
