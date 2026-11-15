# -*- coding: utf-8 -*-
"""Quanto da cota da OddsPapi ja foi (15/11/2026). /v4/account NAO gasta cota e responde mesmo
com a cota estourada. A chave nunca e impressa; da resposta saem so os campos de cota."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

OCULTAR = ("key", "token", "email", "secret", "password", "name", "user", "bookmakers", "sports", "_id")


def limpar(x):
    """Pura: tira da resposta qualquer campo que pareca credencial ou dado pessoal."""
    if isinstance(x, dict):
        return {k: limpar(v) for k, v in x.items() if not any(o in str(k).lower() for o in OCULTAR)}
    if isinstance(x, list):
        return [limpar(v) for v in x[:20]]
    return x


def main() -> int:
    chave = os.environ.get("ODDS_API_KEY", "").strip()
    if not chave:
        print("[conta] sem ODDS_API_KEY")
        return 1
    url = "https://api.oddspapi.io/v4/account?" + urllib.parse.urlencode({"apiKey": chave})
    req = urllib.request.Request(url, headers={"User-Agent": "GabineteCS/0.1", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            print("[conta]", json.dumps(limpar(json.loads(r.read().decode("utf-8"))), ensure_ascii=False))
    except urllib.error.HTTPError as e:
        corpo = e.read().decode("utf-8", "replace")[:300].replace(chave, "***")
        print(f"[conta] HTTP {e.code}: {corpo}")
    except (urllib.error.URLError, OSError) as e:
        print(f"[conta] rede: {type(e).__name__}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
