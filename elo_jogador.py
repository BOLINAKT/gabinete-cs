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

import math
import sys
from collections import defaultdict

import pandas as pd

import base_elo as be
import troca_elenco as te
import variantes as va

K = 24
VAL = (pd.Timestamp("2021-01-01"), be.INICIO_TESTE)


W_OFICIAL, KJ_OFICIAL = 0.0, 32   # validacao 26/10/2026 (grade w 0..0,75; kj 16..64)

# AFINADO COMO O LOL (25/11/2026; _medicoes/afinar_cs_elo.py, escolha na validacao 2021-23, teste uma vez):
#  - MARGEM DE ROUNDS como resultado fracionario (o metodo do LoL): y~ = folga + y(1-2folga) + LAM*(saldo -
#    E[saldo|dif])/desvio, com E[saldo|dif] = a*tanh(b*dif) + c ajustado SO em mapas antes de 2021;
#  - K de NOVATO: time/jogador nos primeiros 20 mapas anda com K*(1+KN);
#  - K do time 24 -> 32 (quase neutro: +0,0002).
# Teste 2024+ (S/A/B, 43.110 mapas): logloss 0,6485 -> 0,6443, ganho +0,0042 IC95 [+0,0034; +0,0051];
# 2026 +0,0051 [+0,0035; +0,0068]; S +0,0023, A +0,0087, B +0,0041; ganho nos 6 semestres. Sem a margem perde
# 0,0030; sem o K de novato, 0,0013.
K_OFICIAL, LAM_OFICIAL, FOLGA_OFICIAL, KN_OFICIAL = 32.0, 0.1, 0.1, 1.0
SALDO_ESPERADO = (10.67, 0.002, 0.37, 6.97)   # a, b, c, desvio -- mapas < 2021
NOVATO_MAPAS = 20


def _nota_inicial() -> float:
    """Nota de quem aparece pela 1a vez (funcao, e nao lambda, para o modelo treinado poder ir para o disco)."""
    return 1500.0


def forca(t, dt, r, pr, el, w=W_OFICIAL):
    """Forca do time na data: Elo do time misturado com a media do elenco."""
    e = te.elenco(el, t, dt)
    if e is None or not 3 <= len(e) <= 7 or w >= 1:
        return r[t]
    return w * r[t] + (1 - w) * sum(pr.get(j, r[t]) for j in e) / len(e)


def rodar(d, el, w=1.0, kj=None, estado=False, k=K_OFICIAL, lam=LAM_OFICIAL, folga=FOLGA_OFICIAL,
          kn=KN_OFICIAL):
    """k=24, lam=0, folga=0, kn=0 da EXATAMENTE o motor de antes de 25/11/2026."""
    kj = K if kj is None else kj
    r, pr = defaultdict(_nota_inicial), {}
    n_t, n_j = defaultdict(int), defaultdict(int)
    a_m, b_m, c_m, s_m = SALDO_ESPERADO
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
        dif = forca[a] - forca[b]
        p = 1 / (1 + 10 ** (-dif / 400))
        y = 1 if x.vencedor == 1 else 0
        fora[(x.pagina, x.data, a, b, x.mapa_n)] = (x.dt, x.tier, p, y)
        ch = (x.pagina, x.data, a, b)
        s = series.setdefault(ch, {"dt": x.dt, "tier": x.tier, "p1": p, "v1": 0, "v2": 0, "id": ch})
        s["v1" if y else "v2"] += 1
        yf = folga + y * (1 - 2 * folga)
        if lam:
            try:
                saldo = float(x.rounds1) - float(x.rounds2)
            except (TypeError, ValueError):
                saldo = float("nan")
            if saldo == saldo:
                yf = min(max(yf + lam * (saldo - (a_m * math.tanh(b_m * dif) + c_m)) / s_m, 0.0), 1.0)
        for t, sinal in ((a, 1), (b, -1)):
            r[t] += sinal * (k * (1 + kn) if n_t[t] < NOVATO_MAPAS else k) * (yf - p)
            n_t[t] += 1
            if elen[t] is not None and w < 1:
                for j in elen[t]:
                    pr[j] += sinal * (kj * (1 + kn) if n_j[j] < NOVATO_MAPAS else kj) * (yf - p)
                    n_j[j] += 1
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
