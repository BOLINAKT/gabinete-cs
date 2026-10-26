# -*- coding: utf-8 -*-
"""MARGEM EM ROUNDS no Elo, forma aditiva conjunta (26/10/2026).

FONTE (abstract aberto em 26/10/2026): Kovalchik 2020, International Journal of
Forecasting 36(4) -- quatro formas de por a margem de vitoria no Elo (tenis,
placar de sets/games, o analogo dos rounds); todas as que usam a margem dentro
do set previram melhor que o Elo de vitoria/derrota, e so a ADITIVA CONJUNTA deu
ratings sem vies e com variancia estavel.
https://ideas.repec.org/a/eee/intfor/v36y2020i4p1329-1341.html

Aqui: o "resultado" do mapa vira  s = a*vitoria + (1-a)*fracao_de_rounds,
com fracao = rounds1 / (rounds1 + rounds2). O Elo atualiza com (s - p). a = 1 e
o Elo de base. a e K escolhidos na VALIDACAO (2021-2023, serie S/A); TESTE 2024+
lido uma vez. Ganho pareado por serie e por mapa, regua da casa.
"""
from __future__ import annotations

import sys
from collections import defaultdict

import pandas as pd

import base_elo as be
import variantes as va

VAL = (pd.Timestamp("2021-01-01"), be.INICIO_TESTE)


def rodar(d, k=24, a=1.0):
    r = defaultdict(lambda: 1500.0)
    series, mapas = {}, []
    for x in d.itertuples(index=False):
        t1, t2 = x.time1, x.time2
        p = 1 / (1 + 10 ** (-(r[t1] - r[t2]) / 400))
        y = 1 if x.vencedor == 1 else 0
        tot = x.rounds1 + x.rounds2
        frac = x.rounds1 / tot if tot > 0 else y
        s_obs = a * y + (1 - a) * frac
        mapas.append((x.dt, x.tier, p, y, (x.pagina, x.data, t1, t2, x.mapa_n)))
        chave = (x.pagina, x.data, t1, t2)
        s = series.setdefault(chave, {"dt": x.dt, "tier": x.tier, "p1": p, "v1": 0, "v2": 0, "id": chave})
        s["v1" if y else "v2"] += 1
        r[t1] += k * (s_obs - p)
        r[t2] -= k * (s_obs - p)
    return list(series.values()), mapas


def perdas_mapa(mapas, desde, ate=None, tiers=("S", "A")):
    return {i: be.ll(p, y) for dt, t, p, y, i in mapas
            if dt >= desde and (ate is None or dt < ate) and t in tiers}


def main() -> int:
    d = be.carregar()
    grade = [(k, a) for k in (40, 56, 72, 96, 128, 160) for a in (0.3, 0.2, 0.1, 0.0)]
    notas = []
    for k, a in grade:
        s, _ = rodar(d, k, a)
        v = va.media(list(va.por_serie(s, *VAL, ("S", "A")).values()))
        notas.append((v, k, a))
        print(f"  K={k:>3} a={a:.1f}  validacao serie S/A {v:.4f}")
    _, k, a = min(notas)
    print(f"\nescolhido na validacao: K={k}, a={a}")
    sb, mb = rodar(d, 24, 1.0)
    sv, mv = rodar(d, k, a)
    for nome, tiers in (("S-Tier", ("S",)), ("S e A", ("S", "A"))):
        b = va.por_serie(sb, be.INICIO_TESTE, tiers=tiers)
        v = va.por_serie(sv, be.INICIO_TESTE, tiers=tiers)
        g, lo, hi, p, n = va.pareado(b, v)
        ok = g > 0.002 and p < 0.05 and lo > 0
        print(f"SERIE {nome:7s} base {va.media(list(b.values())):.4f} -> {va.media(list(v.values())):.4f}  "
              f"ganho {g:+.4f} IC95 [{lo:+.4f}, {hi:+.4f}] p={p:.3f} n={n}  {'PASSA' if ok else 'nao passa'}")
    b, v = perdas_mapa(mb, be.INICIO_TESTE), perdas_mapa(mv, be.INICIO_TESTE)
    g, lo, hi, p, n = va.pareado(b, v)
    print(f"MAPA  S e A   base {va.media(list(b.values())):.4f} -> {va.media(list(v.values())):.4f}  "
          f"ganho {g:+.4f} IC95 [{lo:+.4f}, {hi:+.4f}] p={p:.3f} n={n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
