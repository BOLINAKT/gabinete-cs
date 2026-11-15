# -*- coding: utf-8 -*-
"""FASE 5 do plano do CS (15/11/2026): o METODO DELE no total de rounds do mapa.

Os quatro passos (os mesmos do LoL): 1) media recente dos dois; 2) media ajustada pelos
adversarios; 3) historico 5/20/10; 4) stats do campeonato. Hoje o total de rounds sai so da
chance do mapa (rondas.Tabela) e "empata com a frequencia historica". Pergunta: os passos dele,
com pesos medidos, preveem o Mais/Menos melhor que isso?
So CS2 (MR12). Pesos ajustados ate 2024-12, conferidos no cego 2025+. Linhas 20,5 / 21,5 / 22,5.
"""
from __future__ import annotations

import math
import sys
from collections import defaultdict, deque

import numpy as np
import pandas as pd

import base_elo as be
import elo_jogador as ej
import precos_core as pc
import rondas as rd
import troca_elenco as te
import variantes as va

LINHAS = (20.5, 21.5, 22.5)
MIN_JOGOS = 5
AJUSTE = 0.40
PASSA_HIST, TETO_OUTRO = 0.60, 0.30


def _lg(p: float) -> float:
    p = min(max(p, 0.02), 0.98)
    return math.log(p / (1 - p))


def medidas(d: pd.DataFrame) -> dict:
    """{chave do mapa: medidas PRE-JOGO dos dois times} -- totais dos ultimos 20, tendencia dos
    adversarios (media10 do adversario - media geral) e os totais no campeonato (pagina)."""
    hist = defaultdict(lambda: deque(maxlen=20))        # time -> [(total, tendencia do adversario)]
    camp = defaultdict(list)                            # (time, pagina) -> [total]
    geral = deque(maxlen=3000)
    fora = {}
    for x in d.itertuples(index=False):
        if x.dt < pc.INICIO_CS2:
            continue
        tot = float(x.rounds1 + x.rounds2)
        mg = float(np.mean(geral)) if len(geral) >= 200 else 21.0
        m10 = {}
        ok = True
        lado = {}
        for t in (x.time1, x.time2):
            h = list(hist[t])
            if len(h) < MIN_JOGOS:
                ok = False
            ts = [a for a, _ in h]
            m10[t] = float(np.mean(ts[-10:])) if ts else mg
            lado[t] = {"tot": ts, "tend": [b for _, b in h][-10:], "camp": list(camp[(t, x.pagina)])}
        if ok:
            fora[(x.pagina, x.data, x.time1, x.time2, x.mapa_n)] = {"a": lado[x.time1], "b": lado[x.time2], "y": tot}
        for t, o in ((x.time1, x.time2), (x.time2, x.time1)):
            hist[t].append((tot, m10[o] - mg))
            camp[(t, x.pagina)].append(tot)
        geral.append(tot)
    return fora


def sinais(md: dict, L: float) -> dict:
    """Os numeros do metodo para a linha L. Pura."""
    def um(s):
        t10 = s["tot"][-10:]
        tend = s["tend"][-len(t10):]
        aj = [t - AJUSTE * e for t, e in zip(t10, tend)]
        return {"media": float(np.mean(t10)), "media_aj": float(np.mean(aj)),
                "jan": {n: (sum(1 for v in s["tot"][-n:] if v > L), len(s["tot"][-n:])) for n in (5, 10, 20)},
                "camp": (sum(1 for v in s["camp"] if v > L), len(s["camp"]))}
    a, b = um(md["a"]), um(md["b"])
    h = {n: (a["jan"][n][0] + b["jan"][n][0]) / max(1, a["jan"][n][1] + b["jan"][n][1]) for n in (5, 10, 20)}
    camp = None
    if a["camp"][1] >= 3 and b["camp"][1] >= 3:
        camp = (a["camp"][0] / a["camp"][1] + b["camp"][0] / b["camp"][1]) / 2
    return {"media": (a["media"] + b["media"]) / 2, "media_aj": (a["media_aj"] + b["media_aj"]) / 2,
            "h": h, "camp": camp, "linha": L}


def passos(sn: dict, lado: str) -> list:
    mais = lado == "over"
    L = sn["linha"]
    p1 = sn["media"] > L if mais else sn["media"] < L
    p2 = sn["media_aj"] > L if mais else sn["media_aj"] < L
    p3 = all((sn["h"][n] if mais else 1 - sn["h"][n]) >= PASSA_HIST for n in (5, 10, 20))
    c = sn["camp"]
    p4 = None if c is None else ((1 - c) if mais else c) <= TETO_OUTRO
    return [p1, p2, p3, p4]


def _x(sn: dict, lg_modelo: float) -> list:
    c = sn["camp"] if sn["camp"] is not None else sn["h"][20]
    return [1.0, lg_modelo, sn["media"] - sn["linha"], sn["media_aj"] - sn["linha"],
            _lg(sn["h"][5]), _lg(sn["h"][10]), _lg(sn["h"][20]), _lg(c)]


def _ajusta(X, y, cols, iters=400, lr=0.05, l2=1e-3):
    """Logistica por gradiente nas colunas `cols` (as outras ficam zeradas)."""
    w = np.zeros(X.shape[1])
    m = np.zeros(X.shape[1], bool)
    m[cols] = True
    sd = X.std(axis=0)
    sd[sd == 0] = 1.0
    Z = X / sd
    for _ in range(iters):
        p = 1 / (1 + np.exp(-(Z @ w)))
        g = Z.T @ (p - y) / len(y) + l2 * w
        w -= lr * 10 * g * m
    return w / sd


def medir() -> dict:
    d = be.carregar(incluir_c=True)
    mapas, _ = ej.rodar(d, te.carregar_elencos(), ej.W_OFICIAL, ej.KJ_OFICIAL)
    md = medidas(d)
    tab = rd.Tabela(pc.KAPPA_ROUNDS)
    corte = pd.Timestamp("2025-01-01")
    out = {}
    for L in LINHAS:
        lin = []
        for k, m in md.items():
            dt, tier, p, _y = mapas[k]
            pm = pc.p_linha_rounds(tab.dist(p), "total", "over", L, None)
            sn = sinais(m, L)
            lin.append((dt, _x(sn, _lg(pm)), int(m["y"] > L), pm, sum(1 for v in passos(sn, "over") if v),
                        sum(1 for v in passos(sn, "under") if v)))
        tr = [l for l in lin if l[0] < corte]
        te_ = [l for l in lin if l[0] >= corte]
        Xtr, ytr = np.array([l[1] for l in tr]), np.array([l[2] for l in tr], float)
        Xte, yte = np.array([l[1] for l in te_]), np.array([l[2] for l in te_], float)
        w_mod = _ajusta(Xtr, ytr, [0, 1])                     # so o modelo (recalibrado)
        w_tudo = _ajusta(Xtr, ytr, list(range(8)))            # modelo + os passos dele
        w_met = _ajusta(Xtr, ytr, [0, 2, 3, 4, 5, 6, 7])      # so os passos dele
        ll = lambda w: {i: be.ll(float(1 / (1 + math.exp(-float(Xte[i] @ w)))), int(yte[i])) for i in range(len(yte))}
        base = float(ytr.mean())
        F = {i: be.ll(base, int(yte[i])) for i in range(len(yte))}
        M, T, S = ll(w_mod), ll(w_tudo), ll(w_met)
        g1 = va.pareado(F, M)
        g2 = va.pareado(M, T)
        g3 = va.pareado(F, S)
        bate = {}
        for lado, col in (("over", 4), ("under", 5)):
            bate[lado] = {k: (round(100 * np.mean([(l[2] == 1) == (lado == "over") for l in te_ if l[col] == k]), 1),
                              sum(1 for l in te_ if l[col] == k)) for k in range(5)}
        out[L] = {"n_treino": len(tr), "n_teste": len(te_), "freq_mais": round(float(yte.mean()), 3),
                  "ll_frequencia": round(va.media(list(F.values())), 4),
                  "modelo_sobre_frequencia": [round(x, 4) for x in g1[:3]],
                  "metodo_sobre_frequencia": [round(x, 4) for x in g3[:3]],
                  "metodo_mais_modelo_sobre_modelo": [round(x, 4) for x in g2[:3]],
                  "pesos": [round(float(x), 4) for x in w_tudo], "bateu_por_passos": bate}
    return out


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    for L, r in medir().items():
        print(f"--- linha {L}")
        for k, v in r.items():
            print("  ", k, v)
    return 0


if __name__ == "__main__":
    sys.exit(main())
