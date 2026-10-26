# -*- coding: utf-8 -*-
"""MODELO DE ROUNDS por mapa (26/10/2026): total, handicap, rounds de um time, prorrogacao.

Os mercados de rounds da Pinnacle por mapa: total (21,5; 19,5-23,5), handicap
(+-2,5/3,5/4,5) e rounds de um time (11,5/12,5/13,5). Todos saem da distribuicao
do PLACAR do mapa.

Regras do CS2 (MR12): primeiro a 13; em 12-12, prorrogacao MR3 (primeiro a 4 de
6; em 3-3, outra). So mapas de CS2 (desde 27/09/2023; 99,8% dos placares validos).

Modelo: a chance do time A ganhar o MAPA (Elo por jogador, fora da amostra) vira
uma chance por ROUND q; o placar sai por conta exata (programacao dinamica).
  simples      q fixa no mapa todo
  dispersao    q ~ Beta(media mu, concentracao kappa): o mapa tem "dia" -- gera
               mais placar largo e mais prorrogacao. kappa na VALIDACAO.
Base a bater: a frequencia historica (ignora quem joga). Validacao CS2
10/2023-06/2024; TESTE 07/2024+ uma vez; mapas S/A.
"""
from __future__ import annotations

import math
import sys
from functools import lru_cache

import numpy as np
import pandas as pd
from scipy import stats

import base_elo as be
import elo_jogador as ej
import troca_elenco as te
import variantes as va

INICIO_CS2 = pd.Timestamp("2023-09-27")
VAL = (pd.Timestamp("2023-10-01"), pd.Timestamp("2024-07-01"))
TESTE = pd.Timestamp("2024-07-01")
MAX_OT = 8


def placar_q(q: float) -> dict:
    """{(rounds A, rounds B): prob} para q fixa (rounds independentes)."""
    fora, estados = {}, {(0, 0): 1.0}
    while estados:
        novos = {}
        for (a, b), pr in estados.items():
            for da, db, pp in ((1, 0, q), (0, 1, 1 - q)):
                na, nb = a + da, b + db
                if na == 13 or nb == 13:
                    fora[(na, nb)] = fora.get((na, nb), 0) + pr * pp
                elif na == 12 and nb == 12:
                    novos[(12, 12)] = novos.get((12, 12), 0) + pr * pp
                else:
                    novos[(na, nb)] = novos.get((na, nb), 0) + pr * pp
        empate = novos.pop((12, 12), 0.0)
        estados = novos
        if empate:
            _prorrogacao(q, empate, fora)
    return fora


def _prorrogacao(q, massa, fora):
    base = 12
    for _ in range(MAX_OT):
        est = {(0, 0): massa}
        massa = 0.0
        while est:
            novos = {}
            for (x, y), pr in est.items():
                for dx, dy, pp in ((1, 0, q), (0, 1, 1 - q)):
                    nx, ny = x + dx, y + dy
                    if nx == 4 or ny == 4:
                        k = (base + nx, base + ny)
                        fora[k] = fora.get(k, 0) + pr * pp
                    elif nx == 3 and ny == 3:
                        massa += pr * pp
                    else:
                        novos[(nx, ny)] = novos.get((nx, ny), 0) + pr * pp
            est = novos
        base += 3
        if massa < 1e-9:
            return
    # o resto (prorrogacao infinita) divide-se ao meio: desprezivel
    fora[(base + 1, base - 1)] = fora.get((base + 1, base - 1), 0) + massa / 2
    fora[(base - 1, base + 1)] = fora.get((base - 1, base + 1), 0) + massa / 2


@lru_cache(maxsize=None)
def _q_grade(q2: float) -> tuple:
    d = placar_q(q2)
    return tuple(d.items())


def placar_mistura(mu: float, kappa: float | None, nos: int = 24) -> dict:
    """Distribuicao do placar com q ~ Beta(mu, kappa) (kappa None = q fixa)."""
    if kappa is None:
        return dict(_q_grade(round(mu, 4)))
    a, b = mu * kappa, (1 - mu) * kappa
    qs = stats.beta.ppf((np.arange(nos) + 0.5) / nos, a, b)
    fora = {}
    for q in qs:
        for k, v in _q_grade(round(float(min(max(q, 0.005), 0.995)), 4)):
            fora[k] = fora.get(k, 0) + v / nos
    return fora


def p_vence(dist: dict) -> float:
    return sum(v for (a, b), v in dist.items() if a > b)


class Tabela:
    """p (chance de A no mapa) -> distribuicao do placar, para um kappa."""

    def __init__(self, kappa):
        self.mus = np.round(np.arange(0.20, 0.8001, 0.0025), 4)
        self.dists = [placar_mistura(float(m), kappa) for m in self.mus]
        self.ps = np.array([p_vence(x) for x in self.dists])

    def dist(self, p: float) -> dict:
        """O ponto da grade MAIS PROXIMO de p (antes: sempre o de cima -- puxava
        todas as previsoes ~0,5-1 pp para o time A; achado pelo teste, 26/10/2026)."""
        i = int(np.clip(np.searchsorted(self.ps, p), 1, len(self.ps) - 1))
        return self.dists[i if abs(self.ps[i] - p) < abs(self.ps[i - 1] - p) else i - 1]


def eventos(dist: dict) -> dict:
    """As perguntas dos mercados da Pinnacle (do ponto de vista do time A)."""
    def pr(f):
        return sum(v for (a, b), v in dist.items() if f(a, b))
    fora = {f"total>{x}": pr(lambda a, b, x=x: a + b > x) for x in (19.5, 20.5, 21.5, 22.5, 23.5)}
    fora.update({f"A{-h:+}": pr(lambda a, b, h=h: a - b > h) for h in (2.5, 3.5, 4.5)})
    fora.update({f"B{-h:+}": pr(lambda a, b, h=h: b - a > h) for h in (2.5, 3.5, 4.5)})
    fora.update({f"A>{x}": pr(lambda a, b, x=x: a > x) for x in (11.5, 12.5)})
    fora["prorrogacao"] = pr(lambda a, b: a + b > 24)
    return fora


def ocorreu(a: int, b: int) -> dict:
    return eventos({(a, b): 1.0})


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    d = be.carregar()
    el = te.carregar_elencos()
    m, _ = ej.rodar(d, el, ej.W_OFICIAL, ej.KJ_OFICIAL)
    c = d[(d.dt >= INICIO_CS2) & d.tier.isin(["S", "A"])].copy()
    w, l = c[["rounds1", "rounds2"]].max(axis=1), c[["rounds1", "rounds2"]].min(axis=1)
    c = c[((w == 13) & (l <= 11)) | ((w >= 16) & ((w - 13) % 3 == 0) & (w - l >= 2) & (w - l <= 4))]
    c["p"] = [m[(x.pagina, x.data, x.time1, x.time2, x.mapa_n)][2] for x in c.itertuples(index=False)]
    val, tes = c[(c.dt >= VAL[0]) & (c.dt < VAL[1])], c[c.dt >= TESTE]
    print(f"mapas CS2 S/A: validacao {len(val)}, teste {len(tes)}")
    # base: frequencia de cada evento na validacao (ignora quem joga; simetrica em A/B)
    ev_val = [ocorreu(a, b) for a, b in zip(val.rounds1, val.rounds2)]
    chaves = list(ev_val[0])
    freq = {k: np.mean([e[k] for e in ev_val]) for k in chaves}
    for k in chaves:
        par = ("B" if k[0] == "A" else "A") + k[1:]
        if k.startswith(("A", "B")) and par in freq:
            freq[k] = (np.mean([e[k] for e in ev_val]) + np.mean([e[par] for e in ev_val])) / 2

    def perdas(df, prev_fn):
        """{evento: [logloss por mapa]}."""
        out = {k: [] for k in chaves}
        for a, b, p in zip(df.rounds1, df.rounds2, df.p):
            pr, oc = prev_fn(p), ocorreu(a, b)
            for k in chaves:
                out[k].append(be.ll(pr[k], oc[k]))
        return out
    tabelas = {}
    for kappa in (None, 40, 25, 15):
        tabelas[kappa] = Tabela(kappa)
        pv = perdas(val, lambda p, t=tabelas[kappa]: eventos(t.dist(p)))
        print(f"  kappa={str(kappa):5s} validacao (media dos eventos) {np.mean([np.mean(v) for v in pv.values()]):.4f}",
              flush=True)
    kappa = min(tabelas, key=lambda k: np.mean([np.mean(v) for v in perdas(
        val, lambda p, t=tabelas[k]: eventos(t.dist(p))).values()]))
    print(f"escolhido na validacao: kappa={kappa}\n")
    pb = perdas(tes, lambda p: freq)
    pm = perdas(tes, lambda p, t=tabelas[kappa]: eventos(t.dist(p)))
    print(f"{'evento':12s} {'base':>7s} {'modelo':>7s} {'ganho':>8s}  IC95              p     regua")
    for k in chaves:
        B = dict(enumerate(pb[k])); V = dict(enumerate(pm[k]))
        g, lo, hi, p, n = va.pareado(B, V)
        ok = g > 0.002 and p < 0.05 and lo > 0
        print(f"{k:12s} {np.mean(pb[k]):7.4f} {np.mean(pm[k]):7.4f} {g:+8.4f}  [{lo:+.4f}, {hi:+.4f}] {p:5.3f}  "
              f"{'PASSA' if ok else 'nao'}")
    # calibracao do total 21,5 e da prorrogacao no teste
    t = tabelas[kappa]
    for k in ("total>21.5", "prorrogacao"):
        prev = np.array([eventos(t.dist(p))[k] for p in tes.p])
        real = np.array([ocorreu(a, b)[k] for a, b in zip(tes.rounds1, tes.rounds2)])
        print(f"{k}: previsto medio {prev.mean():.3f} · real {real.mean():.3f} · base {freq[k]:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
