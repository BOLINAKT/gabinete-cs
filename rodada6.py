# -*- coding: utf-8 -*-
"""Rodada 6 (26/10/2026): ideias SOBRE o Elo por jogador (modelo oficial), uma de cada vez.

As rodadas 2-3 foram medidas antes das correcoes (nomes, elenco); aqui de novo,
sobre o oficial (w=0, kj=32, serie com c=0,9):
  margem     o resultado do mapa vira s = a*vitoria + (1-a)*fracao de rounds
  tier       kj multiplicado por tier (S, A, B)
  incerteza  jogador com POUCOS mapas aprende mais rapido: kj*(1 + m*n0/(n0+n))
Escolha na VALIDACAO 2021-2023 (mapa S/A); TESTE 2024+ uma vez; mapa e serie S/A.
"""
from __future__ import annotations

import sys
from collections import defaultdict

import pandas as pd

import base_elo as be
import calibra_serie as cal
import elo_jogador as ej
import troca_elenco as te
import variantes as va

VAL = (pd.Timestamp("2021-01-01"), be.INICIO_TESTE)
K_TIME = ej.K
KJ = ej.KJ_OFICIAL


def rodar(d, el, a=1.0, k_tier=None, n0=0.0, mult=0.0):
    r, pr, nj = defaultdict(lambda: 1500.0), {}, defaultdict(int)
    fora, series = {}, {}
    for x in d.itertuples(index=False):
        t1, t2 = x.time1, x.time2
        forca, elen = {}, {}
        for t in (t1, t2):
            e = te.elenco(el, t, x.dt)
            e = e if e is not None and 3 <= len(e) <= 7 else None
            elen[t] = e
            if e is None:
                forca[t] = r[t]
                continue
            for j in e:
                pr.setdefault(j, r[t])
            forca[t] = sum(pr[j] for j in e) / len(e)
        p = 1 / (1 + 10 ** (-(forca[t1] - forca[t2]) / 400))
        y = 1 if x.vencedor == 1 else 0
        tot = x.rounds1 + x.rounds2
        s_obs = a * y + (1 - a) * (x.rounds1 / tot if tot > 0 else y)
        fora[(x.pagina, x.data, t1, t2, x.mapa_n)] = (x.dt, x.tier, p, y)
        ch = (x.pagina, x.data, t1, t2)
        sr = series.setdefault(ch, {"dt": x.dt, "tier": x.tier, "p1": p, "v1": 0, "v2": 0, "id": ch})
        sr["v1" if y else "v2"] += 1
        kt = (k_tier or {}).get(x.tier, 1.0)
        for t, sinal in ((t1, 1), (t2, -1)):
            r[t] += sinal * K_TIME * (s_obs - p)
            if elen[t] is not None:
                for j in elen[t]:
                    k = KJ * kt * (1 + (mult * n0 / (n0 + nj[j]) if n0 else 0.0))
                    pr[j] += sinal * k * (s_obs - p)
                    nj[j] += 1
    return fora, list(series.values())


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    d = be.carregar()
    el = te.carregar_elencos()
    bm, bs = rodar(d, el)
    B = te.perdas(bm, be.INICIO_TESTE)
    print(f"oficial: mapa S/A teste {va.media(list(B.values())):.4f}")
    ideias = {
        "margem": [{"a": a} for a in (0.7, 0.5, 0.3)],
        "tier": [{"k_tier": dict(zip("SAB", g))} for g in ((1.25, 1, 0.8), (1.5, 1, 0.7), (1.25, 1, 1), (1, 1, 0.7))],
        "incerteza": [{"n0": n0, "mult": m} for n0 in (20, 60) for m in (1.0, 2.0)],
    }
    for nome, grade in ideias.items():
        notas = []
        for g in grade:
            m, _ = rodar(d, el, **g)
            notas.append((va.media(list(te.perdas(m, *VAL).values())), str(g), g))
            print(f"  {nome:9s} {str(g):40s} validacao {notas[-1][0]:.4f}", flush=True)
        base_val = va.media(list(te.perdas(bm, *VAL).values()))
        melhor = min(notas)
        if melhor[0] >= base_val:
            print(f"  {nome}: nenhuma variante melhora a VALIDACAO ({base_val:.4f}) -> nao vai ao teste\n")
            continue
        vm, vs = rodar(d, el, **melhor[2])
        V = te.perdas(vm, be.INICIO_TESTE)
        g_, lo, hi, p, n = va.pareado(B, V)
        ok = g_ > 0.002 and p < 0.05 and lo > 0
        print(f"  {nome} {melhor[1]}: MAPA {va.media(list(B.values())):.4f} -> {va.media(list(V.values())):.4f} "
              f"ganho {g_:+.4f} [{lo:+.4f}, {hi:+.4f}] p={p:.3f} {'PASSA' if ok else 'nao passa'}")
        cb = [dict(x, p1=cal.ajusta(x["p1"], 0.9)) for x in bs]
        cv = [dict(x, p1=cal.ajusta(x["p1"], 0.9)) for x in vs]
        SB, SV = va.por_serie(cb, be.INICIO_TESTE, tiers=("S", "A")), va.por_serie(cv, be.INICIO_TESTE, tiers=("S", "A"))
        g_, lo, hi, p, n = va.pareado(SB, SV)
        ok = g_ > 0.002 and p < 0.05 and lo > 0
        print(f"  {nome}: SERIE S/A {va.media(list(SB.values())):.4f} -> {va.media(list(SV.values())):.4f} "
              f"ganho {g_:+.4f} [{lo:+.4f}, {hi:+.4f}] p={p:.3f} {'PASSA' if ok else 'nao passa'}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
