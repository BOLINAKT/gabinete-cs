# -*- coding: utf-8 -*-
"""COLETOR DA POLYMARKET para CS2 (29/10/2026) -- copia do coletor do LoL (23/10/2026).

Ele: "talvez pegar os jogos da polymarket? ja que ela pega todos os jogos" -- a
Polymarket lista jogos que a Liquipedia (agenda S/A/B) e a Pinnacle nao tem (ex.:
Aurora Young Blud x DimoniX). Sonda de 29/10 (sonda_polymarket_cs.json): tag 100780,
titulo "Counter-Strike: A vs B (BO3) - torneio". O resto e o mesmo do LoL:

Segunda referencia de mercado ao lado da Pinnacle, pedida por ele para a tela
de oportunidades. Medido antes (tools/sonda_polymarket.py, rodada de 23/10 no
robo): o LoL e o esporte id 39, tag 65; cada partida e um EVENTO de titulo
"LoL: <A> vs <B> (BO<n>) - <torneio>", e o vencedor esta no mercado com
sportsMarketType == "moneyline" (outcomes = [A, B], gameStartTime = inicio).
Ex. lido: "LoL: LOS vs T1 (BO1) - Worlds Group Stage", 23/10 23:00 UTC.

O PRECO. Polymarket e bolsa, nao casa: nao ha margem embutida, ha o spread
entre a melhor compra e a melhor venda. Usamos o MEIO do livro
((bestBid + bestAsk) / 2) como probabilidade do time A; sem livro, o
outcomePrices. O spread e a liquidez vao junto: preco de mercado vazio nao
vale o mesmo que o de mercado cheio, e a tela tem que poder dizer isso.

Os dominios da Polymarket nao resolvem no Brasil (conferido 23/10): roda no
robo do GitHub (EUA), .github/workflows/polymarket.yml.

FONTES: API Gamma publica (https://gamma-api.polymarket.com), formato medido
pela sonda em evidence/sonda_polymarket.json (23/10/2026). A documentacao
oficial nao abre daqui; nomes de parametro vieram de clientes de terceiros
(polyte-gamma e polyoxide-gamma em docs.rs, cliente OCaml em ocaml.org).

Uso: python coletar_polymarket_cs.py     (sai 75 se a rede falhar)
"""
from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://gamma-api.polymarket.com"
TAG_CS = 100780
RAIZ = Path(__file__).resolve().parent
ATUAL = RAIZ / "polymarket_cs.json"
HISTORICO = RAIZ / "polymarket_cs_historico.jsonl"
_TITULO = re.compile(r"^Counter-Strike:\s*(?P<a>.+?)\s+vs\.?\s+(?P<b>.+?)\s*\(BO(?P<bo>\d)\)\s*(?:-\s*(?P<torneio>.+))?$")


def _get(caminho: str, **params):
    url = f"{BASE}/{caminho}?{urllib.parse.urlencode(params)}"
    # 15/11/2026: desde 12/11 a Gamma responde 406 "gzip_required" a paginas com limit > 50 sem este
    # cabecalho -- os precos ficaram 3 dias parados sem ninguem ver. Pede comprimido e descomprime.
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 gabinete", "Accept": "application/json",
                                               "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(_corpo(r.read(), r.headers.get("Content-Encoding")).decode("utf-8"))


def _corpo(dados: bytes, codificacao) -> bytes:
    """Pura: o corpo da resposta, descomprimido se veio em gzip."""
    if "gzip" in str(codificacao or "").lower() or dados[:2] == b"\x1f\x8b":
        import gzip
        return gzip.decompress(dados)
    return dados


def _lista(v):
    if isinstance(v, list):
        return v
    try:
        x = json.loads(v or "[]")
        return x if isinstance(x, list) else []
    except (TypeError, ValueError):
        return []


def _f(v):
    try:
        x = float(v)
        return x if x == x else None
    except (TypeError, ValueError):
        return None


def _ja_comecou(inicio, agora: datetime) -> bool:
    try:
        dt = datetime.fromisoformat(str(inicio).replace("Z", "+00:00").replace(" ", "T"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt <= agora
    except (TypeError, ValueError):
        return False


def ler_partida(ev: dict, agora: datetime | None = None) -> dict | None:
    """Evento da Gamma -> partida com preco do time A. Pura.

    So PRE-JOGO: depois do inicio o preco e ao vivo (ou ja resolvido, 0,0005
    num jogo acabado, visto na sonda) e nao se compara com o modelo pre-jogo."""
    m = _TITULO.match(str(ev.get("title") or "").strip())
    if not m:
        return None
    ml = next((x for x in (ev.get("markets") or []) if x.get("sportsMarketType") == "moneyline"), None)
    if not ml or ml.get("closed"):
        return None
    times = [str(t) for t in _lista(ml.get("outcomes"))]
    precos = [_f(p) for p in _lista(ml.get("outcomePrices"))]
    if len(times) != 2:
        return None
    if _ja_comecou(ml.get("gameStartTime") or ev.get("startDate"), agora or datetime.now(timezone.utc)):
        return None
    bid, ask = _f(ml.get("bestBid")), _f(ml.get("bestAsk"))
    if bid is not None and ask is not None and 0 < bid <= ask < 1:
        p_a, fonte = (bid + ask) / 2, "meio_do_livro"
    elif len(precos) == 2 and precos[0] is not None:
        p_a, fonte = precos[0], "ultimo_preco"
    else:
        return None
    return {
        "time_a": times[0], "time_b": times[1],
        "p_a": round(p_a, 4), "p_b": round(1 - p_a, 4),
        "fonte_preco": fonte,
        "spread": None if bid is None or ask is None else round(ask - bid, 4),
        "liquidez": _f(ml.get("liquidity")), "volume": _f(ml.get("volume")),
        "bo": int(m.group("bo")), "torneio": (m.group("torneio") or "").strip(),
        "inicio_utc": ml.get("gameStartTime") or ev.get("startDate"),
        "evento": ev.get("slug"),
        "mercados": outros_mercados(ev),
    }


def outros_mercados(ev: dict) -> list:
    """Pura: os mercados do evento alem do vencedor da serie (15/11/2026, Fase 1 do plano do CS):
    vencedor de mapa, handicap e total de mapas... Cada um: tipo, pergunta, linha, os dois lados e
    o preco do PRIMEIRO lado (meio do livro; sem livro, o ultimo preco), spread e liquidez."""
    fora = []
    for x in ev.get("markets") or []:
        if x.get("sportsMarketType") == "moneyline" or x.get("closed"):
            continue
        lados = [str(t) for t in _lista(x.get("outcomes"))]
        precos = [_f(p) for p in _lista(x.get("outcomePrices"))]
        if len(lados) != 2:
            continue
        bid, ask = _f(x.get("bestBid")), _f(x.get("bestAsk"))
        if bid is not None and ask is not None and 0 < bid <= ask < 1:
            p1 = (bid + ask) / 2
        elif len(precos) == 2 and precos[0] is not None and 0 < precos[0] < 1:
            p1 = precos[0]
        else:
            continue
        fora.append({"tipo": x.get("sportsMarketType"), "pergunta": str(x.get("question") or "")[:140],
                     "grupo": x.get("groupItemTitle"), "linha": _f(x.get("line")), "lados": lados,
                     "p1": round(p1, 4), "spread": None if bid is None or ask is None else round(ask - bid, 4),
                     "liquidez": _f(x.get("liquidity"))})
    return fora


def main() -> int:
    try:
        evs = []
        for pagina in range(4):                       # ate 400 eventos (ha mercados que nao sao jogo)
            lote = _get("events", tag_id=TAG_CS, closed="false", limit=100, offset=100 * pagina)
            lote = lote if isinstance(lote, list) else []
            evs += lote
            if len(lote) < 100:
                break
    except (urllib.error.URLError, OSError, ValueError) as e:
        print(f"[polymarket] rede/API falhou: {type(e).__name__}: {e}")
        return 75
    agora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    partidas = [p for p in (ler_partida(e, datetime.now(timezone.utc)) for e in (evs if isinstance(evs, list) else [])) if p]
    ATUAL.write_text(json.dumps({"coletado_em": agora, "fonte": f"{BASE}/events?tag_id={TAG_CS}",
                                 "partidas": partidas}, ensure_ascii=False, indent=1), encoding="utf-8")
    with HISTORICO.open("a", encoding="utf-8") as f:
        for p in partidas:
            f.write(json.dumps({"coletado_em": agora, **{k: v for k, v in p.items() if k != "mercados"}},
                               ensure_ascii=False) + "\n")       # o historico guarda so o vencedor
    print(f"[polymarket] {len(partidas)} partida(s) de CS2 com preco de vencedor")
    return 0


if __name__ == "__main__":
    sys.exit(main())
