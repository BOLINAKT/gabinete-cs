# -*- coding: utf-8 -*-
"""MELHORES APOSTAS NAS CASAS DELE (Fases 4 e 6 do plano do CS, 15/11/2026).

A regra, toda medida ou dita por ele:
  - a JUSTA: a Pinnacle sem margem quando ela tem o mercado -- na regua (regua_cs.py) o peso do
    modelo na mistura com a Pinnacle deu 0, como no LoL e no Dota; sem Pinnacle, o modelo;
  - a ODD: a que ele consegue de verdade -- compra na Polymarket (meio do livro + meio spread,
    livro vazio fora) e a Stake (OddsPapi, so se a leitura for recente);
  - entra o que tem valor entre 1% e 20% (acima disso quase sempre e dado errado);
  - DESTAQUE: justa abaixo de 1,72 (a regra dele: aposta provavel primeiro, depois o valor).
Mercados: vencedor da serie, +-1,5 e total de mapas, handicap de rounds por mapa (o validado).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import serie_cs as sc

DESTAQUE = 1.72
VALOR_MIN, VALOR_MAX = 1.0, 20.0


def _justa(p_pinnacle, p_modelo):
    if p_pinnacle is not None:
        return float(p_pinnacle), "Pinnacle"
    return (float(p_modelo), "modelo") if p_modelo is not None else (None, None)


def _num_do_rotulo(rotulo: str) -> float:
    """"BIG −1,5" -> -1.5; "Mais de 2,5 mapas" -> 2.5."""
    import re
    m = re.findall(r"[−+\-]?\d+(?:,\d+)?", rotulo)
    return float(m[-1].replace("−", "-").replace(",", ".")) if m else 0.0


def _chave_serie(m: dict, i: int) -> Dict[str, Any]:
    """Como conferir depois um lado de mercados_serie (i = 0 ou 1)."""
    rot = m["lados"][i]["rotulo"]
    if m["mercado"].startswith("Mapas"):
        return {"tipo": "hc_mapas", "lado": "casa" if i == 0 else "fora", "linha": _num_do_rotulo(rot)}
    if m["mercado"] == "Total de mapas":
        return {"tipo": "tot_mapas", "lado": "over" if i == 0 else "under", "linha": abs(_num_do_rotulo(rot))}
    return {"tipo": "outro"}


def _cand(j, mercado, aposta, casa, odd, p_pin, p_mod, chave=None) -> Optional[Dict[str, Any]]:
    p, fonte = _justa(p_pin, p_mod)
    if p is None or not odd or odd <= 1 or not (0 < p < 1):
        return None
    return {"chave": chave or {"tipo": "outro"},
            "jogo": j, "mercado": mercado, "aposta": aposta, "casa": casa, "odd": float(odd), "p_justa": p,
            "odd_justa": 1 / p, "fonte": fonte, "valor": (p * odd - 1) * 100,
            "valor_modelo": None if p_mod is None else (p_mod * odd - 1) * 100,
            "destaque": (1 / p) < DESTAQUE, "pouco_dado": bool(j.get("pouco_dado"))}


def candidatos(j: dict, rounds_poly: Optional[list] = None, stake: Optional[list] = None) -> List[Dict[str, Any]]:
    """Todas as apostas do jogo nas casas dele, com justa e valor (sem filtrar). Pura.
    rounds_poly: precos_core.rounds_da_polymarket(j, tabela); stake: as linhas de
    precos_core.outras_casas(j, ...) (so se a leitura for recente)."""
    if not j.get("precificado") or not j.get("mercados"):
        return []
    fora = []
    venc = j["mercados"][0]["lados"]                       # [casa, fora] da serie (ou do mapa unico)
    nome_venc = j["mercados"][0]["mercado"]
    pm = j.get("poly") or {}
    if pm.get("p_a") is not None and pm.get("spread") is not None and pm["spread"] <= sc.SPREAD_MAXIMO:
        ca, cb = pm["p_a"] + pm["spread"] / 2, pm["p_b"] + pm["spread"] / 2
        if pm.get("invertido"):
            ca, cb = cb, ca
        for l, custo, lado in zip(venc, (ca, cb), ("casa", "fora")):
            if 0.01 < custo < 0.99:
                fora.append(_cand(j, nome_venc, l["lado"], "Polymarket", 1 / custo, l["p_pinnacle"], l["p_modelo"],
                                  {"tipo": "venc", "lado": lado}))
    for m in j.get("mercados_serie") or []:
        for i, l in enumerate(m["lados"]):
            if l.get("odd_poly"):
                fora.append(_cand(j, m["mercado"], l["rotulo"], "Polymarket", l["odd_poly"], l.get("p_pinnacle"),
                                  l["p_modelo"], _chave_serie(m, i)))
    for l in rounds_poly or []:
        if l["tipo"] == "spread" and l.get("validado"):
            quem = j["casa"] if l["lado"] == "home" else j["fora"]
            fora.append(_cand(j, f"Handicap de rounds · mapa {l['mapa']}", f"{quem} {l['pontos']:+.1f}".replace(".", ","),
                              "Polymarket", l["odd"], l.get("p_pinnacle"), l["p_modelo"],
                              {"tipo": "hc_rounds", "lado": "casa" if l["lado"] == "home" else "fora",
                               "linha": float(l["pontos"]), "mapa": int(l["mapa"])}))
    for s in stake or []:
        if s.get("casa") != "Stake" or s.get("periodo") != 0:
            continue
        for l, odd, lado in zip(venc, (s.get("odd_casa"), s.get("odd_fora")), ("casa", "fora")):
            fora.append(_cand(j, nome_venc, l["lado"], "Stake", odd, l["p_pinnacle"], l["p_modelo"],
                              {"tipo": "venc", "lado": lado}))
    return [c for c in fora if c]


def melhores_nas_casas(lista: List[Dict[str, Any]], minimo: float = VALOR_MIN, maximo: float = VALOR_MAX) -> List[Dict[str, Any]]:
    """Filtra pelo valor e ordena: com regua (Pinnacle) antes de so-modelo; destaque (justa < 1,72)
    primeiro; depois o valor. Pura."""
    ok = [c for c in lista if minimo <= c["valor"] <= maximo
          and not c["jogo"].get("ja_comecou") and c["jogo"].get("situacao", "a jogar") == "a jogar"]
    return sorted(ok, key=lambda c: (c["fonte"] != "Pinnacle", not c["destaque"], -c["valor"]))
