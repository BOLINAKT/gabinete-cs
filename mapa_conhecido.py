# -*- coding: utf-8 -*-
"""Saber O MAPA melhora a previsao do mapa? (26/10/2026)

Pergunta dele: "times com 3 mapas com 15+ jogos com 80% de winrate -- se a odd e
even para os dois lados, esse time nao pode ser mais odd even". A rodada 1 testou
o ajuste por mapa so na SERIE (antes do veto, os mapas nao sao conhecidos). Aqui
o caso DELE: o mapa ja e conhecido (depois do veto) e a previsao e do MAPA.

Tres jeitos de prever o mapa, prequencial, teste 2024+ (S e A):
  base      Elo global do time (ignora qual mapa e)
  elo_mapa  global + desvio do time naquele mapa (aprendido jogo a jogo)
  winrate   global + a taxa de vitoria do time NAQUELE mapa, encolhida para 50%
            com peso n/(n+m) -- o "80% em 15 jogos" dele, com o ruido de amostra
            pequena levado em conta (m escolhido na validacao)
Ganho pareado por mapa, regua da casa (ganho > 0,002, p < 0,05, IC acima de 0).
"""
from __future__ import annotations

import math
import random
import sys
from collections import defaultdict

import pandas as pd

import base_elo as be

TIERS = ("S", "A")


def rodar(d, k=24, k_mapa=0.0, m_winrate=None, peso_wr=0.0):
    r = defaultdict(lambda: 1500.0)
    rm = defaultdict(float)
    vit, jog = defaultdict(int), defaultdict(int)
    fora = []
    for x in d.itertuples(index=False):
        a, b, m = x.time1, x.time2, x.mapa
        dif = r[a] - r[b] + rm[(a, m)] - rm[(b, m)]
        if m_winrate is not None:
            def wr(t):
                n = jog[(t, m)]
                return (vit[(t, m)] + 0.5 * m_winrate) / (n + m_winrate)
            # diferenca de taxa (em logit) convertida para a escala do Elo
            la, lb = wr(a), wr(b)
            dif += peso_wr * 400 / math.log(10) * (math.log(la / (1 - la)) - math.log(lb / (1 - lb)))
        p = 1 / (1 + 10 ** (-dif / 400))
        y = 1 if x.vencedor == 1 else 0
        fora.append((x.dt, x.tier, p, y))
        r[a] += k * (y - p)
        r[b] -= k * (y - p)
        if k_mapa:
            rm[(a, m)] += k_mapa * (y - p)
            rm[(b, m)] -= k_mapa * (y - p)
        for t, ganhou in ((a, y), (b, 1 - y)):
            jog[(t, m)] += 1
            vit[(t, m)] += ganhou
    return fora


def perdas(prev, desde, ate=None):
    return [be.ll(p, y) for dt, t, p, y in prev if dt >= desde and (ate is None or dt < ate) and t in TIERS]


def media(v):
    return sum(v) / len(v)


def pareado(b, v, n=2000):
    dif = [x - y for x, y in zip(b, v)]
    rnd = random.Random(7)
    boots = sorted(media([dif[rnd.randrange(len(dif))] for _ in dif]) for _ in range(n))
    return media(dif), boots[int(0.025 * n)], boots[int(0.975 * n)], sum(1 for x in boots if x <= 0) / n


def main() -> int:
    d = be.carregar()
    val = (pd.Timestamp("2021-01-01"), be.INICIO_TESTE)
    base = rodar(d)
    print(f"base (Elo global, K=24): logloss do mapa {media(perdas(base, be.INICIO_TESTE)):.4f}  "
          f"(validacao {media(perdas(base, *val)):.4f})")
    cand = {"elo_mapa": [{"k_mapa": g} for g in (5, 10, 20)],
            "winrate": [{"m_winrate": m, "peso_wr": w} for m in (5, 10, 20) for w in (0.3, 0.6, 1.0)]}
    b_teste = perdas(base, be.INICIO_TESTE)
    for nome, grade in cand.items():
        melhor = min(grade, key=lambda g: media(perdas(rodar(d, **g), *val)))
        v = perdas(rodar(d, **melhor), be.INICIO_TESTE)
        g, lo, hi, p = pareado(b_teste, v)
        passa = g > 0.002 and p < 0.05 and lo > 0
        print(f"{nome:9s} {str(melhor):34s} logloss {media(v):.4f}  ganho {g:+.4f} "
              f"IC95 [{lo:+.4f}, {hi:+.4f}] p={p:.3f}  {'PASSA' if passa else 'nao passa'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
