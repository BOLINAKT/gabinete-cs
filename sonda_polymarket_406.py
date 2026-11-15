# -*- coding: utf-8 -*-
"""Por que a Gamma (Polymarket) passou a responder 406 em 12/11/2026? Testa variantes do pedido
e imprime o codigo de cada uma (e o comeco do corpo do erro). So leitura, sem chave."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://gamma-api.polymarket.com"
UA_NAVEGADOR = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0 Safari/537.36")
VARIANTES = [
    ("como hoje", "events", {"tag_id": 100780, "closed": "false", "limit": 100, "offset": 0},
     {"User-Agent": "Mozilla/5.0 gabinete", "Accept": "application/json"}),
    ("sem Accept", "events", {"tag_id": 100780, "closed": "false", "limit": 100, "offset": 0},
     {"User-Agent": "Mozilla/5.0 gabinete"}),
    ("Accept */*", "events", {"tag_id": 100780, "closed": "false", "limit": 100, "offset": 0},
     {"User-Agent": "Mozilla/5.0 gabinete", "Accept": "*/*"}),
    ("UA de navegador", "events", {"tag_id": 100780, "closed": "false", "limit": 100, "offset": 0},
     {"User-Agent": UA_NAVEGADOR, "Accept": "application/json, text/plain, */*", "Accept-Language": "en-US,en;q=0.9"}),
    ("sem offset", "events", {"tag_id": 100780, "closed": "false", "limit": 100},
     {"User-Agent": "Mozilla/5.0 gabinete", "Accept": "application/json"}),
    ("limit 20", "events", {"tag_id": 100780, "closed": "false", "limit": 20},
     {"User-Agent": "Mozilla/5.0 gabinete", "Accept": "application/json"}),
    ("so tag", "events", {"tag_id": 100780}, {"User-Agent": "Mozilla/5.0 gabinete", "Accept": "application/json"}),
    ("pagination", "events/pagination", {"tag_id": 100780, "closed": "false", "limit": 20},
     {"User-Agent": "Mozilla/5.0 gabinete", "Accept": "application/json"}),
    ("keyset", "events/keyset", {"tag_id": 100780, "closed": "false", "limit": 20},
     {"User-Agent": "Mozilla/5.0 gabinete", "Accept": "application/json"}),
    ("markets", "markets", {"tag_id": 100780, "closed": "false", "limit": 5},
     {"User-Agent": "Mozilla/5.0 gabinete", "Accept": "application/json"}),
    ("sports", "sports", {}, {"User-Agent": "Mozilla/5.0 gabinete", "Accept": "application/json"}),
    ("python puro", "events", {"tag_id": 100780, "closed": "false", "limit": 20}, {}),
]


def main() -> int:
    for nome, caminho, params, cab in VARIANTES:
        url = f"{BASE}/{caminho}" + ("?" + urllib.parse.urlencode(params) if params else "")
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=cab), timeout=30) as r:
                corpo = r.read().decode("utf-8", "replace")
                try:
                    d = json.loads(corpo)
                    forma = f"lista de {len(d)}" if isinstance(d, list) else f"objeto com {list(d)[:6]}"
                except ValueError:
                    forma = "nao e JSON: " + corpo[:80]
                print(f"[sonda406] {nome}: {r.status} {forma}")
        except urllib.error.HTTPError as e:
            print(f"[sonda406] {nome}: HTTP {e.code} {e.read().decode('utf-8', 'replace')[:200]!r} "
                  f"cab={dict((k, v) for k, v in e.headers.items() if k.lower() in ('server', 'content-type', 'cf-mitigated', 'retry-after'))}")
        except (urllib.error.URLError, OSError) as e:
            print(f"[sonda406] {nome}: rede {type(e).__name__}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
