# -*- coding: utf-8 -*-
"""Do texto da wiki da Liquipedia para uma linha por MAPA jogado (25/10/2026).

Formato medido na pagina "Intel Extreme Masters/2025/Cologne":
  {{Match
    |opponent1={{TeamOpponent|faze}}|opponent2={{TeamOpponent|big}}
    |date=July 23, 2025 - 17:35 {{Abbr/CEST}} |finished=true
    |map1={{Map|map=Inferno|finished=true|t1firstside=ct|t1t=5|t1ct=8|t2t=4|t2ct=3|...}}
    |map3={{Map|map=Dust II|finished=skip}}      <- mapa nao jogado
    |hltv=2383749
  }}
Rounds do time 1 no mapa = t1t + t1ct + as prorrogacoes (o1t1t, o1t1ct, o2t1t...).
Fonte dos dados: Liquipedia (CC-BY-SA 3.0) -- citar ao publicar qualquer coisa.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Dict, Iterator, List, Optional


def blocos(texto: str, nome: str) -> Iterator[str]:
    """Cada {{nome ...}} do texto, com as chaves aninhadas inteiras."""
    alvo = "{{" + nome
    i = 0
    while True:
        i = texto.find(alvo, i)
        if i < 0:
            return
        depois = texto[i + len(alvo): i + len(alvo) + 1]
        if depois and (depois.isalnum() or depois == "_"):   # {{MatchList, {{Matches...
            i += len(alvo)
            continue
        nivel, j = 0, i
        while j < len(texto) - 1:
            if texto[j:j + 2] == "{{":
                nivel += 1
                j += 2
                continue
            if texto[j:j + 2] == "}}":
                nivel -= 1
                j += 2
                if nivel == 0:
                    break
                continue
            j += 1
        yield texto[i:j]
        i = j


def campos(bloco: str) -> Dict[str, str]:
    """Os |chave=valor do NIVEL de cima do bloco (ignora o que esta dentro de {{ }} aninhado)."""
    corpo = bloco[2:-2]
    partes, nivel, atual = [], 0, []
    k = 0
    while k < len(corpo):
        if corpo[k:k + 2] == "{{":
            nivel += 1
            atual.append("{{")
            k += 2
            continue
        if corpo[k:k + 2] == "}}":
            nivel -= 1
            atual.append("}}")
            k += 2
            continue
        c = corpo[k]
        if c == "|" and nivel == 0:
            partes.append("".join(atual))
            atual = []
        else:
            atual.append(c)
        k += 1
    partes.append("".join(atual))
    out = {}
    for p in partes[1:]:
        if "=" in p:
            ch, v = p.split("=", 1)
            out[ch.strip()] = v.strip()
    return out


def _time(v: str) -> str:
    m = re.search(r"\{\{\s*TeamOpponent\s*\|\s*([^|}]+)", v or "")
    return m.group(1).strip().lower() if m else ""


def _data(v: str) -> Optional[str]:
    s = re.sub(r"\{\{.*?\}\}", "", v or "").strip()
    for fmt in ("%B %d, %Y - %H:%M", "%B %d, %Y", "%Y-%m-%d - %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d %H:%M")
        except ValueError:
            continue
    return None


def _n(v: Optional[str]) -> int:
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return 0


def mapas_da_pagina(texto: str, *, pagina: str, tier: str) -> List[dict]:
    linhas = []
    for bloco in blocos(texto, "Match"):
        c = campos(bloco)
        t1, t2 = _time(c.get("opponent1", "")), _time(c.get("opponent2", ""))
        if not (t1 and t2):
            continue
        data = _data(c.get("date", ""))
        for k in sorted((k for k in c if re.fullmatch(r"map\d+", k)), key=lambda k: int(k[3:])):
            mb = next(blocos(c[k], "Map"), None)
            if not mb:
                continue
            m = campos(mb)
            if str(m.get("finished", "")).lower() != "true":
                continue
            # PRORROGACAO: o1t1t, o1t1ct, o2t1t... uma por prorrogacao (medido
            # na mesma pagina, 25/10/2026). Sem somar, 15x15 vira "empate".
            ot1 = sum(_n(v) for kk, v in m.items() if re.fullmatch(r"o\d+t1(t|ct)", kk))
            ot2 = sum(_n(v) for kk, v in m.items() if re.fullmatch(r"o\d+t2(t|ct)", kk))
            r1 = _n(m.get("t1t")) + _n(m.get("t1ct")) + ot1
            r2 = _n(m.get("t2t")) + _n(m.get("t2ct")) + ot2
            if r1 == r2:                     # sem placar de rounds: nao sabemos quem venceu
                w = m.get("winner")
                if w not in ("1", "2"):
                    continue
                vencedor = int(w)
            else:
                vencedor = 1 if r1 > r2 else 2
            linhas.append({
                "pagina": pagina, "tier": tier, "data": data, "time1": t1, "time2": t2,
                "mapa_n": int(k[3:]), "mapa": m.get("map", ""), "rounds1": r1, "rounds2": r2,
                "lado_inicial1": m.get("t1firstside", ""), "vencedor": vencedor,
                "prorrogacoes": len({kk[:2] for kk in m if re.fullmatch(r"o\d+t1t", kk)}),
                "hltv": c.get("hltv", ""),
            })
    return linhas


# ---- AGENDA (27/10/2026): os PROXIMOS jogos, com hora em UTC ---------------------
# Pedido dele: "pegar os jogos pela liquipedia e depois so adicionar as odds".
# A Liquipedia escreve a hora no fuso do torneio ("13:00 {{Abbr/EET}}"); o _data
# acima ignora o fuso (serve para ordenar mapas), a agenda precisa de UTC.
FUSOS_H = {"UTC": 0, "GMT": 0, "WET": 0, "WEST": 1, "BST": 1, "CET": 1, "CEST": 2, "EET": 2, "EEST": 3,
           "SAST": 2, "MSK": 3, "AST": 3, "GST": 4, "ALMT": 5, "UZT": 5, "IST": 5.5, "ICT": 7,
           "SGT": 8, "HKT": 8, "MYT": 8, "WITA": 8, "ULAT": 8, "KST": 9, "AEST": 10, "AEDT": 11,
           "BRT": -3, "ART": -3, "EDT": -4, "EST": -5, "CDT": -5, "PET": -5, "PDT": -7, "PST": -8}
_ASIA = ("asia", "china", "chinese", "cn", "east", "oceania", "mongolia", "japan", "korea")


def data_utc(v: str, pagina: str = "") -> Optional[str]:
    """'October 28, 2026 - 13:00 {{Abbr/EET}}' -> '2026-10-28T11:00:00Z'. Sem fuso: UTC.
    CST/CT e ambiguo (China +8 x EUA -6): decide pelo nome da pagina."""
    s = _data(v)
    if not s:
        return None
    m = re.search(r"Abbr/([A-Za-z]+)", v or "")
    ab = (m.group(1).upper() if m else "UTC")
    if ab in ("CST", "CT"):
        h = 8 if any(k in str(pagina).lower() for k in _ASIA) else -6
    else:
        h = FUSOS_H.get(ab, 0)
    dt = datetime.strptime(s, "%Y-%m-%d %H:%M") - timedelta(hours=h)
    return dt.strftime("%Y-%m-%dT%H:%M:00Z")


def proximos_da_pagina(texto: str, *, pagina: str, tier: str) -> List[dict]:
    """Os {{Match}} AINDA NAO decididos com os dois times definidos."""
    fora = []
    for bloco in blocos(texto, "Match"):
        c = campos(bloco)
        t1, t2 = _time(c.get("opponent1", "")), _time(c.get("opponent2", ""))
        if not (t1 and t2) or "tbd" in (t1, t2) or t1 == t2:
            continue
        if str(c.get("finished", "")).lower() == "true" or c.get("winner") in ("1", "2"):
            continue
        quando = data_utc(c.get("date", ""), pagina)
        if not quando:
            continue
        mapas = [k for k in c if re.fullmatch(r"map\d+", k)]
        try:
            bo = int(str(c.get("bestof", "")).strip() or len(mapas) or 1)
        except ValueError:
            bo = len(mapas) or 1
        terminados = 0
        for k in mapas:
            mb = next(blocos(c[k], "Map"), None)
            if mb and str(campos(mb).get("finished", "")).lower() == "true":
                terminados += 1
        fora.append({"pagina": pagina, "tier": tier, "inicio_utc": quando, "time1": t1, "time2": t2,
                     "bo": bo, "mapas_jogados": terminados})
    return fora
