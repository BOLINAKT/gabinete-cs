# -*- coding: utf-8 -*-
"""Cliente da API MediaWiki da Liquipedia, nos termos dela (25/10/2026).

POR QUE A LIQUIPEDIA. Sondado em 25/10/2026 (LEIA-ME.md): o bo3.gg tem os
melhores dados, mas o robots.txt dele diz "Disallow: /api/" para todos -- eles
nao querem robo na API, entao nao usamos. A HLTV devolve o desafio do
Cloudflare. A Liquipedia PERMITE uso automatico pela API, com regras:

TERMOS (lidos em https://liquipedia.net/api-terms-of-use, 25/10/2026):
  - no maximo 1 chamada a cada 2 s (action=parse: 1 a cada 30 s -- nao usamos);
  - User-Agent proprio, com contato; gzip obrigatorio; reusar a conexao;
  - guardar em cache e NUNCA pedir duas vezes o mesmo dado;
  - conteudo CC-BY-SA 3.0: citar a Liquipedia como fonte;
  - paginas HTML por robo sao PROIBIDAS: so a API.
Este modulo garante os quatro primeiros sozinho: ritmo, cabecalho, gzip e
cache em disco (cache/liquipedia/*.json). Violacao = bloqueio de IP.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://liquipedia.net/counterstrike/api.php"
UA = ("GabineteCS/0.1 (modelo pessoal de previsao de CS2; dados citados como Liquipedia CC-BY-SA; "
      "contato: gptconta401@gmail.com)")
INTERVALO_S = 2.1
CACHE = Path(__file__).resolve().parent / "cache" / "liquipedia"
_ultima = [0.0]


def chamar(**params) -> dict:
    """Uma chamada a API, com cache em disco e ritmo garantido."""
    params = {"format": "json", "formatversion": "2", **params}
    chave = hashlib.sha1(json.dumps(params, sort_keys=True).encode()).hexdigest()[:20]
    arq = CACHE / f"{chave}.json"
    if arq.exists():
        return json.loads(arq.read_text(encoding="utf-8"))
    espera = INTERVALO_S - (time.monotonic() - _ultima[0])
    if espera > 0:
        time.sleep(espera)
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=40) as r:
        corpo = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            corpo = gzip.decompress(corpo)
    _ultima[0] = time.monotonic()
    dados = json.loads(corpo.decode("utf-8"))
    CACHE.mkdir(parents=True, exist_ok=True)
    arq.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    return dados


def wikitexto(pagina: str) -> str:
    d = chamar(action="query", prop="revisions", rvprop="content", rvslots="main", titles=pagina)
    paginas = (d.get("query") or {}).get("pages") or []
    if not paginas or "revisions" not in paginas[0]:
        return ""
    return paginas[0]["revisions"][0]["slots"]["main"]["content"]


def buscar(texto: str, limite: int = 10) -> list:
    d = chamar(action="query", list="search", srsearch=texto, srlimit=limite)
    return [r["title"] for r in (d.get("query") or {}).get("search") or []]
