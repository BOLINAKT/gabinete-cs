"""AFINAR O CS COMO O LOL (25/11/2026). Ele: "quero que Dota e CS virem um LoL, bem afinado".
O motor do CS (elo_jogador.rodar) tem K=24 fixo, KJ=32 escolhido numa grade grossa e NAO usa a margem: 13-2 conta
igual a 16-14. Aqui, o mesmo motor (forca = media das notas do elenco, w=0) com as alavancas que afinaram o LoL:
  - K do time e KJ do jogador re-tunados;
  - MARGEM DE ROUNDS como resultado fracionario (o metodo do LoL, tools/eval_whr_mov.py): y~ = folga + y(1-2folga)
    + lam * (saldo - E[saldo | diferenca de forca]) / desvio, com E[] = a*tanh(b*dif) + c ajustado SO antes da
    validacao (<2021);
  - K maior para jogador/time novo (kn: K * (1 + kn) nos primeiros 20 mapas).
PROTOCOLO (o da casa): escolha na VALIDACAO (mapas S/A/B de 2021-2023), teste UMA vez em 2024+ (S/A/B) e
2026 a parte; ganho pareado com IC95 (bootstrap); regua: ganho > 0,002 e IC > 0. Mesma base do app (com tier C).
Uso: py -3.13 afinar_cs_elo.py
"""
import math
import random
import sys
from collections import defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\Gabinetes\GabineteCS")
sys.stdout.reconfigure(encoding="utf-8")
import os  # noqa: E402
os.chdir(r"C:\Gabinetes\GabineteCS")
import base_elo as be  # noqa: E402
import troca_elenco as te  # noqa: E402

VAL = (pd.Timestamp("2021-01-01"), pd.Timestamp("2024-01-01"))
TESTE = pd.Timestamp("2024-01-01")
ANO = pd.Timestamp("2026-01-01")
TIERS = ("S", "A", "B")

d = be.carregar(incluir_c=True)
el = te.carregar_elencos()
LINHAS = []
for x in d.itertuples(index=False):
    ea, eb = te.elenco(el, x.time1, x.dt), te.elenco(el, x.time2, x.dt)
    ea = tuple(ea) if ea is not None and 3 <= len(ea) <= 7 else None
    eb = tuple(eb) if eb is not None and 3 <= len(eb) <= 7 else None
    LINHAS.append((x.time1, x.time2, ea, eb, 1 if x.vencedor == 1 else 0, float(x.rounds1 - x.rounds2), x.dt, x.tier,
                   (x.pagina, x.data, x.time1, x.time2, x.mapa_n)))
print(f"{len(LINHAS)} mapas", flush=True)


def rodar(K=24.0, KJ=32.0, lam=0.0, folga=0.0, kn=0.0, fit=None, coletar=False):
    r, pr = defaultdict(lambda: 1500.0), {}
    n_t, n_j = defaultdict(int), defaultdict(int)
    prev, xs, ys = {}, [], []
    a_m, b_m, c_m, s_m = fit or (0.0, 0.0, 0.0, 1.0)
    for a, b, ea, eb, y, rd, dt, tier, ch in LINHAS:
        f = {}
        for t, e in ((a, ea), (b, eb)):
            if e is None:
                f[t] = r[t]
            else:
                for j in e:
                    pr.setdefault(j, r[t])
                f[t] = sum(pr[j] for j in e) / len(e)
        dif = f[a] - f[b]
        p = 1 / (1 + 10 ** (-dif / 400))
        prev[ch] = (dt, tier, p, y)
        if coletar and dt < VAL[0]:
            xs.append(dif)
            ys.append(rd)
        yf = folga + y * (1 - 2 * folga)
        if lam:
            yf = min(max(yf + lam * (rd - (a_m * math.tanh(b_m * dif) + c_m)) / s_m, 0.0), 1.0)
        for t, e, sinal in ((a, ea, 1), (b, eb, -1)):
            kt = K * (1 + kn) if n_t[t] < 20 else K
            r[t] += sinal * kt * (yf - p)
            n_t[t] += 1
            if e is not None:
                for j in e:
                    kj = KJ * (1 + kn) if n_j[j] < 20 else KJ
                    pr[j] += sinal * kj * (yf - p)
                    n_j[j] += 1
    if coletar:
        return prev, np.array(xs), np.array(ys)
    return prev


def ll(p, y):
    p = min(max(p, 1e-6), 1 - 1e-6)
    return -math.log(p if y else 1 - p)


def perdas(prev, ini, fim=None):
    return {k: ll(p, y) for k, (dt, t, p, y) in prev.items() if dt >= ini and (fim is None or dt < fim) and t in TIERS}


def val(prev):
    v = perdas(prev, *VAL)
    return sum(v.values()) / len(v)


def pareado(b, c):
    ids = [i for i in b if i in c]
    dd = np.array([b[i] - c[i] for i in ids])
    rng = np.random.default_rng(7)
    bt = dd[rng.integers(0, len(dd), (2000, len(dd)))].mean(axis=1)
    return dd.mean(), np.percentile(bt, 2.5), np.percentile(bt, 97.5), len(dd)


# E[saldo | dif], so com mapas ANTES da validacao
_, X, Y = rodar(coletar=True)
melhor = None
for bb in (0.001, 0.002, 0.003, 0.005, 0.008, 0.012):
    T = np.tanh(bb * X)
    A = np.column_stack([T, np.ones_like(T)])
    coef, *_ = np.linalg.lstsq(A, Y, rcond=None)
    res = Y - A @ coef
    if melhor is None or res @ res < melhor[0]:
        melhor = (float(res @ res), (float(coef[0]), bb, float(coef[1]), float(res.std())))
FIT = melhor[1]
print(f"E[saldo|dif] (<2021, n={len(X)}): a={FIT[0]:.2f} b={FIT[1]} c={FIT[2]:.2f} desvio={FIT[3]:.2f}", flush=True)

base_cfg = dict(K=24.0, KJ=32.0)
base = rodar(**base_cfg)
print(f"producao (K=24, KJ=32): validacao {val(base):.4f}", flush=True)


def tunar(cfg, nome, valores):
    best = (val(rodar(**cfg, fit=FIT)), cfg[nome] if nome in cfg else 0.0)
    for v in valores:
        c = {**cfg, nome: v}
        s = val(rodar(**c, fit=FIT))
        print(f"   {nome}={v:<6} -> {s:.4f}", flush=True)
        if s < best[0]:
            best = (s, v)
    print(f"  {nome}: {best[1]} ({best[0]:.4f})", flush=True)
    return {**cfg, nome: best[1]}


cfg = dict(base_cfg)
FIXO = os.environ.get("CS_CFG")   # reavaliar uma escolha ja feita, sem re-tunar (ex.: '{"K":32,...}')
for rodada in range(0 if FIXO else 2):     # coordenadas, duas voltas (o LoL re-tuna o drift DEPOIS da margem)
    print(f"-- volta {rodada + 1}", flush=True)
    cfg = tunar(cfg, "lam", [0.1, 0.2, 0.35, 0.5, 0.75, 1.0])
    cfg = tunar(cfg, "folga", [0.0, 0.1, 0.15, 0.25])
    cfg = tunar(cfg, "KJ", [16.0, 24.0, 32.0, 40.0, 48.0, 64.0])
    cfg = tunar(cfg, "K", [12.0, 16.0, 24.0, 32.0, 48.0])
    cfg = tunar(cfg, "kn", [0.0, 0.5, 1.0, 2.0])
if FIXO:
    import json
    cfg = {**cfg, **json.loads(FIXO)}
print(f"\nESCOLHIDO na validacao: {cfg}", flush=True)
cand = rodar(**cfg, fit=FIT)
for nome, ini, fim in (("TESTE 2024+", TESTE, None), ("2026", ANO, None)):
    b, c = perdas(base, ini, fim), perdas(cand, ini, fim)
    g, lo, hi, n = pareado(b, c)
    print(f"{nome}: n={n} producao {np.mean(list(b.values())):.4f} -> {np.mean(list(c.values())):.4f} "
          f"ganho {g:+.4f} IC95 [{lo:+.4f}; {hi:+.4f}] {'PASSA' if g > 0.002 and lo > 0 else 'nao passa'}", flush=True)
for tier in TIERS:
    b = {k: v for k, v in perdas(base, TESTE).items() if base[k][1] == tier}
    c = {k: v for k, v in perdas(cand, TESTE).items() if k in b}
    g, lo, hi, n = pareado(b, c)
    print(f"  tier {tier}: n={n} ganho {g:+.4f} [{lo:+.4f}; {hi:+.4f}]")
anos = defaultdict(lambda: [0.0, 0])
pb, pc_ = perdas(base, TESTE), perdas(cand, TESTE)
for k in pb:
    m = f"{base[k][0].year}-{(base[k][0].month - 1) // 6 + 1}"
    anos[m][0] += pb[k] - pc_[k]
    anos[m][1] += 1
print("  por semestre: " + " | ".join(f"{m} {s / n:+.4f} (n={n})" for m, (s, n) in sorted(anos.items()) if n))

# QUAL ALAVANCA FAZ O GANHO (so leitura: a escolha ja foi feita na validacao)
for nome, tira in (("sem margem de rounds", {"lam": 0.0, "folga": 0.0}), ("sem K de novato", {"kn": 0.0}),
                   ("K do time 24", {"K": 24.0})):
    c2 = rodar(**{**cfg, **tira}, fit=FIT)
    g, lo, hi, n = pareado(perdas(c2, TESTE), perdas(cand, TESTE))
    print(f"  tirando {nome}: perde {g:+.4f} [{lo:+.4f}; {hi:+.4f}] no teste 2024+")
