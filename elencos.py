# -*- coding: utf-8 -*-
"""ELENCOS dos times, com datas, das paginas de time da Liquipedia (26/10/2026).

Cada pagina de time tem {{Squad|status=active|former|inactive ...}} com um
{{Person|id=...|joindate=...|leavedate=...|inactivedate=...}} por pessoa.
Ficam os JOGADORES (sem role, ou role de jogador); tecnico, analista etc. saem.
Saida do jogador = a primeira entre leavedate e inactivedate (banco ja e saida).

Coleta pelo liquipedia.chamar: 50 paginas por chamada (o limite da API), so os
times com 10+ mapas S/A -- 16 chamadas. Grava elencos.csv:
  time, jogador, entrada, saida   (datas AAAA-MM-DD; saida vazia = ainda no time)
"""
from __future__ import annotations

import collections
import csv
import json
import re
import sys
from pathlib import Path

import base_elo as be
import liquipedia as lq

RAIZ = Path(__file__).resolve().parent
SAIDA = RAIZ / "elencos.csv"
LOTE = 50
MIN_MAPAS = 10
NAO_JOGADOR = ("coach", "analyst", "manager", "director", "owner", "psychologist", "streamer", "content")
_DATA = re.compile(r"(\d{4})-(\d{2}|\?\?)-(\d{2}|\?\?)")


def _data(txt: str) -> str:
    """Primeira data do campo; mes/dia desconhecidos ('??') viram 01/15."""
    m = _DATA.search(txt or "")
    if not m:
        return ""
    a, mm, dd = m.groups()
    mm = "01" if mm == "??" else mm
    dd = "15" if dd == "??" else dd
    return f"{a}-{mm}-{dd}"


def _campos(person: str) -> dict:
    """Divide {{Person|a=b|...}} no nivel de cima (ignora | dentro de {{ }} e <ref>)."""
    corpo = person[len("{{Person"):-2]
    partes, nivel, atual = [], 0, ""
    i = 0
    while i < len(corpo):
        if corpo.startswith("{{", i):
            nivel += 1; atual += "{{"; i += 2; continue
        if corpo.startswith("}}", i):
            nivel -= 1; atual += "}}"; i += 2; continue
        c = corpo[i]
        if c == "|" and nivel == 0:
            partes.append(atual); atual = ""
        else:
            atual += c
        i += 1
    partes.append(atual)
    fora = {}
    for p in partes:
        if "=" in p:
            k, v = p.split("=", 1)
            fora[k.strip().lower()] = v.strip()
    return fora


def _persons(txt: str) -> list:
    """Cada {{Person ...}} completo (com chaves aninhadas)."""
    fora, i = [], 0
    while True:
        i = txt.find("{{Person|", i)
        if i < 0:
            return fora
        nivel, j = 0, i
        while j < len(txt):
            if txt.startswith("{{", j):
                nivel += 1; j += 2; continue
            if txt.startswith("}}", j):
                nivel -= 1; j += 2
                if nivel == 0:
                    break
                continue
            j += 1
        fora.append(txt[i:j])
        i = j


def _blocos(txt: str, abre: str) -> list:
    """Cada {{<abre>...}} completo (com chaves aninhadas)."""
    fora, i = [], 0
    while True:
        i = txt.find(abre, i)
        if i < 0:
            return fora
        nivel, j = 0, i
        while j < len(txt):
            if txt.startswith("{{", j):
                nivel += 1; j += 2; continue
            if txt.startswith("}}", j):
                nivel -= 1; j += 2
                if nivel == 0:
                    break
                continue
            j += 1
        fora.append(txt[i:j])
        i = j


def _blocos_de_jogador(txt: str) -> list:
    """Os {{Squad}} de JOGADOR: fora type=staff/organization (diretoria, tecnicos --
    o "Presidente do Conselho" do MIBR estava contando como jogador desde 2021)."""
    fora = []
    for s in _blocos(txt, "{{Squad"):
        cab = s.split("|{{", 1)[0]
        m = re.search(r"type\s*=\s*(\w+)", cab)
        if m and m.group(1).lower() not in ("player", "players"):
            continue
        fora.append(s)
    return fora


def jogadores(wikitexto: str) -> list:
    """Pura: [(jogador, entrada, saida)] da pagina do time (so blocos de jogador)."""
    fora = []
    for p in (x for s in _blocos_de_jogador(wikitexto) for x in _persons(s)):
        c = _campos(p)
        papel = c.get("role", "").lower()
        if any(x in papel for x in NAO_JOGADOR) or not c.get("id"):
            continue
        saidas = [s for s in (_data(c.get("leavedate", "")), _data(c.get("inactivedate", ""))) if s]
        fora.append((c["id"].strip(), _data(c.get("joindate", "")), min(saidas) if saidas else ""))
    return fora


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    d = be.carregar()
    a = d[d.tier.isin(["S", "A"])]
    cont = collections.Counter(list(a.time1) + list(a.time2))
    times = sorted(t for t, n in cont.items() if n >= MIN_MAPAS)
    # titulo real da pagina (o nome canonico pode ser de outra pagina: "Mindfreak")
    pg = json.loads((RAIZ / "times_paginas.json").read_text(encoding="utf-8"))
    de_pagina = {pg.get(t, t): t for t in times}
    linhas, sem = [], []
    for i in range(0, len(times), LOTE):
        lote = [pg.get(t, t) for t in times[i:i + LOTE]]
        r = lq.chamar(action="query", prop="revisions", rvprop="content", rvslots="main",
                      titles="|".join(lote), redirects=1)
        q = r.get("query") or {}
        volta = {x["to"]: x["from"] for x in q.get("redirects") or []}
        volta.update({x["to"]: x["from"] for x in q.get("normalized") or []})
        for p in q.get("pages") or []:
            nome = p["title"]
            while nome in volta:
                nome = volta[nome]
            nome = de_pagina.get(nome, nome)
            if "revisions" not in p:
                sem.append(nome); continue
            js = jogadores(p["revisions"][0]["slots"]["main"]["content"])
            if not js:
                sem.append(nome)
            linhas += [(nome, *j) for j in js]
        print(f"  {min(i + LOTE, len(times))}/{len(times)}", flush=True)
    with SAIDA.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["time", "jogador", "entrada", "saida"])
        w.writerows(linhas)
    print(f"{len(linhas)} passagens de jogador em {len(times) - len(sem)} times; sem elenco: {len(sem)} "
          f"(ex.: {sem[:8]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
