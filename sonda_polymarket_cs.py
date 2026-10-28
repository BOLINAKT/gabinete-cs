# -*- coding: utf-8 -*-
"""SONDA da Polymarket para CS2 (29/10/2026): qual tag e qual formato de titulo?

Ele: "talvez pegar os jogos da polymarket? ja que ela pega todos os jogos". No LoL o
formato e "LoL: A vs B (BO3) - torneio", tag 65 (tools/coletar_polymarket.py do repo
do LoL). Para o CS ainda nao sabemos -- esta sonda le /sports e tenta as tags/slugs
provaveis, e grava o que voltou em sonda_polymarket_cs.json. Roda no robo (a
Polymarket nao resolve no Brasil).
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://gamma-api.polymarket.com"
SAIDA = Path(__file__).resolve().parent / "sonda_polymarket_cs.json"


def _get(caminho: str, **params):
    url = f"{BASE}/{caminho}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 gabinete", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    out = {}
    try:
        sports = _get("sports")
        out["sports"] = [s for s in (sports if isinstance(sports, list) else [])
                         if any(k in json.dumps(s).lower() for k in ("cs", "counter", "esport"))]
    except (urllib.error.URLError, OSError, ValueError) as e:
        print(f"[sonda] /sports falhou: {e}")
        return 75
    tentativas = {}
    for s in out["sports"]:
        for t in str(s.get("tags") or "").split(","):
            t = t.strip()
            if t.isdigit():
                tentativas[f"tag_id={t}"] = {"tag_id": t}
    for slug in ("counter-strike", "cs2", "csgo", "counter-strike-2", "esports"):
        tentativas[f"tag_slug={slug}"] = {"tag_slug": slug}
    out["eventos"] = {}
    for nome, params in tentativas.items():
        try:
            evs = _get("events", closed="false", limit=60, **params)
        except (urllib.error.URLError, OSError, ValueError) as e:
            out["eventos"][nome] = {"erro": str(e)}
            continue
        evs = evs if isinstance(evs, list) else []
        out["eventos"][nome] = {
            "n": len(evs),
            "titulos": [e.get("title") for e in evs[:40]],
            "exemplo_mercados": [{k: m.get(k) for k in ("question", "sportsMarketType", "outcomes", "outcomePrices",
                                                         "bestBid", "bestAsk", "gameStartTime", "liquidity", "closed")}
                                 for m in (evs[0].get("markets") or [])[:4]] if evs else []}
        print(f"[sonda] {nome}: {len(evs)} eventos; ex.: {[e.get('title') for e in evs[:3]]}")
    SAIDA.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
