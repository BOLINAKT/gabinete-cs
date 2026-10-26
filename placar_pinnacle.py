# -*- coding: utf-8 -*-
"""PLACAR modelo x Pinnacle no FECHAMENTO (26/10/2026) -- a regua de verdade.

Para cada jogo/mercado gravado por registrar_previsoes.py: a ULTIMA leitura antes
do inicio (o "fechamento" que temos, de 3 em 3 h) e o resultado nos mapas
coletados (robo de dados, inclui tier C so para achar o resultado). Compara:
  - logloss do modelo x logloss da Pinnacle sem margem (quem preve melhor);
  - apostando 1 unidade onde o modelo via vantagem entre 1% e 20%: lucro e ROI.
Com poucos jogos e sorte; a conta mostra o intervalo de confianca.
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import pandas as pd

import base_elo as be

RAIZ = Path(__file__).resolve().parent
PREV = RAIZ / "previsoes_cs2.jsonl"


def fechamento(regs: list) -> list:
    """Pura: por (jogo, mercado), a ultima previsao lida ANTES do inicio."""
    ult = {}
    for r in regs:
        if not r.get("inicio_utc") or r["lido_em"] >= r["inicio_utc"].replace("Z", "+00:00"):
            continue
        k = (r["jogo"], r["mercado"])
        if k not in ult or r["lido_em"] > ult[k]["lido_em"]:
            ult[k] = r
    return list(ult.values())


def resultado(d: pd.DataFrame, r: dict):
    """1 se o time da casa venceu (serie ou mapa n), 0 se perdeu, None se nao achou."""
    ini = pd.Timestamp(r["inicio_utc"]).tz_localize(None)
    j = d[(d.dt >= ini - pd.Timedelta(hours=12)) & (d.dt <= ini + pd.Timedelta(hours=18))]
    a, b = r["time_casa"], r["time_fora"]
    ab = j[(j.time1 == a) & (j.time2 == b)]
    ba = j[(j.time1 == b) & (j.time2 == a)]
    if ab.empty and ba.empty:
        return None
    s, casa_e_1 = (ab, True) if not ab.empty else (ba, False)
    s = s[s.pagina == s.pagina.iloc[0]]
    if r["periodo"] == 0:
        v1 = int((s.vencedor == 1).sum())
        v2 = len(s) - v1
        if v1 == v2:
            return None
        return int((v1 > v2) == casa_e_1)
    m = s[s.mapa_n == r["periodo"]]
    if m.empty:
        return None
    return int((m.vencedor.iloc[0] == 1) == casa_e_1)


def placar(d: pd.DataFrame, regs: list) -> dict:
    linhas = []
    for r in fechamento(regs):
        y = resultado(d, r)
        if y is None or r.get("p_pinnacle_casa") is None:
            continue
        pm, pp = r["p_modelo_casa"], r["p_pinnacle_casa"]
        lucro = 0.0
        apostou = None
        for lado, p, odd, ganhou in (("casa", pm, r["odd_casa"], y == 1), ("fora", 1 - pm, r["odd_fora"], y == 0)):
            v = (p * odd - 1) * 100 if odd else None
            if v is not None and 1 <= v <= 20:
                apostou = lado
                lucro = (odd - 1) if ganhou else -1.0
        linhas.append({**r, "venceu_casa": y, "ll_modelo": be.ll(pm, y), "ll_pinnacle": be.ll(pp, y),
                       "apostou": apostou, "lucro": lucro})
    if not linhas:
        return {"n": 0, "linhas": []}
    n = len(linhas)
    dif = [l["ll_pinnacle"] - l["ll_modelo"] for l in linhas]   # > 0 = modelo melhor
    rnd = random.Random(7)
    boots = sorted(sum(rnd.choice(dif) for _ in dif) / n for _ in range(2000))
    ap = [l for l in linhas if l["apostou"]]
    return {"n": n, "linhas": linhas,
            "ll_modelo": sum(l["ll_modelo"] for l in linhas) / n,
            "ll_pinnacle": sum(l["ll_pinnacle"] for l in linhas) / n,
            "ic_dif": (boots[50], boots[1949]),
            "apostas": len(ap), "lucro": sum(l["lucro"] for l in ap),
            "roi": (sum(l["lucro"] for l in ap) / len(ap)) if ap else None}


def carregar_registros() -> list:
    if not PREV.exists():
        return []
    return [json.loads(t) for t in PREV.read_text(encoding="utf-8").splitlines() if t.strip()]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    pl = placar(be.carregar(incluir_c=True), carregar_registros())
    if not pl["n"]:
        print("Ainda sem jogo com previsao gravada E resultado coletado.")
        return 0
    lo, hi = pl["ic_dif"]
    print(f"{pl['n']} mercados com resultado | logloss modelo {pl['ll_modelo']:.4f} x Pinnacle {pl['ll_pinnacle']:.4f} "
          f"(modelo - Pinnacle, IC95 da vantagem do modelo [{lo:+.4f}, {hi:+.4f}])")
    if pl["apostas"]:
        print(f"apostas com vantagem 1-20%: {pl['apostas']} | lucro {pl['lucro']:+.2f} u | ROI {100 * pl['roi']:+.1f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
