# -*- coding: utf-8 -*-
"""GRAVA a previsao do modelo junto com cada leitura de odds (26/10/2026).

A regua de verdade e modelo x Pinnacle no FECHAMENTO. Para ela ser honesta, a
previsao tem de ser a que o modelo dava NAQUELE momento, com o dado de entao --
nao uma refeita depois. O robo de odds (de 3 em 3 h) roda este script logo apos
coletar: uma linha por jogo/mercado precificado em previsoes_cs2.jsonl. O placar
(placar_pinnacle.py) usa a ULTIMA leitura antes do inicio de cada jogo.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import precos_core as pc

RAIZ = Path(__file__).resolve().parent
ODDS = RAIZ / "odds_cs2.json"
SAIDA = RAIZ / "previsoes_cs2.jsonl"


def linhas_da_leitura(jogos: list, lido_em: str) -> list:
    """Pura: as previsoes de uma leitura (so jogo precificado e ainda nao comecado)."""
    fora = []
    for j in jogos:
        if not j["precificado"] or j["ja_comecou"]:
            continue
        for m in j["mercados"]:
            a, b = m["lados"]
            fora.append({"lido_em": lido_em, "jogo": j["id"], "inicio_utc": j["inicio_utc"], "bo": j["bo"],
                         "liga": j["liga"], "casa": j["casa"], "fora": j["fora"],
                         "time_casa": j["casou"][0][0], "time_fora": j["casou"][1][0],
                         "mercado": m["mercado"], "periodo": m["periodo"],
                         "p_modelo_casa": round(a["p_modelo"], 4),
                         "p_pinnacle_casa": None if a["p_pinnacle"] is None else round(a["p_pinnacle"], 4),
                         "odd_casa": a["odd_pinnacle"], "odd_fora": b["odd_pinnacle"]})
        # handicap/total de mapas (Fase 2, 12/11/2026): gravados a parte ("tipo": "serie_extra") para
        # medir depois; o placar de vencedor (placar_pinnacle) ignora estas linhas
        for m in j.get("mercados_serie") or []:
            a, b = m["lados"]
            if a["odd_pinnacle"] is None and b["odd_pinnacle"] is None:
                continue
            fora.append({"lido_em": lido_em, "jogo": j["id"], "inicio_utc": j["inicio_utc"], "bo": j["bo"],
                         "liga": j["liga"], "casa": j["casa"], "fora": j["fora"],
                         "time_casa": j["casou"][0][0], "time_fora": j["casou"][1][0],
                         "tipo": "serie_extra", "mercado": f"{m['mercado']}: {a['rotulo']}", "periodo": 0,
                         "rotulo_a": a["rotulo"], "rotulo_b": b["rotulo"],
                         "p_modelo_a": round(a["p_modelo"], 4),
                         "p_pinnacle_a": None if a["p_pinnacle"] is None else round(a["p_pinnacle"], 4),
                         "odd_a": a["odd_pinnacle"], "odd_b": b["odd_pinnacle"]})
    return fora


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    if not ODDS.exists():
        print("[previsoes] sem odds")
        return 0
    odds = json.loads(ODDS.read_text(encoding="utf-8"))
    est = pc.Estado()
    novas = linhas_da_leitura(pc.calcular(est, odds), odds["lido_em"])
    with SAIDA.open("a", encoding="utf-8") as f:
        for l in novas:
            f.write(json.dumps(l, ensure_ascii=False) + "\n")
    print(f"[previsoes] {len(novas)} previsoes gravadas (leitura {odds['lido_em']}, mapas ate {est.fim:%d/%m %H:%M})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
