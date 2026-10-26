# -*- coding: utf-8 -*-
"""Coleta os mapas de CS da Liquipedia: torneios S, A e B-Tier, 2020 em diante (25/10/2026).

  1. lista os torneios das categorias "S/A/B-Tier Tournaments" (API, com continuacao);
  2. fica com os de 2020+ (o ano esta no nome da pagina) e tira paginas de usuario;
  3. para cada torneio: a pagina e as SUBPAGINAS (Stage 1, Playoffs...), que e onde
     os Majors e as ligas guardam as partidas;
  4. extrai uma linha por mapa (extrator.py) e grava mapas_cs.csv.

Tudo passa por liquipedia.chamar: 1 chamada a cada 2,1 s e cache em disco, entao
rodar de novo NAO repete chamada -- so busca o que falta. Pode parar e continuar.
Fonte: Liquipedia (CC-BY-SA 3.0).

Uso: python coletor.py [--limite N]   (N torneios, para testar)
"""
from __future__ import annotations

import argparse
import functools
print = functools.partial(print, flush=True)  # o log mostra o progresso na hora
import csv
import re
import sys
import time
from pathlib import Path

import extrator as ex
import liquipedia as lp

RAIZ = Path(__file__).resolve().parent
SAIDA = RAIZ / "mapas_cs.csv"
TIERS = (("S", "Category:S-Tier Tournaments"), ("A", "Category:A-Tier Tournaments"),
         ("B", "Category:B-Tier Tournaments"))
ANO_MINIMO = 2020


def torneios() -> list:
    vistos, fora = set(), []
    for tier, cat in TIERS:
        cont = {}
        while True:
            d = lp.chamar(action="query", list="categorymembers", cmtitle=cat, cmlimit=500,
                          cmnamespace=0, **cont)
            for x in (d.get("query") or {}).get("categorymembers", []):
                t = x["title"]
                anos = [int(a) for a in re.findall(r"(?<!\d)(20\d\d)(?!\d)", t)]
                if t in vistos or not anos or max(anos) < ANO_MINIMO:
                    continue
                vistos.add(t)
                fora.append((tier, t))
            if "continue" not in d:
                break
            cont = {k: v for k, v in d["continue"].items()}
    return fora


def subpaginas(titulo: str) -> list:
    d = lp.chamar(action="query", list="allpages", apprefix=titulo + "/", aplimit=100, apnamespace=0)
    return [p["title"] for p in (d.get("query") or {}).get("allpages", [])]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limite", type=int, default=0)
    a = ap.parse_args()
    lista = torneios()
    print(f"[coletor] {len(lista)} torneios S/A/B de {ANO_MINIMO}+")
    if a.limite:
        lista = lista[: a.limite]
    linhas, t0 = [], time.monotonic()
    for i, (tier, titulo) in enumerate(lista, 1):
        for pagina in [titulo, *subpaginas(titulo)]:
            try:
                linhas.extend(ex.mapas_da_pagina(lp.wikitexto(pagina), pagina=pagina, tier=tier))
            except Exception as e:  # uma pagina ruim nao derruba a coleta
                print(f"  ! {pagina}: {type(e).__name__}: {e}")
        if i % 25 == 0:
            print(f"  {i}/{len(lista)} torneios · {len(linhas)} mapas · {time.monotonic() - t0:.0f}s")
    # o mesmo mapa pode aparecer em duas paginas (pagina e subpagina): fica um
    unicos, vistos = [], set()
    for l in linhas:
        k = (l["data"], tuple(sorted((l["time1"], l["time2"]))), l["mapa_n"], l["mapa"])
        if k in vistos:
            continue
        vistos.add(k)
        unicos.append(l)
    unicos.sort(key=lambda l: (l["data"] or "", l["pagina"], l["mapa_n"]))
    with SAIDA.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(unicos[0].keys()) if unicos else ["pagina"])
        w.writeheader()
        w.writerows(unicos)
    print(f"[coletor] {len(unicos)} mapas gravados em {SAIDA.name} ({time.monotonic() - t0:.0f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
