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
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://liquipedia.net/counterstrike/api.php"
UA = ("GabineteCS/0.1 (modelo pessoal de previsao de CS2; dados citados como Liquipedia CC-BY-SA; "
      "contato: https://github.com/BOLINAKT/gabinete-cs)")
INTERVALO_S = 2.1
CACHE = Path(__file__).resolve().parent / "cache" / "liquipedia"
_ultima = [0.0]


BLOQUEIO = CACHE.parent / "liquipedia_429.txt"
PAUSA_PADRAO_S = 3600
PAUSA_MAX_S = 24 * 3600
# Chamadas PESADAS (montam a pagina): as regras da Liquipedia pedem 1 a cada 30 s.
# 26/10/2026: 75 expandtemplates a 2,1 s (resolver_times.py) foram o provavel
# motivo do 429 -- erro nosso. Agora o ritmo depende do tipo de chamada.
PESADAS = {"parse", "expandtemplates"}
INTERVALO_PESADA_S = 31.0


class Pausado(RuntimeError):
    """A Liquipedia pediu para esperar (429): nenhuma chamada ate o fim da pausa."""


def _pausa_anterior() -> tuple:
    """(fim da ultima pausa em epoch, duracao dela em s) -- (0, 0) se nunca houve."""
    try:
        partes = BLOQUEIO.read_text(encoding="utf-8").split()
        ate = float(partes[0])
        return ate, float(partes[1]) if len(partes) > 1 else PAUSA_PADRAO_S
    except (OSError, ValueError, IndexError):
        return 0.0, 0.0


def pausa_restante() -> float:
    """Segundos que ainda faltam da pausa pedida pelo site (0 = liberado)."""
    ate, _ = _pausa_anterior()
    return max(0.0, ate - time.time())


def do_cache(**params):
    """O que o cache tem para estes parametros, sem rede (None se nao tem)."""
    params = {"format": "json", "formatversion": "2", **params}
    chave = hashlib.sha1(json.dumps(params, sort_keys=True).encode()).hexdigest()[:20]
    arq = CACHE / f"{chave}.json"
    return json.loads(arq.read_text(encoding="utf-8")) if arq.exists() else None


def chamar(fresco: bool = False, **params) -> dict:
    """Uma chamada a API, com cache em disco e ritmo garantido.

    fresco=True (26/10/2026, so para o VETO de um jogo que vai comecar): ignora o
    cache na leitura -- a pagina muda minutos antes do jogo -- mas mantem o ritmo
    de 1 chamada a cada 2,1 s e regrava o cache."""
    params = {"format": "json", "formatversion": "2", **params}
    chave = hashlib.sha1(json.dumps(params, sort_keys=True).encode()).hexdigest()[:20]
    arq = CACHE / f"{chave}.json"
    if arq.exists() and not fresco:
        return json.loads(arq.read_text(encoding="utf-8"))
    # 429 (26/10/2026): o site pediu para parar. Uma hora (ou o Retry-After dele)
    # sem NENHUMA chamada -- insistir e o que leva a bloqueio de IP.
    if pausa_restante() > 0:
        raise Pausado(f"Liquipedia pediu pausa: faltam {pausa_restante() / 60:.0f} min")
    intervalo = INTERVALO_PESADA_S if params.get("action") in PESADAS else INTERVALO_S
    espera = intervalo - (time.monotonic() - _ultima[0])
    if espera > 0:
        time.sleep(espera)
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip"})
    try:
        r = urllib.request.urlopen(req, timeout=40)
    except urllib.error.HTTPError as e:
        _ultima[0] = time.monotonic()
        if e.code == 429:
            try:
                seg = float(e.headers.get("Retry-After") or PAUSA_PADRAO_S)
            except ValueError:
                seg = PAUSA_PADRAO_S
            # PAUSA CRESCENTE: 429 logo depois de uma pausa = o bloqueio e mais
            # longo; dobra (1 h, 2 h, 4 h... ate 24 h) em vez de bater de novo.
            ate_antes, pausa_antes = _pausa_anterior()
            pausa = max(seg, PAUSA_PADRAO_S)
            if ate_antes and time.time() - ate_antes < 3 * 3600:
                pausa = min(max(pausa, 2 * pausa_antes), PAUSA_MAX_S)
            BLOQUEIO.parent.mkdir(parents=True, exist_ok=True)
            BLOQUEIO.write_text(f"{time.time() + pausa} {pausa}", encoding="utf-8")
            raise Pausado(f"Liquipedia respondeu 429: pausa de {pausa / 60:.0f} min") from e
        raise
    with r:
        corpo = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            corpo = gzip.decompress(corpo)
    _ultima[0] = time.monotonic()
    dados = json.loads(corpo.decode("utf-8"))
    CACHE.mkdir(parents=True, exist_ok=True)
    arq.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    return dados


def wikitexto(pagina: str, fresco: bool = False) -> str:
    d = chamar(fresco=fresco, action="query", prop="revisions", rvprop="content", rvslots="main", titles=pagina)
    paginas = (d.get("query") or {}).get("pages") or []
    if not paginas or "revisions" not in paginas[0]:
        return ""
    return paginas[0]["revisions"][0]["slots"]["main"]["content"]


def buscar(texto: str, limite: int = 10) -> list:
    d = chamar(action="query", list="search", srsearch=texto, srlimit=limite)
    return [r["title"] for r in (d.get("query") or {}).get("search") or []]
