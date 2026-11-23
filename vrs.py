# -*- coding: utf-8 -*-
"""Valve Regional Standings (ranking oficial da Valve), aberto no GitHub (26/10/2026).

github.com/ValveSoftware/counter-strike_regional_standings, pasta live/<ano>,
arquivos standings_global_AAAA_MM_DD.md (desde 08/2024): posicao, pontos, time e
ELENCO. Baixa uma vez para cache/vrs/ (raw.githubusercontent, publico).
Grava vrs.csv: data, posicao, pontos, time, elenco (jogadores separados por ";").
"""
from __future__ import annotations

import csv
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
CACHE = RAIZ / "cache" / "vrs"
API = "https://api.github.com/repos/ValveSoftware/counter-strike_regional_standings/contents/live/"
RAW = "https://raw.githubusercontent.com/ValveSoftware/counter-strike_regional_standings/main/live/"
UA = {"User-Agent": "GabineteCS/0.1 (modelo pessoal; contato: https://github.com/BOLINAKT/gabinete-cs)"}
_ARQ = re.compile(r"standings_global_(\d{4})_(\d{2})_(\d{2})\.md$")


def _get(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return r.read()


def ler_md(txt: str) -> list:
    """Pura: [(posicao, pontos, time, [jogadores])] da tabela do arquivo."""
    fora = []
    for l in txt.splitlines():
        c = [x.strip() for x in l.strip().strip("|").split("|")]
        if len(c) >= 4 and c[0].isdigit() and c[1].lstrip("-").isdigit():
            fora.append((int(c[0]), int(c[1]), c[2], [j.strip() for j in c[3].split(",") if j.strip()]))
    return fora


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    CACHE.mkdir(parents=True, exist_ok=True)
    linhas = []
    for ano in (2024, 2025, 2026):
        nomes = [x["name"] for x in json.loads(_get(API + str(ano))) if _ARQ.search(x["name"])]
        for n in nomes:
            arq = CACHE / n
            if not arq.exists():
                arq.write_bytes(_get(f"{RAW}{ano}/{n}"))
                time.sleep(0.5)
            a, m, d = _ARQ.search(n).groups()
            for pos, pts, t, el in ler_md(arq.read_text(encoding="utf-8")):
                linhas.append((f"{a}-{m}-{d}", pos, pts, t, ";".join(el)))
    with (RAIZ / "vrs.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["data", "posicao", "pontos", "time", "elenco"])
        w.writerows(sorted(linhas))
    print(f"{len(linhas)} linhas, {len({l[0] for l in linhas})} datas ({min(l[0] for l in linhas)} a {max(l[0] for l in linhas)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
