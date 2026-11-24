# -*- coding: utf-8 -*-
"""COMPLETUDE DA BASE DO CS2 (24/11/2026): toda serie que a Liquipedia da como TERMINADA esta na base?

A agenda e os dados do CS saem das paginas dos torneios que o robo acompanha -- conferir um contra o outro
nao pega um torneio inteiro que ficou de fora. Aqui a fonte e outra: Liquipedia:Matches (a pagina geral de
jogos, 1 chamada pesada por rodada, pelo liquipedia.chamar, que respeita o ritmo e as pausas). As series
terminadas ficam 21 dias em agenda_cs_terminados.json; as que nao estao em mapas_cs.csv vao para
evidence/completude_cs.json com o motivo, e a faixa do topo do app mostra (confianca_base_core.py).
So conta como falta a serie que comecou ha mais de 8 h (o robo de dados roda 2x por dia).
Mesmo papel do tools/completude_dota.py do Dota. Regra dele: jogo nunca falta calado.
Uso: python completude_cs.py
"""
from __future__ import annotations

import html as _html
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, OSError, ValueError):
    pass

RAIZ = Path(__file__).resolve().parent
TERM = RAIZ / "agenda_cs_terminados.json"
SAIDA = RAIZ / "evidence" / "completude_cs.json"
PRAZO_H = 8

_CARTAO = re.compile(r'<div class="match-ticker-card"[^>]*>(.*?)(?=<div class="match-ticker-card"[^>]*>|\Z)', re.S)
_OPON = re.compile(r'match-ticker-card(?:&#95;|_){2}opponent(?: [a-z-]+)*">(.*?)(?=match-ticker-card(?:&#95;|_){2}'
                   r'opponent(?: [a-z-]+)*"|match-ticker-card-tournament|\Z)', re.S)
_TS = re.compile(r'data-timestamp="(\d+)"')
_TITULO = re.compile(r'<a href="[^"]*" (?:class="new" )?title="([^"]+)"')
_TORNEIO = re.compile(r'match-ticker-card-tournament-name"><a href="[^"]*" title="([^"#]+)[^"]*">([^<]+)</a>')


def _nome(bloco: str) -> str:
    m = _TITULO.search(bloco)
    if not m:
        return ""
    t = re.sub(r"\s*\(page does not exist\)$", "", _html.unescape(m.group(1)))
    return re.sub(r"\s*\((?:team|Counter-Strike team)\)$", "", t).strip()


def ler_terminadas(html_txt: str) -> list:
    """Pura: Liquipedia:Matches -> series TERMINADAS [{time_a, time_b, inicio_utc, placar, torneio}]."""
    out = []
    for b in _CARTAO.findall(html_txt):
        if 'data-finished="finished"' not in b:
            continue
        ts, ops = _TS.search(b), _OPON.findall(b)
        if not ts or len(ops) < 2:
            continue
        a, c = _nome(ops[0]), _nome(ops[1])
        if not a or not c or "TBD" in (a.upper(), c.upper()):
            continue
        pl = [re.findall(r"<div>(\d+)</div>", o) for o in ops[:2]]
        tn = _TORNEIO.search(b)
        out.append({"time_a": a, "time_b": c,
                    "inicio_utc": datetime.fromtimestamp(int(ts.group(1)), tz=timezone.utc).isoformat(),
                    "placar": f"{pl[0][-1]}-{pl[1][-1]}" if all(pl) else "",
                    "torneio": _html.unescape(tn.group(2)).strip() if tn else ""})
    return out


def conferir(series: list, mapas: pd.DataFrame, canon, agora: datetime) -> list:
    """Pura: series (comecadas ha mais de PRAZO_H) sem mapa na base entre 1 dia antes e 2 dias depois."""
    m = mapas.copy()
    m["dt"] = pd.to_datetime(m["data"], errors="coerce", utc=True)
    m = m.dropna(subset=["dt"])
    pares = [(dt, frozenset((canon(a).lower(), canon(b).lower()))) for dt, a, b in zip(m["dt"], m["time1"], m["time2"])]
    faltam = []
    for s in series:
        ini = pd.Timestamp(s["inicio_utc"])
        if ini > pd.Timestamp(agora) - pd.Timedelta(hours=PRAZO_H):
            continue
        # o nome da Liquipedia passa pelo MESMO tradutor da base ("PVISION" -> PARIVISION, "GOSH" -> BC.Game)
        par = frozenset((canon(s["time_a"].lower()).lower(), canon(s["time_b"].lower()).lower()))
        if not any(p == par and ini - pd.Timedelta(days=1) <= dt <= ini + pd.Timedelta(days=2) for dt, p in pares):
            faltam.append({"inicio": s["inicio_utc"], "a": s["time_a"], "b": s["time_b"], "liga": s.get("torneio"),
                           "placar": s.get("placar", ""),
                           "motivo": "não está na base (torneio fora da coleta ou nome do time diferente)"})
    return faltam


def main() -> int:
    import liquipedia as lq
    agora = datetime.now(timezone.utc)
    try:
        txt = lq.chamar(fresco=True, action="parse", page="Liquipedia:Matches", prop="text")["parse"]["text"]
    except Exception as e:  # noqa: BLE001
        print(f"[completude_cs] Liquipedia nao respondeu ({type(e).__name__}: {e}); fica o arquivo anterior")
        return 0
    try:
        velhas = json.loads(TERM.read_text(encoding="utf-8")).get("series") or []
    except (OSError, ValueError):
        velhas = []
    juntas = {(s["time_a"], s["time_b"], s["inicio_utc"]): s for s in velhas + ler_terminadas(txt)}
    limite = (agora - timedelta(days=21)).isoformat()
    series = sorted([s for s in juntas.values() if s["inicio_utc"] >= limite], key=lambda s: s["inicio_utc"])
    TERM.write_text(json.dumps({"atualizado_em": agora.isoformat(timespec="seconds"),
                                "fonte": "Liquipedia (CC-BY-SA): Liquipedia:Matches", "series": series},
                               ensure_ascii=False, indent=1), encoding="utf-8")
    import base_elo as be
    mapa = json.loads((RAIZ / "times_canonicos.json").read_text(encoding="utf-8"))
    mapas = pd.read_csv(RAIZ / "mapas_cs.csv", usecols=["data", "time1", "time2"], low_memory=False)
    faltam = conferir(series, mapas, lambda n: be.canonico(str(n), mapa), agora)
    doc = {"quando": agora.isoformat(timespec="seconds"), "fonte": "Liquipedia:Matches", "janela_dias": 21,
           "prazo_horas": PRAZO_H, "series_conferidas": len(series), "faltando": faltam}
    SAIDA.parent.mkdir(exist_ok=True)
    SAIDA.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[completude_cs] {len(series)} series terminadas guardadas; faltam {len(faltam)} na base")
    for f in faltam[:10]:
        print("  -", f["inicio"][:10], f["a"], "x", f["b"], f"({f['liga']}, {f['placar']}):", f["motivo"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
