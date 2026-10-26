# -*- coding: utf-8 -*-
"""Coleta as odds de CS2 da Pinnacle e guarda o MOVIMENTO delas (26/10/2026).

POR QUE AGORA: sem guardar as odds a partir de hoje, nunca da para comparar o
modelo com a Pinnacle -- historico de odds de esports nao existe de graca.

CAMPOS DA API: os mesmos que o coletor do LoL le e ja foram medidos la
(parentId, participants/alignment, bestOfX, startTime, matchupId, type, period,
isAlternate, units, prices/designation/points/price).

DE ONDE VEM (o mesmo arranjo do coletor do LoL, tools/coletar_odds.py, que ele
aprovou em 15/09/2026): `guest.api.arcadia.pinnacle.com`, a API que o site da
Pinnacle usa, aberta e sem credencial. Esporte 12 = esports; ficam as ligas cujo
nome comeca com "CS2". Regras, iguais as do LoL:
  - DUAS chamadas por corrida (jogos + precos), de 3 em 3 horas;
  - User-Agent honesto, SEM a chave copiada do site (mandar seria se passar pelo
    site deles);
  - 403/429 = para na hora e sai com 75; nao insiste, nao contorna.

GRAVA:
  odds_cs2.json            o retrato atual (jogos e linhas)
  odds_cs2_historico.jsonl so as linhas cujo preco MUDOU desde a ultima leitura
  odds_cs2_partidas.jsonl  cada jogo visto (id, liga, times, BO, inicio)
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://guest.api.arcadia.pinnacle.com/0.1/"
ESPORTE = 12
AGENTE = ("GabineteCS/0.1 (modelo pessoal de previsao de CS2; 2 chamadas a cada 3 h; "
          "contato: gptconta401@gmail.com)")
RAIZ = Path(__file__).resolve().parent
ATUAL, HIST, PARTIDAS = RAIZ / "odds_cs2.json", RAIZ / "odds_cs2_historico.jsonl", RAIZ / "odds_cs2_partidas.jsonl"
RC_BLOQUEIO = 75


def _get(caminho: str):
    req = urllib.request.Request(BASE + caminho, headers={"User-Agent": AGENTE, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def _e_cs2(m: dict) -> bool:
    return str((m.get("league") or {}).get("name") or "").upper().startswith("CS2")


def jogos_e_linhas(matchups: list, mercados: list) -> tuple:
    """Pura: os jogos de CS2 (pais) e as linhas de preco deles (e dos filhos, mapa a mapa)."""
    jogos, pai_de = {}, {}
    for m in matchups:
        if not _e_cs2(m):
            continue
        parent = m.get("parentId")
        if parent:
            pai_de[m["id"]] = parent
            continue
        times = {str(p.get("alignment")): str(p.get("name")) for p in m.get("participants") or []}
        jogos[m["id"]] = {"id": m["id"], "liga": (m.get("league") or {}).get("name"),
                          "casa": times.get("home"), "fora": times.get("away"),
                          "bo": m.get("bestOfX"), "inicio_utc": m.get("startTime")}
    linhas = []
    for k in mercados:
        mid = k.get("matchupId")
        jogo = mid if mid in jogos else pai_de.get(mid)
        if jogo not in jogos:
            continue
        for preco in k.get("prices") or []:
            lado = preco.get("designation") or preco.get("participantId")
            linhas.append({"jogo": jogo, "matchup": mid, "tipo": k.get("type"),
                           "periodo": k.get("period"), "alternativa": bool(k.get("isAlternate")),
                           "unidade": (k.get("units") or ""),
                           "lado": lado, "pontos": preco.get("points"), "americana": preco.get("price"),
                           "odd": _decimal(preco.get("price"))})
    return list(jogos.values()), linhas


def _decimal(americana):
    try:
        a = float(americana)
    except (TypeError, ValueError):
        return None
    return round(1 + (a / 100 if a > 0 else 100 / -a), 4)


def main() -> int:
    agora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        matchups = _get(f"sports/{ESPORTE}/matchups")
        mercados = _get(f"sports/{ESPORTE}/markets/straight")
    except urllib.error.HTTPError as e:
        if e.code in (403, 429):
            print(f"[odds cs2] a casa respondeu {e.code}: parando sem insistir")
            return RC_BLOQUEIO
        raise
    except (urllib.error.URLError, OSError) as e:
        print(f"[odds cs2] rede: {type(e).__name__}")
        return RC_BLOQUEIO
    jogos, linhas = jogos_e_linhas(matchups, mercados)
    anterior = {}
    if ATUAL.exists():
        try:
            for l in json.loads(ATUAL.read_text(encoding="utf-8")).get("linhas") or []:
                anterior[(l["matchup"], l["tipo"], l["periodo"], l["lado"], l["pontos"])] = l.get("americana")
        except (OSError, ValueError, KeyError):
            anterior = {}
    mudou = [l for l in linhas
             if anterior.get((l["matchup"], l["tipo"], l["periodo"], l["lado"], l["pontos"])) != l["americana"]]
    ATUAL.write_text(json.dumps({"lido_em": agora, "jogos": jogos, "linhas": linhas}, ensure_ascii=False),
                     encoding="utf-8")
    with HIST.open("a", encoding="utf-8") as f:
        for l in mudou:
            f.write(json.dumps({"lido_em": agora, **l}, ensure_ascii=False) + "\n")
    vistos = set()
    if PARTIDAS.exists():
        vistos = {json.loads(t).get("id") for t in PARTIDAS.read_text(encoding="utf-8").splitlines() if t.strip()}
    with PARTIDAS.open("a", encoding="utf-8") as f:
        for j in jogos:
            if j["id"] not in vistos:
                f.write(json.dumps({"visto_em": agora, **j}, ensure_ascii=False) + "\n")
    print(f"[odds cs2] {len(jogos)} jogos, {len(linhas)} linhas, {len(mudou)} mudaram")
    return 0


if __name__ == "__main__":
    sys.exit(main())
