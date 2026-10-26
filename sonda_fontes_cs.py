# -*- coding: utf-8 -*-
"""SONDA DAS FONTES DE DADOS DO CS2 (25/10/2026).

Primeiro passo do modelo de CS, combinado com ele: MEDIR antes de construir
(o mesmo caminho que deu certo na Polymarket). Uma chamada por fonte, com
User-Agent honesto, e grava o que cada uma respondeu em sonda_fontes.json.
Nada aqui coleta dado de verdade nem insiste: 403/429/desafio do Cloudflare
e anotado e a sonda segue para a proxima.

O que cada fonte precisa responder:
  - responde daqui (Brasil, PC dele)? ou bloqueia?
  - tem RESULTADO historico (o modelo precisa de anos de jogos, por mapa)?
  - tem MAPA a mapa? veto? jogadores?
  - o que os termos de uso dizem (anotado para conferir, nao decidido aqui)

FONTES (pesquisadas em 25/10/2026; ver a conversa):
  - Pinnacle (a API interna que o coletor do LoL ja usa, esporte 12 = esports)
  - HLTV (a mais completa; sem API; Cloudflare)
  - Liquipedia (wiki com API MediaWiki; termos proprios)
  - bo3.gg (API publica que o proprio site usa)
  - csapi.de, cs2-api.org, ggscore.net (APIs "gratis" que dizem ter CS2)

Uso: python sonda_fontes_cs.py
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

UA = ("GabineteCS-sonda/0.1 (pesquisa pessoal de modelo de previsao; uma chamada por fonte; "
      "contato: dono do repositorio)")
SAIDA = Path(__file__).resolve().parent / "sonda_fontes.json"

ALVOS = [
    # Sem X-API-Key, como o coletor do LoL: mandar a chave copiada do site
    # seria se passar pelo site deles (ver tools/coletar_odds.py no LoL).
    ("pinnacle_esports", "https://guest.api.arcadia.pinnacle.com/0.1/sports/12/matchups", {}),
    ("hltv_resultados", "https://www.hltv.org/results", {}),
    ("hltv_robots", "https://www.hltv.org/robots.txt", {}),
    ("liquipedia_api", "https://liquipedia.net/counterstrike/api.php?action=query&meta=siteinfo&format=json", {}),
    ("liquipedia_termos", "https://liquipedia.net/api-terms-of-use", {}),
    ("bo3gg_partidas", "https://api.bo3.gg/api/v1/matches?page[limit]=3&sort=-start_date&filter[matches.status][in]=finished", {}),
    ("csapi_de", "https://csapi.de/", {}),
    ("cs2_api_org", "https://cs2-api.org/", {}),
    ("ggscore", "https://ggscore.net/", {}),
]


def chamar(nome: str, url: str, extra: dict) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json, text/html", **extra})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            corpo = r.read(400_000)
            status = r.status
            tipo = r.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        corpo, status, tipo = e.read(4000), e.code, e.headers.get("Content-Type", "")
    except Exception as e:  # rede: anota e segue
        return {"fonte": nome, "url": url, "status": 0, "erro": f"{type(e).__name__}: {e}"[:300]}
    texto = corpo.decode("utf-8", "replace")
    out = {"fonte": nome, "url": url, "status": status, "tipo": tipo, "bytes": len(corpo),
           "cloudflare": ("Just a moment" in texto or "cf-chl" in texto or "challenge-platform" in texto)}
    if "json" in tipo:
        try:
            out["json_amostra"] = _amostra(json.loads(texto))
        except ValueError:
            out["texto"] = texto[:600]
    else:
        out["texto"] = " ".join(texto.split())[:900]
    return out


def _amostra(obj, prof=0):
    """Estrutura do JSON com pouca coisa de cada nivel."""
    if prof > 3:
        return "..."
    if isinstance(obj, dict):
        return {k: _amostra(v, prof + 1) for k, v in list(obj.items())[:12]}
    if isinstance(obj, list):
        return {"_lista_de": len(obj), "_primeiro": _amostra(obj[0], prof + 1) if obj else None}
    return obj if not isinstance(obj, str) else obj[:120]


def resumo_pinnacle(r: dict) -> dict:
    """Quantos jogos de CS2 a Pinnacle tem agora (a mesma leitura do coletor do LoL)."""
    try:
        req = urllib.request.Request(r["url"], headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=25) as resp:
            dados = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"erro": f"{type(e).__name__}"}
    ligas = {}
    for m in dados if isinstance(dados, list) else []:
        liga = str((m.get("league") or {}).get("name") or "")
        if liga.upper().startswith(("CS2", "COUNTER")) or "CS2" in liga.upper():
            ligas[liga] = ligas.get(liga, 0) + 1
    return {"jogos_cs2": sum(ligas.values()), "ligas": ligas}


def main() -> int:
    rel = {"quando": datetime.now(timezone.utc).isoformat(timespec="seconds"), "fontes": []}
    for nome, url, extra in ALVOS:
        r = chamar(nome, url, extra)
        if nome == "pinnacle_esports":
            r.pop("json_amostra", None)
            r["cs2"] = resumo_pinnacle(r) if r.get("status") == 200 else None
        rel["fontes"].append(r)
        print("{:20s} {:>4} {}{}".format(nome, r.get("status"), "CLOUDFLARE " if r.get("cloudflare") else "",
                                         r.get("erro", "")[:80]))
    SAIDA.write_text(json.dumps(rel, ensure_ascii=False, indent=1), encoding="utf-8")
    print("gravado em", SAIDA)
    return 0


if __name__ == "__main__":
    sys.exit(main())
