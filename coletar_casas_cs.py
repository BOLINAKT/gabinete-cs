# -*- coding: utf-8 -*-
"""ODDS DE OUTRAS CASAS (OddsPapi) para CS2 (27/10/2026).

Ele: "a pinnacle vai abrir quase sempre com a odd mais regulada... se
conseguissemos outras casas sinto que seria possivel ver a qualidade do modelo".
A Pinnacle vira a REGUA (preco justo); o valor esta nas casas moles. A OddsPapi
(plano gratis, chave dele no secret ODDS_API_KEY) junta 369 casas, inclusive as
dele: bet365, Superbet, Polymarket, Estrela Bet (e clones), Blaze -- e Betano/Stake.

Por corrida: 1 chamada de jogos (CS2, proximos 3 dias, com odds) + 1 do catalogo de
mercados + 1 de odds por jogo (no maximo MAX_JOGOS). Guarda:
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


# LINHAS DAS CASAS DELE (12/11/2026, Fase 1 do plano do CS): do catalogo da OddsPapi (1 chamada
# por corrida), os mercados de SERIE e de MAPA que interessam -- handicap e total de mapas, placar
# exato, total/handicap de rounds, rounds e kills de cada time, prorrogacao.
_PERIODOS = {"result": 0, "p1": 1, "p2": 2, "p3": 3, "p4": 4, "p5": 5}
_ORDINAL = (" First Map", " Second Map", " Third Map", " Fourth Map", " Fifth Map")
LINHAS_HIST = RAIZ / "odds_casas_cs2_linhas_historico.jsonl"
CATALOGO = RAIZ / "catalogo_casas_cs2.json"
_REGRAS = {"Maps Handicap": ("maps", "spread", None), "Total Maps Over Under": ("maps", "total", None),
           "Total Rounds": ("rounds", "total", None), "Rounds Handicap": ("rounds", "spread", None),
           "Team 1 Total Rounds": ("rounds", "team_total", 1), "Team 2 Total Rounds": ("rounds", "team_total", 2),
           "Kills - Over Under": ("kills", "total", None), "Kills - Over Under Team 1": ("kills", "team_total", 1),
           "Kills - Over Under Team 2": ("kills", "team_total", 2),
           "Will There Be Overtime": ("overtime", "simnao", None)}


def catalogo_de_linhas(markets) -> dict:
    """Pura: {marketId: (unidade, tipo, mapa, pontos, (outcome A, outcome B), time)} -- ou uma
    LISTA dessas tuplas (placar exato: um par por placar).
    mapa 0 = serie. tipo total/team_total -> (Over, Under); spread -> (time 1, time 2), pontos =
    handicap do time 1; simnao -> (Yes, No); placar -> (time 1 a:b, time 2 a:b), pontos = 10a + b."""
    fora = {}
    for m in markets if isinstance(markets, list) else []:
        mapa = _PERIODOS.get(str(m.get("period") or ""))
        if mapa is None or m.get("playerProp"):
            continue
        nome = str(m.get("marketName") or "")
        for suf in _ORDINAL:
            if nome.endswith(suf):
                nome = nome[: -len(suf)]
        outs = {str(o.get("outcomeName")): str(o.get("outcomeId")) for o in m.get("outcomes") or []}
        mid, h = str(m.get("marketId")), m.get("handicap")
        if nome == "Correct Map Score":
            pares = []
            for o in outs:
                a, _, b = o.partition(":")
                if a.isdigit() and b.isdigit() and int(a) > int(b) and f"{b}:{a}" in outs:
                    pares.append(("maps", "placar", 0, float(int(a) * 10 + int(b)), (outs[o], outs[f"{b}:{a}"]), None))
            if pares:
                fora[mid] = pares
            continue
        regra = _REGRAS.get(nome)
        if not regra or int(m.get("marketLength") or 0) != 2:
            continue
        unidade, tipo, qual = regra
        par = {"spread": (outs.get("1"), outs.get("2")), "simnao": (outs.get("Yes"), outs.get("No"))}.get(
            tipo, (outs.get("Over"), outs.get("Under")))
        if None in par or (h is None and tipo != "simnao"):
            continue
        fora[mid] = (unidade, tipo, mapa, float(h or 0.0), par, qual)
    return fora


def linhas_das_casas(odds: dict, catalogo: dict) -> dict:
    """Pura: {casa DELE: [[unidade, tipo, mapa, pontos, odd A, odd B, time], ...]}."""
    fora = {}
    for casa, b in (odds.get("bookmakerOdds") or {}).items():
        if not e_casa_dele(casa) or not b.get("bookmakerIsActive", True) or b.get("suspended"):
            continue
        for mid, mk in (b.get("markets") or {}).items():
            cs = catalogo.get(str(mid))
            if not cs:
                continue
            outs = (mk or {}).get("outcomes") or {}
            for c in (cs if isinstance(cs, list) else [cs]):
                par = []
                for o in c[4]:
                    pl = ((outs.get(o) or {}).get("players") or {}).get("0") or {}
                    par.append(pl.get("price") if pl.get("active", True) else None)
                if all(isinstance(x, (int, float)) and x > 1 for x in par):
                    fora.setdefault(casa, []).append([c[0], c[1], c[2], c[3], par[0], par[1], c[5]])
    return fora


def resumo_do_catalogo(markets, odds_por_jogo) -> list:
    """Pura: os mercados que as casas DELE cotam, por (nome, periodo): linhas, handicaps, casas."""
    por_id = {str(m.get("marketId")): m for m in (markets if isinstance(markets, list) else [])}
    grupos: dict = {}
    for od in odds_por_jogo:
        for casa, b in (od.get("bookmakerOdds") or {}).items():
            if not e_casa_dele(casa):
                continue
            for mid in (b.get("markets") or {}):
                m = por_id.get(str(mid))
                if not m:
                    continue
                k = (str(m.get("marketName")), str(m.get("period")), bool(m.get("playerProp")))
                g = grupos.setdefault(k, {"nome": k[0], "periodo": k[1], "jogador": k[2], "linhas": 0,
                                          "handicaps": set(), "casas": set()})
                g["linhas"] += 1
                if m.get("handicap") is not None:
                    g["handicaps"].add(float(m["handicap"]))
                g["casas"].add(str(casa).split(".")[0])
    fora = [{**g, "handicaps": sorted(g["handicaps"])[:14], "casas": sorted(g["casas"])} for g in grupos.values()]
    return sorted(fora, key=lambda g: (-g["linhas"], g["nome"]))


def linha_principal(par) -> bool:
    """Vale guardar no historico: os dois lados entre 1,30 e 4,00 (fora as alternativas extremas)."""
    return all(1.30 <= float(x) <= 4.00 for x in par)


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
        time.sleep(1.0)
        bruto = chamar("markets", chave, sportId=SPORT_ID)
        catalogo = catalogo_de_linhas(bruto)
        jogos, odds_brutas = [], []
        for f in (fx if isinstance(fx, list) else [])[:MAX_JOGOS]:
            time.sleep(1.0)
            od = chamar("odds", chave, fixtureId=f["fixtureId"])
            odds_brutas.append(od)
            jogos.append({"fixtureId": f["fixtureId"], "time1": f.get("participant1Name"),
                          "time2": f.get("participant2Name"), "torneio": f.get("tournamentName"),
                          "inicio_utc": f.get("startTime"), "casas": precos(od),
                          "linhas": linhas_das_casas(od, catalogo)})
    except urllib.error.HTTPError as e:
        print(f"[casas cs2] a API respondeu {e.code}: parando sem insistir")
        return RC_BLOQUEIO
    except (urllib.error.URLError, OSError) as e:
        print(f"[casas cs2] rede: {type(e).__name__}")
        return RC_BLOQUEIO
    try:
        CATALOGO.write_text(json.dumps({"lido_em": agora, "mercados": resumo_do_catalogo(bruto, odds_brutas)},
                                       ensure_ascii=False, indent=1), encoding="utf-8")
    except (OSError, TypeError, ValueError) as e:
        print(f"[casas cs2] resumo do catalogo falhou: {type(e).__name__}")
    anterior, ant_linhas = {}, {}
    if ATUAL.exists():
        try:
            for j in json.loads(ATUAL.read_text(encoding="utf-8")).get("jogos", []):
                for casa, mk in j["casas"].items():
                    for mid, par in mk.items():
                        anterior[(j["fixtureId"], casa, mid)] = par
                for casa, lst in (j.get("linhas") or {}).items():
                    for l in lst:
                        ant_linhas[(j["fixtureId"], casa, l[0], l[1], l[2], l[3], l[6])] = l[4:6]
        except (OSError, ValueError, KeyError, IndexError):
            anterior, ant_linhas = {}, {}
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
    # historico das LINHAS das casas dele (so as principais, so o que mudou): e com ele que se mede,
    # semanas depois, se a justa do app da dinheiro nas odds reais (Fases 4 e 7 do plano)
    mudou_l = 0
    with LINHAS_HIST.open("a", encoding="utf-8") as h:
        for j in jogos:
            for casa, lst in j["linhas"].items():
                for l in lst:
                    k = (j["fixtureId"], casa, l[0], l[1], l[2], l[3], l[6])
                    if linha_principal(l[4:6]) and ant_linhas.get(k) != l[4:6]:
                        h.write(json.dumps({"lido_em": agora, "fixtureId": j["fixtureId"], "time1": j["time1"],
                                            "time2": j["time2"], "inicio_utc": j["inicio_utc"], "casa": casa,
                                            "linha": l}, ensure_ascii=False) + "\n")
                        mudou_l += 1
    n_casas = len({c for j in jogos for c in j["casas"]})
    n_lin = sum(len(v) for j in jogos for v in j["linhas"].values())
    print(f"[casas cs2] {len(jogos)} jogos, {n_casas} casas com odd; {mudou} vencedores das casas dele mudaram; "
          f"{n_lin} linhas das casas dele ({mudou_l} novas no historico)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
