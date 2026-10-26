# -*- coding: utf-8 -*-
"""MODELO DE BASE DO CS: Elo por mapa, medido de forma honesta (26/10/2026).

O primeiro numero do modelo de CS. Nao e o modelo final: e a BASE que todo
modelo seguinte precisa bater, e a primeira comparacao com a regua externa
(CS2-Predictor: logloss 0,645 na SERIE, tier-1, teste nos 20% mais recentes).

COMO MEDE (prequencial): os mapas em ordem de data; cada um e PREVISTO com os
ratings de antes e so depois entra no rating. Nada do futuro vaza.

  - rating por time, Elo classico: p = 1 / (1 + 10^(-(Ra-Rb)/400));
  - K escolhido nos anos 2020-2023 (validacao) entre poucos valores; o TESTE e
    2024-2026, nunca usado para escolher nada;
  - serie: a probabilidade de vencer a serie sai da do mapa (mapas
    independentes, BO pelo numero de mapas que o vencedor precisou: 1, 2 ou 3);
  - regua externa: logloss da SERIE, so S e A-Tier (o mais perto do "tier-1"
    do CS2-Predictor), no periodo de teste.
Fora: mapas sem data, W.O. ("Default") e mapa "Unknown".
Fonte dos dados: Liquipedia (CC-BY-SA 3.0).
"""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent
INICIO_TESTE = pd.Timestamp("2024-01-01")
KS = (16, 24, 32, 40, 48)


def canonico(nome: str, mapa: dict) -> str:
    """Nome curto -> pagina do time (resolver_times.py). Fica o nome cru quando a
    fusao seria errada: sem organizacao ("Orgless"), elenco feminino, ou sub-elenco
    de selecao ("france.3dmax" -> "Team France")."""
    c = mapa.get(nome)
    if not c or c == "Orgless" or "female" in nome or nome.endswith(".fe"):
        return nome
    if c.startswith("Team ") and "." in nome:
        return nome
    return c


def carregar(incluir_c: bool = False) -> pd.DataFrame:
    """Mapas para o modelo. Tier C (coleta aos poucos desde 26/10/2026) fica FORA
    por padrao: so entra no oficial se passar na regua (teste com/sem)."""
    d = pd.read_csv(RAIZ / "mapas_cs.csv")
    if not incluir_c:
        d = d[d["tier"] != "C"]
    arq = RAIZ / "times_canonicos.json"
    if arq.exists():
        mapa = json.loads(arq.read_text(encoding="utf-8"))
        for col in ("time1", "time2"):
            d[col] = [canonico(str(n), mapa) for n in d[col]]
    d["dt"] = pd.to_datetime(d["data"], errors="coerce")
    d = d[d["dt"].notna() & ~d["mapa"].isin(["Default", "Unknown"])].copy()
    return d.sort_values(["dt", "pagina", "mapa_n"]).reset_index(drop=True)


def ll(p: float, y: int) -> float:
    p = min(max(p, 1e-6), 1 - 1e-6)
    return -math.log(p if y else 1 - p)


def p_serie(p: float, precisa: int) -> float:
    """Chance de ganhar 'precisa' mapas antes do adversario (mapas independentes)."""
    q, tot = 1 - p, 0.0
    for perdidos in range(precisa):
        tot += math.comb(precisa - 1 + perdidos, perdidos) * p ** precisa * q ** perdidos
    return tot


def rodar(d: pd.DataFrame, k: float):
    """Prequencial. Devolve (linhas por mapa, previsoes por serie)."""
    r = defaultdict(lambda: 1500.0)
    mapas, series = [], {}
    for x in d.itertuples(index=False):
        a, b = x.time1, x.time2
        p = 1 / (1 + 10 ** (-(r[a] - r[b]) / 400))
        y = 1 if x.vencedor == 1 else 0
        mapas.append((x.dt, x.tier, p, y))
        chave = (x.pagina, x.data, a, b)
        s = series.setdefault(chave, {"dt": x.dt, "tier": x.tier, "p1": p, "v1": 0, "v2": 0})
        s["v1" if y else "v2"] += 1
        delta = k * (y - p)
        r[a] += delta
        r[b] -= delta
    return mapas, list(series.values())


def notas(mapas, series, desde, ate=None, tiers=("S", "A", "B")):
    m = [(p, y) for dt, t, p, y in mapas if dt >= desde and (ate is None or dt < ate) and t in tiers]
    s = []
    for x in series:
        if x["dt"] < desde or (ate is not None and x["dt"] >= ate) or x["tier"] not in tiers:
            continue
        precisa = max(x["v1"], x["v2"])
        if precisa < 1 or x["v1"] == x["v2"]:
            continue
        s.append((p_serie(x["p1"], precisa), 1 if x["v1"] > x["v2"] else 0))
    def resumo(v):
        if not v:
            return None
        return {"n": len(v), "logloss": round(sum(ll(p, y) for p, y in v) / len(v), 4),
                "acerto": round(sum((p > 0.5) == bool(y) for p, y in v) / len(v), 3)}
    return {"mapa": resumo(m), "serie": resumo(s)}


def main() -> int:
    d = carregar()
    print(f"{len(d)} mapas de {d.dt.min():%d/%m/%Y} a {d.dt.max():%d/%m/%Y}")
    melhor = None
    for k in KS:
        mapas, series = rodar(d, k)
        v = notas(mapas, series, pd.Timestamp("2021-01-01"), INICIO_TESTE)
        print(f"  K={k:>3}  validacao 2021-2023: mapa {v['mapa']['logloss']}  serie {v['serie']['logloss']}")
        if melhor is None or v["mapa"]["logloss"] < melhor[1]:
            melhor = (k, v["mapa"]["logloss"])
    k = melhor[0]
    mapas, series = rodar(d, k)
    print(f"\nK escolhido na validacao: {k}. TESTE 2024 em diante (nunca usado para escolher):")
    for nome, tiers in (("todos (S/A/B)", ("S", "A", "B")), ("S e A-Tier", ("S", "A")), ("S-Tier", ("S",))):
        t = notas(mapas, series, INICIO_TESTE, tiers=tiers)
        print(f"  {nome:14s} mapa: {t['mapa']}  |  serie: {t['serie']}")
    t = notas(mapas, series, pd.Timestamp("2025-06-01"), tiers=("S", "A"))
    print(f"  S/A desde 06/2025 (~os 20% mais recentes) serie: {t['serie']}   <- comparar com 0,645")
    return 0


if __name__ == "__main__":
    sys.exit(main())
