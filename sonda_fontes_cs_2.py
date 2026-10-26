# -*- coding: utf-8 -*-
"""SONDA DAS FONTES DO CS2, 2a RODADA (25/10/2026).

A 1a rodada (sonda_fontes_cs.py) mostrou: bo3.gg responde com 76.512 partidas
encerradas; Liquipedia pede gzip; HLTV devolve o desafio do Cloudflare.
Aqui, poucas chamadas para responder:
  - bo3.gg: tem MAPA a mapa (games)? ate que data o historico volta? que
    campos a partida traz? os termos de uso dizem o que?
  - Liquipedia: a API responde com gzip? (os termos ja foram lidos)
Grava sonda_fontes_2.json.
"""
from __future__ import annotations

import gzip
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

UA = ("GabineteCS-sonda/0.1 (pesquisa pessoal de modelo de previsao; poucas chamadas; "
      "contato: dono do repositorio)")
SAIDA = Path(__file__).resolve().parent / "sonda_fontes_2.json"
B = "https://api.bo3.gg/api/v1"


def get(url: str, gz: bool = False):
    h = {"User-Agent": UA, "Accept": "application/json, text/html"}
    if gz:
        h["Accept-Encoding"] = "gzip"
    req = urllib.request.Request(url, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            corpo, status, enc = r.read(2_000_000), r.status, r.headers.get("Content-Encoding", "")
    except urllib.error.HTTPError as e:
        return e.code, e.read(3000).decode("utf-8", "replace")
    except Exception as e:
        return 0, f"{type(e).__name__}: {e}"
    if enc == "gzip":
        corpo = gzip.decompress(corpo)
    texto = corpo.decode("utf-8", "replace")
    try:
        return status, json.loads(texto)
    except ValueError:
        return status, " ".join(texto.split())[:3000]


def main() -> int:
    rel = {}
    s, d = get(f"{B}/matches?page[limit]=2&sort=start_date&filter[matches.status][in]=finished")
    rel["bo3_mais_antigas"] = {"status": s, "dados": d}
    s, d = get(f"{B}/matches/132707")
    rel["bo3_uma_partida"] = {"status": s, "dados": d}
    s, d = get(f"{B}/games?filter[games.match_id][eq]=132707")
    rel["bo3_mapas_da_partida"] = {"status": s, "dados": d}
    s, d = get("https://bo3.gg/terms-of-use")
    rel["bo3_termos"] = {"status": s, "dados": d if isinstance(d, str) else str(d)[:3000]}
    s, d = get("https://liquipedia.net/counterstrike/api.php?action=query&meta=siteinfo&format=json", gz=True)
    rel["liquipedia_api_gzip"] = {"status": s, "dados": str(d)[:1500]}
    SAIDA.write_text(json.dumps(rel, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    for k, v in rel.items():
        print(k, v["status"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
