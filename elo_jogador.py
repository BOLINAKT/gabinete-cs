# -*- coding: utf-8 -*-
"""ELO POR JOGADOR, que leva a nota quando muda de time (26/10/2026).

Encolher o time na troca de elenco PIOROU (troca_elenco.py): quem troca costuma
trocar para melhor, e o que importa e QUEM chegou. Aqui:
  - cada jogador tem nota; ao aparecer pela 1a vez, nasce com a nota do time;
  - forca do time = w * Elo do time + (1 - w) * media das notas do elenco atual
    (elenco das datas da Liquipedia; sem elenco conhecido, so o Elo do time);
  - depois do mapa, o time e cada jogador do elenco recebem a mesma atualizacao.
w escolhido na VALIDACAO; TESTE 2024+ uma vez; regua da casa.
"""
from __future__ import annotations

import sys
from collections import defaultdict

import pandas as pd

import base_elo as be
import troca_elenco as te
import variantes as va

K = 24
VAL = (pd.Timestamp("2021-01-01"), be.INICIO_TESTE)


W_OFICIAL, KJ_OFICIAL = 0.0, 32   # validacao 26/10/2026 (grade w 0..0,75; kj 16..64)


def forca(t, dt, r, pr, el, w=W_OFICIAL):
    """Forca do time na data: Elo do time misturado com a media do elenco."""
    e = te.elenco(el, t, dt)
    if e is None or not 3 <= len(e) <= 7 or w >= 1:
        return r[t]
    return w * r[t] + (1 - w) * sum(pr.get(j, r[t]) for j in e) / len(e)


def rodar(d, el, w=1.0, kj=None, estado=False):
    kj = K if kj is None else kj
    r, pr = defaultdict(lambda: 1500.0), {}
    fora, series = {}, {}
    for x in d.itertuples(index=False):
        a, b = x.time1, x.time2
        forca, elen = {}, {}
        for t in (a, b):
            e = te.elenco(el, t, x.dt)
            e = e if e is not None and 3 <= len(e) <= 7 else None
            elen[t] = e
            if e is None or w >= 1:
                forca[t] = r[t]
                continue
            for j in e:
                pr.setdefault(j, r[t])
            forca[t] = w * r[t] + (1 - w) * sum(pr[j] for j in e) / len(e)
        p = 1 / (1 + 10 ** (-(forca[a] - forca[b]) / 400))
        y = 1 if x.vencedor == 1 else 0
        fora[(x.pagina, x.data, a, b, x.mapa_n)] = (x.dt, x.tier, p, y)
        ch = (x.pagina, x.data, a, b)
        s = series.setdefault(ch, {"dt": x.dt, "tier": x.tier, "p1": p, "v1": 0, "v2": 0, "id": ch})
        s["v1" if y else "v2"] += 1
        for t, sinal in ((a, 1), (b, -1)):
            r[t] += sinal * K * (y - p)
            if elen[t] is not None and w < 1:
                for j in elen[t]:
                    pr[j] += sinal * kj * (y - p)
    if estado:
        return r, pr
    return fora, list(series.values())


def main() -> int:
    d = be.carregar()
    el = te.carregar_elencos()
    bm, bs = rodar(d, el)
    bt = te.perdas(bm, be.INICIO_TESTE)
    notas = []
    for w in (0.75, 0.5, 0.25, 0.0):
        for kj in (16, 24, 32):
            m, _ = rodar(d, el, w, kj)
            notas.append((va.media(list(te.perdas(m, *VAL).values())), w, kj))
            print(f"  w={w} kj={kj} validacao {notas[-1][0]:.4f}", flush=True)
    _, w, kj = min(notas)
    vm, vs = rodar(d, el, w, kj)
    v = te.perdas(vm, be.INICIO_TESTE)
    g, lo, hi, p, n = va.pareado(bt, v)
    ok = g > 0.002 and p < 0.05 and lo > 0
    print(f"\nescolhido w={w} kj={kj}: MAPA {va.media(list(bt.values())):.4f} -> {va.media(list(v.values())):.4f} "
          f"ganho {g:+.4f} IC95 [{lo:+.4f}, {hi:+.4f}] p={p:.3f} {'PASSA' if ok else 'nao passa'}")
    for tiers in (("S",), ("S", "A")):
        B, V = va.por_serie(bs, be.INICIO_TESTE, tiers=tiers), va.por_serie(vs, be.INICIO_TESTE, tiers=tiers)
        g, lo, hi, p, n = va.pareado(B, V)
        ok = g > 0.002 and p < 0.05 and lo > 0
        print(f"SERIE {'/'.join(tiers)} {va.media(list(B.values())):.4f} -> {va.media(list(V.values())):.4f} "
              f"ganho {g:+.4f} IC95 [{lo:+.4f}, {hi:+.4f}] p={p:.3f} {'PASSA' if ok else 'nao passa'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
