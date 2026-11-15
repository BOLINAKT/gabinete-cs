# -*- coding: utf-8 -*-
"""PLACAR DAS APOSTAS (Fase 7 do plano do CS, 15/11/2026): o que a lista "Melhores apostas nas
suas casas" indicou, conferido depois nas odds REAIS que ela mostrou.

registrar (no robo, a cada leitura): grava em apostas_cs2.jsonl as apostas da lista naquele
instante -- com a odd, a justa e a fonte de entao (nada refeito depois).
placar: por aposta, a ULTIMA indicacao antes do jogo; 1 unidade em cada; lucro e ROI por fonte da
justa (Pinnacle x modelo) e com/sem destaque. Com poucas apostas e sorte: o IC vai junto.
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

RAIZ = Path(__file__).resolve().parent
SAIDA = RAIZ / "apostas_cs2.jsonl"


def linhas_para_gravar(melhores: list, lido_em: str) -> list:
    """Pura: as apostas da lista, sem o jogo inteiro dentro."""
    fora = []
    for c in melhores:
        j = c["jogo"]
        fora.append({"lido_em": lido_em, "jogo": j["id"], "inicio_utc": j.get("inicio_utc"), "bo": j.get("bo"),
                     "liga": j.get("liga"), "casa": j["casa"], "fora": j["fora"],
                     "time_casa": j["casou"][0][0], "time_fora": j["casou"][1][0],
                     "mercado": c["mercado"], "aposta": c["aposta"], "onde": c["casa"], "odd": round(c["odd"], 4),
                     "p_justa": round(c["p_justa"], 4), "fonte": c["fonte"], "valor": round(c["valor"], 2),
                     "valor_modelo": None if c["valor_modelo"] is None else round(c["valor_modelo"], 2),
                     "destaque": c["destaque"], "pouco_dado": c["pouco_dado"], "chave": c["chave"]})
    return fora


def ganhou(mapas: List[Dict[str, Any]], chave: Dict[str, Any]) -> Optional[bool]:
    """Pura. mapas: [{"n", "rc", "rf"}] (rounds da casa e da fora em cada mapa jogado).
    None = nao da para conferir (mercado desconhecido, mapa nao jogado, serie empatada)."""
    if not mapas:
        return None
    vc = sum(1 for m in mapas if m["rc"] > m["rf"])
    vf = len(mapas) - vc
    t, lado = chave.get("tipo"), chave.get("lado")
    if t == "venc":
        if vc == vf:
            return None
        return (vc > vf) == (lado == "casa")
    if t == "hc_mapas":
        saldo = (vc - vf) if lado == "casa" else (vf - vc)
        return saldo + float(chave["linha"]) > 0
    if t == "tot_mapas":
        return (len(mapas) > float(chave["linha"])) == (lado == "over")
    if t == "hc_rounds":
        m = next((x for x in mapas if x["n"] == chave.get("mapa")), None)
        if m is None:
            return None
        saldo = (m["rc"] - m["rf"]) if lado == "casa" else (m["rf"] - m["rc"])
        return saldo + float(chave["linha"]) > 0
    return None


def mapas_do_jogo(d: pd.DataFrame, r: dict) -> list:
    """Os mapas da serie nos dados, na orientacao casa/fora da aposta."""
    if not r.get("inicio_utc") or not r.get("time_casa") or not r.get("time_fora"):
        return []
    ini = pd.Timestamp(r["inicio_utc"]).tz_localize(None)
    j = d[(d.dt >= ini - pd.Timedelta(hours=12)) & (d.dt <= ini + pd.Timedelta(hours=18))]
    a, b = r["time_casa"], r["time_fora"]
    ab, ba = j[(j.time1 == a) & (j.time2 == b)], j[(j.time1 == b) & (j.time2 == a)]
    if ab.empty and ba.empty:
        return []
    s, direto = (ab, True) if not ab.empty else (ba, False)
    s = s[s.pagina == s.pagina.iloc[0]]
    return [{"n": int(x.mapa_n), "rc": int(x.rounds1 if direto else x.rounds2),
             "rf": int(x.rounds2 if direto else x.rounds1)} for x in s.itertuples(index=False)]


def ultimas(regs: list) -> list:
    """Pura: por aposta, a ultima indicacao lida ANTES do inicio."""
    ult: dict = {}
    for r in regs:
        if not r.get("inicio_utc") or str(r["lido_em"])[:19] >= str(r["inicio_utc"]).replace(" ", "T")[:19]:
            continue
        k = (r["jogo"], r["mercado"], r["aposta"], r["onde"])
        if k not in ult or r["lido_em"] > ult[k]["lido_em"]:
            ult[k] = r
    return list(ult.values())


def resumo(conferidas: list) -> dict:
    """Pura: conferidas = [{... "lucro": float}]. Lucro, ROI e IC95 por recorte."""
    def rec(ls):
        if not ls:
            return {"n": 0}
        lu = [l["lucro"] for l in ls]
        rnd = random.Random(7)
        b = sorted(sum(rnd.choice(lu) for _ in lu) / len(lu) for _ in range(2000))
        return {"n": len(lu), "acertos": sum(1 for x in lu if x > 0), "lucro": round(sum(lu), 2),
                "roi": round(sum(lu) / len(lu), 3), "ic95_roi": [round(b[50], 3), round(b[1949], 3)]}
    return {"todas": rec(conferidas),
            "justa_pinnacle": rec([l for l in conferidas if l["fonte"] == "Pinnacle"]),
            "justa_modelo": rec([l for l in conferidas if l["fonte"] == "modelo"]),
            "destaque": rec([l for l in conferidas if l["destaque"]]),
            "sem_destaque": rec([l for l in conferidas if not l["destaque"]])}


def placar(d: pd.DataFrame, regs: list) -> dict:
    conf = []
    for r in ultimas(regs):
        g = ganhou(mapas_do_jogo(d, r), r.get("chave") or {})
        if g is None:
            continue
        conf.append({**r, "ganhou": g, "lucro": (r["odd"] - 1) if g else -1.0})
    return {"resumo": resumo(conf), "linhas": conf}


def carregar() -> list:
    if not SAIDA.exists():
        return []
    return [json.loads(t) for t in SAIDA.read_text(encoding="utf-8").splitlines() if t.strip()]


def registrar() -> int:
    """No robo: monta a lista como o app e acrescenta ao arquivo."""
    import apostas_cs as ap
    import precos_core as pc
    import rondas as rd
    odds = json.loads((RAIZ / "odds_cs2.json").read_text(encoding="utf-8"))

    def _le(nome):
        try:
            return json.loads((RAIZ / nome).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
    est = pc.Estado()
    tab = rd.Tabela(pc.KAPPA_ROUNDS)
    casas = _le("odds_casas_cs2.json")
    try:
        h = (pd.Timestamp.utcnow().tz_localize(None) - pd.Timestamp(casas["lido_em"]).tz_localize(None)).total_seconds() / 3600
        casas_jogos = casas.get("jogos", []) if h <= 36 else []
    except (KeyError, ValueError):
        casas_jogos = []
    jogos = pc.calcular(est, pc.montar_jogos(est, _le("agenda_cs.json"), odds, poly=_le("polymarket_cs.json")))
    c = []
    for j in jogos:
        if j.get("precificado"):
            c += ap.candidatos(j, pc.rounds_da_polymarket(j, tab),
                               pc.outras_casas(j, casas_jogos, est) if casas_jogos else None)
    agora = pd.Timestamp.utcnow().strftime("%Y-%m-%dT%H:%M:%S+00:00")
    novas = linhas_para_gravar(ap.melhores_nas_casas(c), agora)
    with SAIDA.open("a", encoding="utf-8") as f:
        for l in novas:
            f.write(json.dumps(l, ensure_ascii=False) + "\n")
    print(f"[apostas] {len(novas)} indicacoes gravadas ({len(c)} candidatas em {len(jogos)} jogos)")
    return 0


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    if "--registrar" in sys.argv:
        return registrar()
    import base_elo as be
    pl = placar(be.carregar(incluir_c=True), carregar())
    print(json.dumps(pl["resumo"], ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
