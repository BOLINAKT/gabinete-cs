# -*- coding: utf-8 -*-
"""Resolve o NOME DE MODELO de cada time para a pagina canonica dele (26/10/2026).

O BUG: a Liquipedia escreve o time pelo nome curto do modelo ({{TeamOpponent|tl}}),
e esse nome curto mudou com o tempo -- "liquid" virou "tl", "vitality" virou
"vit", "gamerlegion" virou "gl". Lido cru, o Elo achava que a Liquid de 2025 era
um time NOVO e jogava fora o historico.

A CURA: o proprio modelo {{Team|nome}} da Liquipedia diz qual pagina e o time
(data-highlighting-class="Team Liquid"). Uma chamada expandtemplates resolve
LOTE nomes de uma vez, pelo liquipedia.chamar (2,1 s, cache). Grava
times_canonicos.json: nome curto -> pagina do time. Sem modelo = fica o nome.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

import liquipedia as lq

RAIZ = Path(__file__).resolve().parent
SAIDA = RAIZ / "times_canonicos.json"
LOTE = 80
_ROT = re.compile(r"@@(.*?)@@(.*)")
_CLASSE = re.compile(r'data-highlighting-class="([^"]+)"')


def ler_lote(texto: str) -> dict:
    """Pura: o wikitexto expandido -> {nome: pagina}."""
    fora = {}
    for linha in texto.splitlines():
        m = _ROT.match(linha)
        if m:
            c = _CLASSE.search(m.group(2))
            if c:
                fora[m.group(1)] = c.group(1)
    return fora


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    d = pd.read_csv(RAIZ / "mapas_cs.csv", usecols=["time1", "time2"])
    nomes = sorted(set(d.time1.dropna().astype(str)) | set(d.time2.dropna().astype(str)))
    mapa = {}
    for i in range(0, len(nomes), LOTE):
        lote = [n for n in nomes[i:i + LOTE] if "@" not in n and "}" not in n and "|" not in n]
        txt = "\n".join(f"@@{n}@@{{{{Team|{n}}}}}" for n in lote)
        r = lq.chamar(action="expandtemplates", text=txt, prop="wikitext")
        mapa.update(ler_lote(r["expandtemplates"]["wikitext"]))
        print(f"  {min(i + LOTE, len(nomes))}/{len(nomes)}", flush=True)
    SAIDA.write_text(json.dumps(mapa, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")
    juntos = len(nomes) - len(set(mapa.get(n, n) for n in nomes))
    print(f"{len(mapa)} de {len(nomes)} nomes resolvidos; {juntos} nomes viraram o mesmo time de outro")
    return 0


if __name__ == "__main__":
    sys.exit(main())
