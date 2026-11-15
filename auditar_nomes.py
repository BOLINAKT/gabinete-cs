# -*- coding: utf-8 -*-
"""Times PARTIDOS por grafia (15/11/2026). Regra dele: o historico de um time nunca fica partido.

Dois nomes que so diferem por caixa/acento/espaco podem ser o mesmo time escrito de dois jeitos em
alguns torneios ("Heroic" x "HEROIC") -- ou times diferentes de nome generico ("Players",
"Looking for Org"). O elenco nao ajuda (a Liquipedia so guarda o de uma das grafias). A prova
usada, toda nos mapas:
  - o nome principal e um time de verdade: 100+ mapas e elenco conhecido;
  - a grafia alternativa e pequena (ate 30 mapas) e cai DENTRO do periodo de atividade do principal;
  - os dois nunca se enfrentaram e nunca jogaram no mesmo dia.
`python auditar_nomes.py` lista; `--gravar` escreve uniao_times_cs.json (antigo -> atual).
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

import base_elo as be
import precos_core as pc

RAIZ = Path(__file__).resolve().parent
SAIDA = RAIZ / "uniao_times_cs.json"
MIN_COMUNS = 3


def grupos(d: pd.DataFrame) -> dict:
    """{chave normalizada: [nomes distintos, do mais antigo ao mais recente]} com 2+ nomes."""
    ult = {}
    for col in ("time1", "time2"):
        for t, dt in zip(d[col], d["dt"]):
            if t not in ult or dt > ult[t]:
                ult[t] = dt
    g = defaultdict(list)
    for t in ult:
        g[pc._n(t)].append(t)
    return {k: sorted(v, key=lambda t: ult[t]) for k, v in g.items() if len(v) > 1}


def provas(d: pd.DataFrame, elencos: pd.DataFrame, a: str, b: str) -> dict:
    ja = set(elencos[elencos.time == a].jogador)
    jb = set(elencos[elencos.time == b].jogador)
    da = d[(d.time1 == a) | (d.time2 == a)]
    db = d[(d.time1 == b) | (d.time2 == b)]
    enf = int((((d.time1 == a) & (d.time2 == b)) | ((d.time1 == b) & (d.time2 == a))).sum())
    dias_a, dias_b = set(da.dt.dt.date), set(db.dt.dt.date)
    return {"mesmo_dia": len(dias_a & dias_b),
            "comuns": len(ja & jb), "elenco_a": len(ja), "elenco_b": len(jb), "enfrentaram": enf,
            "mapas_a": len(da), "mapas_b": len(db),
            "janela_a": [str(da.dt.min())[:10], str(da.dt.max())[:10]],
            "janela_b": [str(db.dt.min())[:10], str(db.dt.max())[:10]]}


def prova_basta(p: dict) -> bool:
    """Pura: a grafia `a` e o mesmo time que `b`? (ver o cabecalho)"""
    dentro = p["janela_b"][0] <= p["janela_a"][0] and p["janela_a"][1] <= p["janela_b"][1]
    return bool(p["mapas_b"] >= 100 and p["elenco_b"] > 0 and p["mapas_a"] <= 30 and dentro
                and p["enfrentaram"] == 0 and p["mesmo_dia"] == 0)


def auditar(d: pd.DataFrame, elencos: pd.DataFrame) -> list:
    fora = []
    for _k, nomes in grupos(d).items():
        atual = nomes[-1]
        for antigo in nomes[:-1]:
            p = provas(d, elencos, antigo, atual)
            p.update(antigo=antigo, atual=atual, une=prova_basta(p))
            fora.append(p)
    return fora


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    import os
    os.environ["CS_SEM_UNIAO"] = "1"                      # audita os nomes CRUS (sem a uniao ja gravada)
    d = be.carregar(incluir_c=True)
    el = pd.read_csv(RAIZ / "elencos.csv", dtype=str).fillna("")
    r = sorted(auditar(d, el), key=lambda x: (-x["une"], -x["comuns"], -x["mapas_b"]))
    for x in r:
        if x["une"]:
            print(("UNE " if x["une"] else "    "), f"{x['antigo']!r} -> {x['atual']!r} | comuns {x['comuns']} "
                  f"({x['elenco_a']}/{x['elenco_b']}) | enfrentaram {x['enfrentaram']} | mapas {x['mapas_a']}/{x['mapas_b']} "
                  f"| {x['janela_a']} {x['janela_b']}")
    unir = {x["antigo"]: x["atual"] for x in r if x["une"]}
    print(f"{len(r)} pares de nomes parecidos; {len(unir)} com prova para unir")
    if "--gravar" in sys.argv:
        SAIDA.write_text(json.dumps({"_como": "grafia alternativa -> nome atual; prova: principal com 100+ mapas e "
                                              "elenco conhecido, alternativa com ate 30 mapas dentro do periodo dele, "
                                              "nunca se enfrentaram nem jogaram no mesmo dia (auditar_nomes.py)",
                                     "unioes": unir},
                                    ensure_ascii=False, indent=1), encoding="utf-8")
        print("gravado", SAIDA.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
