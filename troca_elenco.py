# -*- coding: utf-8 -*-
"""TROCA DE ELENCO sobre o modelo oficial (Elo K=24, nomes certos) (26/10/2026).

Elenco do time numa data = jogadores de elencos.csv com entrada <= data < saida.
Entre um mapa e o proximo do mesmo time, se o elenco mudou:
  trocados = 1 - (jogadores que ficaram) / max(5, tamanho do elenco novo)
  encolhe  r = 1500 + (r - 1500) * (1 - f * trocados)
  acelera  K * (1 + g) nos `dias` seguintes a troca (aprende o time novo mais rapido)
Time sem elenco na Liquipedia: sem ajuste. f, g escolhidos na VALIDACAO; TESTE uma vez.
"""
from __future__ import annotations

import bisect
import sys
from collections import defaultdict

import pandas as pd

import base_elo as be
import variantes as va

K = 24
VAL = (pd.Timestamp("2021-01-01"), be.INICIO_TESTE)


def carregar_elencos(caminho="elencos.csv") -> dict:
    """{time: (datas de mudanca ordenadas, [conjunto do elenco valido a partir de cada data])}."""
    e = pd.read_csv(caminho, dtype=str).fillna("")
    fora = {}
    for t, g in e.groupby("time"):
        datas = sorted({x for x in list(g.entrada) + list(g.saida) if x})
        sets = []
        for dd in datas:
            sets.append(frozenset(j for j, a, s in zip(g.jogador, g.entrada, g.saida)
                                  if (not a or a <= dd) and (not s or s > dd)))
        fora[t] = ([pd.Timestamp(x) for x in datas], sets)
    return fora


def elenco(el, t, dt):
    if t not in el:
        return None
    datas, sets = el[t]
    i = bisect.bisect_right(datas, dt) - 1
    return sets[i] if i >= 0 else None


def rodar(d, el, f=0.0, g=0.0, dias=60):
    r, ant, troca_em, frac_troca = defaultdict(lambda: 1500.0), {}, {}, {}
    fora, series = {}, {}
    for x in d.itertuples(index=False):
        a, b = x.time1, x.time2
        for t in (a, b):
            agora = elenco(el, t, x.dt)
            antes = ant.get(t)
            if agora is not None and antes is not None and agora != antes and len(agora) >= 3:
                trocados = 1 - len(agora & antes) / max(5, len(agora))
                if trocados > 0:
                    r[t] = 1500 + (r[t] - 1500) * (1 - f * trocados)
                    troca_em[t], frac_troca[t] = x.dt, trocados
            if agora is not None:
                ant[t] = agora
        p = 1 / (1 + 10 ** (-(r[a] - r[b]) / 400))
        y = 1 if x.vencedor == 1 else 0
        fora[(x.pagina, x.data, a, b, x.mapa_n)] = (x.dt, x.tier, p, y)
        ch = (x.pagina, x.data, a, b)
        s = series.setdefault(ch, {"dt": x.dt, "tier": x.tier, "p1": p, "v1": 0, "v2": 0, "id": ch})
        s["v1" if y else "v2"] += 1
        for t, sinal in ((a, 1), (b, -1)):
            k = K
            if g and t in troca_em and (x.dt - troca_em[t]).days <= dias:
                k = K * (1 + g * frac_troca[t])
            r[t] += sinal * k * (y - p)
    return fora, list(series.values())


def perdas(f, desde, ate=None):
    return {i: be.ll(p, y) for i, (dt, t, p, y) in f.items()
            if dt >= desde and (ate is None or dt < ate) and t in ("S", "A")}


def main() -> int:
    d = be.carregar()
    el = carregar_elencos()
    bm, bs = rodar(d, el)
    bt = perdas(bm, be.INICIO_TESTE)
    print(f"base Elo K=24: mapa S/A {va.media(list(bt.values())):.4f}")
    grade = [{"f": f, "g": g} for f in (0.0, 0.2, 0.4, 0.6) for g in (0.0, 0.5, 1.0, 2.0)]
    notas = []
    for c in grade:
        m, _ = rodar(d, el, **c)
        notas.append((va.media(list(perdas(m, *VAL).values())), str(c), c))
        print(f"  {str(c):24s} validacao {notas[-1][0]:.4f}", flush=True)
    melhor = min(notas)[2]
    vm, vs = rodar(d, el, **melhor)
    v = perdas(vm, be.INICIO_TESTE)
    g_, lo, hi, p, n = va.pareado(bt, v)
    ok = g_ > 0.002 and p < 0.05 and lo > 0
    print(f"\nescolhido {melhor}: MAPA {va.media(list(bt.values())):.4f} -> {va.media(list(v.values())):.4f} "
          f"ganho {g_:+.4f} IC95 [{lo:+.4f}, {hi:+.4f}] p={p:.3f} {'PASSA' if ok else 'nao passa'}")
    for tiers in (("S",), ("S", "A")):
        B, V = va.por_serie(bs, be.INICIO_TESTE, tiers=tiers), va.por_serie(vs, be.INICIO_TESTE, tiers=tiers)
        g_, lo, hi, p, n = va.pareado(B, V)
        print(f"SERIE {'/'.join(tiers)} {va.media(list(B.values())):.4f} -> {va.media(list(V.values())):.4f} "
              f"ganho {g_:+.4f} IC95 [{lo:+.4f}, {hi:+.4f}] p={p:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
