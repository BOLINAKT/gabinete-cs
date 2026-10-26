# -*- coding: utf-8 -*-
"""MAPAS DO VETO de um jogo, da Liquipedia, e o placar base x "sabendo o mapa" (26/10/2026).

Pedido dele: "quando sair [o veto] voce coloca ali, e vai comparando com o seu
nivel de acertividade". O veto sai minutos antes do jogo; a Liquipedia poe o nome
do mapa em {{Map|map=...}} dentro do {{Match}} antes de haver placar.

Busca SOB DEMANDA (botao no app), nao robo: paginas de torneio em que um dos dois
times jogou nos ultimos 21 dias (no maximo 4), lidas SEM cache (liquipedia.chamar
fresco=True, mesmo ritmo de 2,1 s).

"Sabendo o mapa" = o ajuste medido em mapa_sobre_jogador.py, com os parametros
da VALIDACAO (m=40, peso=0,1). No teste 2024+ ele ganhou so +0,0003 na media, mas
nos jogos com vantagem clara de mapa o modelo base SUBESTIMA o time em ~3 pp
(3.259 mapas: dava 57,4%, ganhou 60,2%). O registro previsoes_mapas.jsonl deixa
medir isso daqui para a frente, com jogo de verdade.
"""
from __future__ import annotations

import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import base_elo as be
import extrator as ex
import liquipedia as lq

RAIZ = Path(__file__).resolve().parent
REGISTRO = RAIZ / "previsoes_mapas.jsonl"
M_WR, PESO_WR = 40, 0.1          # validacao 26/10/2026 (mapa_sobre_jogador.py)
MAX_PAGINAS, DIAS_PAGINA = 4, 21
_SEM_MAPA = {"", "tbd", "tba", "unknown", "default"}


def nomes_curtos(time_canonico: str) -> set:
    """Os nomes de modelo da Liquipedia que viram este time ("tl", "liquid" -> Team Liquid)."""
    mapa = json.loads((RAIZ / "times_canonicos.json").read_text(encoding="utf-8"))
    return {cru for cru in mapa if be.canonico(cru, mapa) == time_canonico} | {time_canonico.lower()}


def mapas_na_pagina(texto: str, curtos_a: set, curtos_b: set) -> list:
    """Pura: do {{Match}} entre os dois times MAIS RECENTE da pagina, os mapas com nome:
    [{'n', 'mapa', 'terminado', 'vencedor_a'}] (vencedor_a: 1 = time A ganhou, 0, None)."""
    achados = []
    for bloco in ex.blocos(texto, "Match"):
        c = ex.campos(bloco)
        t1, t2 = ex._time(c.get("opponent1", "")), ex._time(c.get("opponent2", ""))
        if {t1, t2} & curtos_a and {t1, t2} & curtos_b and t1 != t2:
            achados.append((ex._data(c.get("date", "")) or "", t1 in curtos_a, c))
    if not achados:
        return []
    _, a_e_time1, c = max(achados, key=lambda x: x[0])
    fora = []
    for k in sorted((k for k in c if re.fullmatch(r"map\d+", k)), key=lambda k: int(k[3:])):
        mb = next(ex.blocos(c[k], "Map"), None)
        if not mb:
            continue
        m = ex.campos(mb)
        nome = (m.get("map") or "").strip()
        if nome.lower() in _SEM_MAPA:
            continue
        terminado = str(m.get("finished", "")).lower() == "true"
        venc = None
        if terminado:
            # vencedor pelos rounds, como o extrator (o {{Map}} quase nunca traz winner)
            r1 = sum(ex._n(v) for kk, v in m.items() if re.fullmatch(r"(o\d+)?t1(t|ct)", kk))
            r2 = sum(ex._n(v) for kk, v in m.items() if re.fullmatch(r"(o\d+)?t2(t|ct)", kk))
            w = "1" if r1 > r2 else "2" if r2 > r1 else m.get("winner")
            if w in ("1", "2"):
                venc = int((w == "1") == a_e_time1)
        fora.append({"n": int(k[3:]), "mapa": nome, "terminado": terminado, "vencedor_a": venc})
    return fora


def paginas_candidatas(d: pd.DataFrame, ta: str, tb: str, hoje) -> list:
    rec = d[(d.dt >= hoje - pd.Timedelta(days=DIAS_PAGINA)) & (d.time1.isin([ta, tb]) | d.time2.isin([ta, tb]))]
    if rec.empty:
        return []
    ultima = rec.groupby("pagina").dt.max().sort_values(ascending=False)
    return list(ultima.index[:MAX_PAGINAS])


def buscar_veto(est, ta: str, tb: str, hoje=None) -> dict:
    """{'pagina', 'mapas'} do primeiro torneio candidato que tem o confronto com mapa."""
    hoje = hoje if hoje is not None else pd.Timestamp.now()
    ca, cb = nomes_curtos(ta), nomes_curtos(tb)
    lidas = []
    for pg in paginas_candidatas(est.d, ta, tb, hoje):
        lidas.append(pg)
        mapas = mapas_na_pagina(lq.wikitexto(pg, fresco=True), ca, cb)
        if mapas:
            return {"pagina": pg, "mapas": mapas, "lidas": lidas}
    return {"pagina": None, "mapas": [], "lidas": lidas}


def _logit(p):
    p = min(max(p, 1e-6), 1 - 1e-6)
    return math.log(p / (1 - p))


def p_com_mapa(est, ta: str, tb: str, mapa: str, p_base: float) -> float:
    """p do mapa ajustado pela taxa de cada time NAQUELE mapa (encolhida, m=M_WR)."""
    def wr(t):
        h = est.por_mapa.get((t, mapa), [])
        return (sum(v for _, v, _ in h) + 0.5 * M_WR) / (len(h) + M_WR)
    z = _logit(p_base) + PESO_WR * (_logit(wr(ta)) - _logit(wr(tb)))
    return 1 / (1 + math.exp(-z))


def linhas_do_veto(est, jogo: dict, veto: dict) -> list:
    """Uma linha por mapa do veto: p base, p com mapa, odd da Pinnacle desse mapa."""
    ta, tb = jogo["casou"][0][0], jogo["casou"][1][0]
    base = next((m for m in jogo["mercados"] if m["periodo"] == 1), None)
    p_base = base["lados"][0]["p_modelo"] if base else None
    if p_base is None:
        return []
    por_periodo = {m["periodo"]: m for m in jogo["mercados"]}
    fora = []
    for mp in veto["mapas"]:
        pm = p_com_mapa(est, ta, tb, mp["mapa"], p_base)
        merc = por_periodo.get(mp["n"])
        odd_a = merc["lados"][0]["odd_pinnacle"] if merc else None
        odd_b = merc["lados"][1]["odd_pinnacle"] if merc else None
        fora.append({**mp, "p_base": p_base, "p_mapa": pm, "odd_a": odd_a, "odd_b": odd_b,
                     "vant_base_a": (p_base * odd_a - 1) * 100 if odd_a else None,
                     "vant_mapa_a": (pm * odd_a - 1) * 100 if odd_a else None,
                     "vant_base_b": ((1 - p_base) * odd_b - 1) * 100 if odd_b else None,
                     "vant_mapa_b": ((1 - pm) * odd_b - 1) * 100 if odd_b else None})
    return fora


def registrar(jogo: dict, linhas: list, pagina: str) -> int:
    """Grava cada mapa UMA vez (antes de terminar): a previsao fica congelada para o placar."""
    vistos = set()
    if REGISTRO.exists():
        for t in REGISTRO.read_text(encoding="utf-8").splitlines():
            if t.strip():
                r = json.loads(t)
                vistos.add((r["jogo"], r["n"]))
    novos = 0
    agora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with REGISTRO.open("a", encoding="utf-8") as f:
        for l in linhas:
            if (jogo["id"], l["n"]) in vistos or l["terminado"]:
                continue
            f.write(json.dumps({"registrado_em": agora, "jogo": jogo["id"], "inicio_utc": jogo["inicio_utc"],
                                "time_a": jogo["casou"][0][0], "time_b": jogo["casou"][1][0], "pagina": pagina,
                                "n": l["n"], "mapa": l["mapa"], "p_base": round(l["p_base"], 4),
                                "p_mapa": round(l["p_mapa"], 4), "odd_a": l["odd_a"], "odd_b": l["odd_b"]},
                               ensure_ascii=False) + "\n")
            novos += 1
    return novos


RESULTADOS = RAIZ / "resultados_mapas.jsonl"


def registrar_resultados(jogo: dict, linhas: list) -> int:
    """Mapa TERMINADO visto na pagina do veto: grava quem ganhou (time A = casa)."""
    vistos = set()
    if RESULTADOS.exists():
        vistos = {(r["jogo"], r["n"]) for r in map(json.loads, filter(str.strip,
                  RESULTADOS.read_text(encoding="utf-8").splitlines()))}
    novos = 0
    with RESULTADOS.open("a", encoding="utf-8") as f:
        for l in linhas:
            if l["terminado"] and l["vencedor_a"] is not None and (jogo["id"], l["n"]) not in vistos:
                f.write(json.dumps({"jogo": jogo["id"], "n": l["n"], "mapa": l["mapa"],
                                    "venceu_a": l["vencedor_a"]}, ensure_ascii=False) + "\n")
                novos += 1
    return novos


def placar(d: pd.DataFrame) -> dict:
    """Junta o registro com os resultados (pagina do veto ou mapas_cs.csv): base x com mapa."""
    if not REGISTRO.exists():
        return {"n": 0, "pendentes": 0, "linhas": []}
    regs = [json.loads(t) for t in REGISTRO.read_text(encoding="utf-8").splitlines() if t.strip()]
    res = {}
    if RESULTADOS.exists():
        for t in RESULTADOS.read_text(encoding="utf-8").splitlines():
            if t.strip():
                r = json.loads(t)
                res[(r["jogo"], r["n"])] = r["venceu_a"]
    linhas = []
    for r in regs:
        if (r["jogo"], r["n"]) in res:
            y = res[(r["jogo"], r["n"])]
            linhas.append({**r, "venceu_a": y, "ll_base": be.ll(r["p_base"], y), "ll_mapa": be.ll(r["p_mapa"], y)})
            continue
        ini = pd.Timestamp(r["inicio_utc"]).tz_localize(None) if r.get("inicio_utc") else None
        if ini is None:
            continue
        janela = d[(d.dt >= ini - pd.Timedelta(hours=12)) & (d.dt <= ini + pd.Timedelta(hours=36))
                   & (d.mapa_n == r["n"]) & (d.mapa == r["mapa"])]
        ab = janela[(janela.time1 == r["time_a"]) & (janela.time2 == r["time_b"])]
        ba = janela[(janela.time1 == r["time_b"]) & (janela.time2 == r["time_a"])]
        if not ab.empty:
            y = int(ab.iloc[0].vencedor == 1)
        elif not ba.empty:
            y = int(ba.iloc[0].vencedor == 2)
        else:
            continue
        linhas.append({**r, "venceu_a": y, "ll_base": be.ll(r["p_base"], y), "ll_mapa": be.ll(r["p_mapa"], y)})
    if not linhas:
        return {"n": 0, "pendentes": len(regs), "linhas": []}
    n = len(linhas)
    return {"n": n, "pendentes": len(regs) - n, "linhas": linhas,
            "ll_base": sum(l["ll_base"] for l in linhas) / n, "ll_mapa": sum(l["ll_mapa"] for l in linhas) / n,
            "acerto_base": sum((l["p_base"] >= 0.5) == bool(l["venceu_a"]) for l in linhas) / n,
            "acerto_mapa": sum((l["p_mapa"] >= 0.5) == bool(l["venceu_a"]) for l in linhas) / n}
