# -*- coding: utf-8 -*-
"""LAN x ONLINE, sobre o modelo de margem (26/10/2026).

O tipo vem do infobox do torneio (|type=Offline/Online), lido do CACHE da
Liquipedia (nenhuma chamada nova); subpagina herda o tipo da pagina-mae.
Ideia: jogo de LAN informa mais sobre a forca real (sem ping, sem casa, palco)
-> K proprio para LAN e para online, escolhido na VALIDACAO; TESTE 2024+ uma vez.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

import base_elo as be
import variantes as va

K, A = 72, 0.3
VAL = (pd.Timestamp("2021-01-01"), be.INICIO_TESTE)
CACHE = Path(__file__).resolve().parent / "cache" / "liquipedia"


def tipos() -> dict:
    t = {}
    for f in CACHE.glob("*.json"):
        try:
            pags = json.loads(f.read_text(encoding="utf-8"))["query"]["pages"]
        except (KeyError, ValueError, TypeError):
            continue
        for p in pags:
            try:
                txt = p["revisions"][0]["slots"]["main"]["content"]
            except (KeyError, IndexError):
                continue
            m = re.search(r"\|\s*type\s*=\s*(\w+)", txt)
            if m:
                t[p["title"]] = "lan" if m.group(1).lower() == "offline" else "online"
    return t


def tipo_de(pag, t):
    partes = str(pag).split("/")
    for i in range(len(partes), 0, -1):
        k = "/".join(partes[:i])
        if k in t:
            return t[k]
    return None


def rodar(d, k_lan=K, k_on=K):
    r = defaultdict(lambda: 1500.0)
    fora = {}
    for x in d.itertuples(index=False):
        a, b = x.time1, x.time2
        p = 1 / (1 + 10 ** (-(r[a] - r[b]) / 400))
        y = 1 if x.vencedor == 1 else 0
        tot = x.rounds1 + x.rounds2
        s = A * y + (1 - A) * (x.rounds1 / tot if tot > 0 else y)
        fora[(x.pagina, x.data, a, b, x.mapa_n)] = (x.dt, x.tier, p, y)
        k = k_lan if x.tipo == "lan" else k_on
        r[a] += k * (s - p)
        r[b] -= k * (s - p)
    return fora


def perdas(f, desde, ate=None):
    return {i: be.ll(p, y) for i, (dt, t, p, y) in f.items()
            if dt >= desde and (ate is None or dt < ate) and t in ("S", "A")}


def main() -> int:
    d = be.carregar()
    t = tipos()
    d["tipo"] = [tipo_de(p, t) for p in d["pagina"]]
    print("mapas por tipo:", Counter(d["tipo"].fillna("?")))
    bt = perdas(rodar(d), be.INICIO_TESTE)
    grade = [(kl, ko) for kl in (72, 96, 128) for ko in (40, 56, 72)]
    kl, ko = min(grade, key=lambda g: va.media(list(perdas(rodar(d, *g), *VAL).values())))
    v = perdas(rodar(d, kl, ko), be.INICIO_TESTE)
    g, lo, hi, p, n = va.pareado(bt, v)
    ok = g > 0.002 and p < 0.05 and lo > 0
    print(f"K lan={kl} online={ko}: mapa S/A {va.media(list(bt.values())):.4f} -> {va.media(list(v.values())):.4f} "
          f"ganho {g:+.4f} IC95 [{lo:+.4f}, {hi:+.4f}] p={p:.3f} n={n} {'PASSA' if ok else 'nao passa'}")
    return 0



def rodar_desvio(d, k_d=0.0):
    """Global + desvio do time no TIPO (lan/online), aprendido com a margem."""
    r, rd = defaultdict(lambda: 1500.0), defaultdict(float)
    fora = {}
    for x in d.itertuples(index=False):
        a, b, tp = x.time1, x.time2, x.tipo
        p = 1 / (1 + 10 ** (-(r[a] - r[b] + rd[(a, tp)] - rd[(b, tp)]) / 400))
        y = 1 if x.vencedor == 1 else 0
        tot = x.rounds1 + x.rounds2
        s = A * y + (1 - A) * (x.rounds1 / tot if tot > 0 else y)
        fora[(x.pagina, x.data, a, b, x.mapa_n)] = (x.dt, x.tier, p, y)
        r[a] += K * (s - p); r[b] -= K * (s - p)
        if k_d:
            rd[(a, tp)] += k_d * (s - p); rd[(b, tp)] -= k_d * (s - p)
    return fora


def main_desvio() -> int:
    d = be.carregar()
    t = tipos()
    d["tipo"] = [tipo_de(p, t) for p in d["pagina"]]
    bt = perdas(rodar_desvio(d), be.INICIO_TESTE)
    kd = min((5, 10, 20, 30), key=lambda g: va.media(list(perdas(rodar_desvio(d, g), *VAL).values())))
    v = perdas(rodar_desvio(d, kd), be.INICIO_TESTE)
    g, lo, hi, p, n = va.pareado(bt, v)
    ok = g > 0.002 and p < 0.05 and lo > 0
    print(f"desvio LAN/online K_d={kd}: {va.media(list(bt.values())):.4f} -> {va.media(list(v.values())):.4f} "
          f"ganho {g:+.4f} IC95 [{lo:+.4f}, {hi:+.4f}] p={p:.3f} {'PASSA' if ok else 'nao passa'}")
    return 0


if __name__ == "__main__":
    sys.exit(main_desvio() if "--desvio" in sys.argv else main())
