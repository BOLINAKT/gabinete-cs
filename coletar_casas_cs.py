# -*- coding: utf-8 -*-
"""ODDS DE OUTRAS CASAS (OddsPapi) para CS2 (27/10/2026).

Ele: "a pinnacle vai abrir quase sempre com a odd mais regulada... se
conseguissemos outras casas sinto que seria possivel ver a qualidade do modelo".
A Pinnacle vira a REGUA (preco justo); o valor esta nas casas moles. A OddsPapi
(plano gratis, chave dele no secret ODDS_API_KEY) junta 369 casas, inclusive as
dele: bet365, Superbet, Polymarket, Estrela Bet (e clones), Blaze -- e Betano/Stake.

Por corrida: 1 chamada de jogos (CS2, proximos 3 dias, com odds) + 1 de odds por
jogo (no maximo MAX_JOGOS). Guarda:
  odds_casas_cs2.json            retrato: TODAS as casas, serie (171) e mapas 1-3
  odds_casas_cs2_historico.jsonl so as casas DELE, so o que mudou
A chave nunca e impressa. 401/403/429 = para, sai 75, nao insiste.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

BASE = "https://api.oddspapi.io/v4/"
SPORT_ID = 17
UA = "GabineteCS/0.1 (modelo pessoal; contato: gptconta401@gmail.com)"
RAIZ = Path(__file__).resolve().parent
ATUAL = RAIZ / "odds_casas_cs2.json"
HIST = RAIZ / "odds_casas_cs2_historico.jsonl"
MAX_JOGOS = 30
RC_BLOQUEIO = 75
# mercado -> (nome, periodo do app: 0 = serie, n = mapa n), e os dois outcomes (time1, time2)
MERCADOS = {"171": ("Série", 0, ("171", "172")), "1747": ("Mapa 1", 1, ("1747", "1748")),
            "1749": ("Mapa 2", 2, ("1749", "1750")), "1751": ("Mapa 3", 3, ("1751", "1752"))}
# as casas DELE (27/10/2026) -- prefixos do slug na OddsPapi; guardamos historico so delas
CASAS_DELE = ("pinnacle", "bet365", "superbet", "polymarket", "estrelabet", "blaze", "betano", "stake")


def e_casa_dele(slug: str) -> bool:
    return any(str(slug).startswith(p) for p in CASAS_DELE)


def chamar(caminho: str, chave: str, **params):
    url = BASE + caminho + "?" + urllib.parse.urlencode({**params, "apiKey": chave})
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode("utf-8"))


def precos(odds: dict) -> dict:
    """Pura: {casa: {mercado: [odd time1, odd time2]}} so dos MERCADOS, casa ativa e nao suspensa."""
    fora = {}
    for casa, b in (odds.get("bookmakerOdds") or {}).items():
        if not b.get("bookmakerIsActive", True) or b.get("suspended"):
            continue
        mk = b.get("markets") or {}
        for mid, (_, _, (o1, o2)) in MERCADOS.items():
            outs = (mk.get(mid) or {}).get("outcomes") or {}
            par = []
            for o in (o1, o2):
                pl = ((outs.get(o) or {}).get("players") or {}).get("0") or {}
                par.append(pl.get("price") if pl.get("active", True) else None)
            if all(isinstance(x, (int, float)) and x > 1 for x in par):
                fora.setdefault(casa, {})[mid] = par
    return fora


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    chave = os.environ.get("ODDS_API_KEY", "").strip()
    if not chave:
        print("[casas cs2] sem ODDS_API_KEY")
        return 1
    agora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    hoje = date.today()
    try:
        fx = chamar("fixtures", chave, sportId=SPORT_ID, hasOdds="true",
                    **{"from": hoje.isoformat(), "to": (hoje + timedelta(days=3)).isoformat()})
        jogos = []
        for f in (fx if isinstance(fx, list) else [])[:MAX_JOGOS]:
            time.sleep(1.0)
            od = chamar("odds", chave, fixtureId=f["fixtureId"])
            jogos.append({"fixtureId": f["fixtureId"], "time1": f.get("participant1Name"),
                          "time2": f.get("participant2Name"), "torneio": f.get("tournamentName"),
                          "inicio_utc": f.get("startTime"), "casas": precos(od)})
    except urllib.error.HTTPError as e:
        print(f"[casas cs2] a API respondeu {e.code}: parando sem insistir")
        return RC_BLOQUEIO
    except (urllib.error.URLError, OSError) as e:
        print(f"[casas cs2] rede: {type(e).__name__}")
        return RC_BLOQUEIO
    anterior = {}
    if ATUAL.exists():
        try:
            for j in json.loads(ATUAL.read_text(encoding="utf-8")).get("jogos", []):
                for casa, mk in j["casas"].items():
                    for mid, par in mk.items():
                        anterior[(j["fixtureId"], casa, mid)] = par
        except (OSError, ValueError, KeyError):
            anterior = {}
    ATUAL.write_text(json.dumps({"lido_em": agora, "jogos": jogos}, ensure_ascii=False), encoding="utf-8")
    mudou = 0
    with HIST.open("a", encoding="utf-8") as h:
        for j in jogos:
            for casa, mk in j["casas"].items():
                if not e_casa_dele(casa):
                    continue
                for mid, par in mk.items():
                    if anterior.get((j["fixtureId"], casa, mid)) != par:
                        h.write(json.dumps({"lido_em": agora, "fixtureId": j["fixtureId"], "time1": j["time1"],
                                            "time2": j["time2"], "inicio_utc": j["inicio_utc"], "casa": casa,
                                            "mercado": MERCADOS[mid][0], "odds": par}, ensure_ascii=False) + "\n")
                        mudou += 1
    n_casas = len({c for j in jogos for c in j["casas"]})
    print(f"[casas cs2] {len(jogos)} jogos, {n_casas} casas com odd; {mudou} linhas das casas dele mudaram")
    return 0


if __name__ == "__main__":
    sys.exit(main())
