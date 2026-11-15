# -*- coding: utf-8 -*-
"""FASE 3 do plano do CS (15/11/2026): da para precificar jogo de time com POUCO DADO?

Hoje o app se recusa quando um dos times tem menos de 30 mapas no ultimo ano ou esta parado ha
mais de 120 dias ("sem preco do modelo": 28 de 40 jogos da agenda). Aqui, com TODOS os tiers
(inclusive C), mede-se o que o Elo por jogador acerta nesses jogos, por faixa de dado do time
mais fraco de historico, e quanto a chance precisa ser ENCOLHIDA (c) para ficar honesta.
O c de cada faixa e escolhido em 2024 e conferido em 2025+ (cego). Regua: 0,6931 = moeda.
"""
from __future__ import annotations

import sys
from collections import defaultdict, deque

import pandas as pd

import base_elo as be
import calibra_serie as cal
import elo_jogador as ej
import troca_elenco as te
import variantes as va

FAIXAS = ((0, 0, "estreia (0 mapas)"), (1, 9, "1-9 mapas"), (10, 29, "10-29 mapas"), (30, 10 ** 6, "30+ (hoje precifica)"))
GRADE = [x / 100 for x in range(20, 111, 5)]


def faixa(n: int) -> str:
    return next(nome for lo, hi, nome in FAIXAS if lo <= n <= hi)


def contagens(d: pd.DataFrame) -> dict:
    """{chave do mapa: (min de mapas no ultimo ano entre os dois, max de dias parado)} -- pre-jogo."""
    hist = defaultdict(deque)
    fora = {}
    ano = pd.Timedelta(days=365)
    for x in d.itertuples(index=False):
        ns, parado = [], []
        for t in (x.time1, x.time2):
            h = hist[t]
            while h and h[0] < x.dt - ano:
                h.popleft()
            ns.append(len(h))
            parado.append((x.dt - h[-1]).days if h else 9999)
        fora[(x.pagina, x.data, x.time1, x.time2, x.mapa_n)] = (min(ns), max(parado))
        for t in (x.time1, x.time2):
            hist[t].append(x.dt)
    return fora


def medir() -> dict:
    d = be.carregar(incluir_c=True)
    mapas, _ = ej.rodar(d, te.carregar_elencos(), ej.W_OFICIAL, ej.KJ_OFICIAL)
    cont = contagens(d)
    lin = []
    for k, (dt, tier, p, y) in mapas.items():
        n, parado = cont[k]
        lin.append({"dt": dt, "tier": tier, "p": p, "y": y, "faixa": faixa(n), "parado": parado})
    corte = pd.Timestamp("2025-01-01")
    out = {}
    for _lo, _hi, nome in FAIXAS:
        tr = [l for l in lin if l["faixa"] == nome and pd.Timestamp("2024-01-01") <= l["dt"] < corte]
        te_ = [l for l in lin if l["faixa"] == nome and l["dt"] >= corte]
        if len(tr) < 200 or len(te_) < 200:
            out[nome] = {"n_treino": len(tr), "n_teste": len(te_)}
            continue
        c = min(GRADE, key=lambda c: va.media([be.ll(cal.ajusta(l["p"], c), l["y"]) for l in tr]))
        B = {i: be.ll(0.5, l["y"]) for i, l in enumerate(te_)}
        C = {i: be.ll(l["p"], l["y"]) for i, l in enumerate(te_)}
        V = {i: be.ll(cal.ajusta(l["p"], c), l["y"]) for i, l in enumerate(te_)}
        g, lo, hi, p, n = va.pareado(B, V)
        ac = va.media([int((l["p"] >= 0.5) == (l["y"] == 1)) for l in te_])
        out[nome] = {"n_treino": len(tr), "n_teste": n, "c": c, "ll_cru": round(va.media(list(C.values())), 4),
                     "ll_encolhido": round(va.media(list(V.values())), 4), "ganho_sobre_moeda": round(g, 4),
                     "ic95": [round(lo, 4), round(hi, 4)], "acerto": round(ac, 3)}
    return out


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    for nome, r in medir().items():
        print(nome, r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
