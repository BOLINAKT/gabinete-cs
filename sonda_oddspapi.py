# -*- coding: utf-8 -*-
"""SONDA da OddsPapi (27/10/2026): a chave funciona? quais casas e como vem as odds?

Ele criou a conta (plano gratis) e salvou a chave como secret ODDS_API_KEY. Poucas
chamadas, de proposito (o plano gratis tem limite): sports, fixtures de CS2/LoL/Dota
com odds nos proximos 3 dias, e as odds de UM jogo de cada. A chave NUNCA e impressa.
Grava sonda_oddspapi.json com o que voltou (sem a chave).
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

BASE = "https://api.oddspapi.io/v4/"
ESPORTES = {"CS2": 17, "LoL": 18, "Dota2": 16}
UA = "GabineteCS/0.1 (modelo pessoal; contato: gptconta401@gmail.com)"


def chamar(caminho: str, chave: str, **params):
    url = BASE + caminho + "?" + urllib.parse.urlencode({**params, "apiKey": chave})
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return r.status, json.loads(r.read().decode("utf-8")), dict(r.headers)
    except urllib.error.HTTPError as e:
        corpo = e.read().decode("utf-8", "replace")[:300]
        return e.code, {"erro": corpo}, dict(e.headers or {})


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    chave = os.environ.get("ODDS_API_KEY", "").strip()
    if not chave:
        print("[sonda] sem ODDS_API_KEY no ambiente")
        return 1
    out = {"quando": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    hoje = date.today()
    for nome, sid in ESPORTES.items():
        st, fx, hd = chamar("fixtures", chave, sportId=sid, **{"from": hoje.isoformat(), "to": (hoje + timedelta(days=3)).isoformat(), "hasOdds": "true"})
        lim = {k: v for k, v in hd.items() if "limit" in k.lower() or "remaining" in k.lower()}
        lista = fx if isinstance(fx, list) else (fx.get("data") if isinstance(fx, dict) else None) or []
        print(f"[sonda] {nome}: fixtures status {st} | {len(lista) if isinstance(lista, list) else '?'} jogos | limites {lim}")
        if st != 200:
            print(f"        resposta: {str(fx)[:300]}")
            out[nome] = {"status": st, "resposta": fx}
            continue
        ex = lista[0] if lista else {}
        print(f"        exemplo: {json.dumps(ex, ensure_ascii=False)[:300]}")
        info = {"status": st, "n": len(lista), "exemplo": ex,
                "jogos": [{k: f.get(k) for k in ("fixtureId", "participant1Name", "participant2Name",
                                                 "tournamentName", "startTime")} for f in lista[:40]]}
        if ex.get("fixtureId"):
            time.sleep(1)
            st2, od, _ = chamar("odds", chave, fixtureId=ex["fixtureId"])
            casas = sorted((od.get("bookmakerOdds") or {}).keys()) if isinstance(od, dict) else []
            print(f"        odds status {st2} | {len(casas)} casas: {casas[:60]}")
            info["odds_status"], info["casas"] = st2, casas
            info["odds_exemplo"] = json.dumps(od, ensure_ascii=False)[:4000]
        out[nome] = info
        time.sleep(1)
    # 2a sonda (27/10): o catalogo de CASAS (procurar Estrela Bet, Blaze, casas BR) e
    # o de MERCADOS de cada esporte (os ids 171/172... viram nomes)
    st, bk, _ = chamar("bookmakers", chave)
    lista_bk = bk if isinstance(bk, list) else (bk.get("data") if isinstance(bk, dict) else []) or []
    print(f"[sonda] bookmakers status {st} | {len(lista_bk)} casas")
    out["bookmakers"] = lista_bk if st == 200 else {"status": st, "resposta": bk}
    for nome, sid in ESPORTES.items():
        time.sleep(1)
        st, mk, _ = chamar("markets", chave, sportId=sid)
        print(f"[sonda] markets {nome} status {st} | {len(mk) if isinstance(mk, list) else '?'}")
        out[f"markets_{nome}"] = mk if st == 200 else {"status": st, "resposta": mk}
    Path("sonda_oddspapi.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
