# -*- coding: utf-8 -*-
"""Odd justa do modelo x Pinnacle sem margem, para os jogos que o robo coletou (26/10/2026).

Modelo oficial: Elo POR JOGADOR (elo_jogador.py, aceito 26/10/2026), nomes canonicos,
treinado em TODOS os mapas ate o ultimo dado; forca = media do elenco de HOJE.
Serie: p do mapa encolhido (C_SERIE, calibra_serie.py) antes de p_serie -- os
mapas nao sao independentes e a serie sem isso sai otimista com o favorito. Serie: be.p_serie (mapas independentes).
Pinnacle: moneyline do jogo principal, periodo 0 = serie, 1..3 = mapa; margem
tirada por proporcao (1/odd normalizado).

Nomes Pinnacle -> Liquipedia: exato na pagina do time, no nome curto, com "Team "
na frente, e por ultimo o mais parecido entre os times ativos no ultimo ano;
APELIDOS abaixo para o que nao bate. O casamento aparece na tela para conferir.
"""
from __future__ import annotations

import difflib
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

import pandas as pd

import base_elo as be
import calibra_serie as cal
import elo_jogador as ej
import troca_elenco as te

K = 24
RAIZ = Path(__file__).resolve().parent
# Sem isso o Elo de um time e o de 1500 da estreia (ou o de um elenco antigo de
# mesmo nome): numero sem base. Abaixo disso o lado NAO e precificado.
MIN_MAPAS_ANO, MAX_DIAS_PARADO = 30, 120
C_SERIE = 0.9   # validacao 26/10/2026; no mapa a calibracao nao passou
APELIDOS = {"bb team": "BetBoom Team"}


def _n(s) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", s)


def treinar(d):
    r, n, ult = defaultdict(lambda: 1500.0), defaultdict(int), {}
    for x in d.itertuples(index=False):
        a, b = x.time1, x.time2
        p = 1 / (1 + 10 ** (-(r[a] - r[b]) / 400))
        y = 1 if x.vencedor == 1 else 0
        r[a] += K * (y - p)
        r[b] -= K * (y - p)
        for t in (a, b):
            n[t] += 1
            ult[t] = x.dt
    return r, n, ult


def indice(d, ult):
    mapa = json.loads((RAIZ / "times_canonicos.json").read_text(encoding="utf-8"))
    idx = {}
    for cru, can in mapa.items():
        c = be.canonico(cru, mapa)
        idx.setdefault(_n(cru), c)
    for t in ult:
        idx[_n(t)] = t
    return idx


def casar(nome, idx, ult, desde):
    nome = APELIDOS.get(str(nome).lower(), nome)
    for chave in (_n(nome), _n("Team " + str(nome))):
        if chave in idx and idx[chave] in ult:
            return idx[chave], "exato"
    ativos = {_n(t): t for t, dt in ult.items() if dt >= desde}
    pref = [t for k, t in ativos.items() if k.startswith(_n(nome))]
    if len(pref) == 1:
        return pref[0], "comeco do nome"
    m = difflib.get_close_matches(_n(nome), list(ativos), n=1, cutoff=0.75)
    return (ativos[m[0]], "parecido") if m else (None, "sem time")


def justas(linhas, jogo):
    """{periodo: (p_casa, p_fora)} sem margem, do jogo principal."""
    por = defaultdict(dict)
    for l in linhas:
        if l["matchup"] == jogo and l["tipo"] == "moneyline" and not l["alternativa"] and l["odd"]:
            por[l["periodo"]][l["lado"]] = 1 / l["odd"]
    fora = {}
    for per, v in por.items():
        if "home" in v and "away" in v:
            s = v["home"] + v["away"]
            fora[per] = (v["home"] / s, v["away"] / s)
    return fora


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    d = be.carregar()
    _, n, ult = treinar(d)
    el = te.carregar_elencos()
    r_t, pr = ej.rodar(d, el, ej.W_OFICIAL, ej.KJ_OFICIAL, estado=True)
    hoje = pd.Timestamp.now().normalize()
    idx = indice(d, ult)
    desde = d.dt.max() - pd.Timedelta(days=365)
    rec = d[d.dt >= desde]
    n_ano = pd.concat([rec.time1, rec.time2]).value_counts().to_dict()
    od = json.loads((RAIZ / "odds_cs2.json").read_text(encoding="utf-8"))
    lido = pd.Timestamp(od["lido_em"]).tz_localize(None)
    print(f"dados ate {d.dt.max():%d/%m %H:%M} · odds lidas {lido:%d/%m %H:%M} UTC\n")
    saida = []
    for j in sorted(od["jogos"], key=lambda j: j["inicio_utc"] or ""):
        tc, mc = casar(j["casa"], idx, ult, desde)
        tf, mf = casar(j["fora"], idx, ult, desde)
        ini = pd.Timestamp(j["inicio_utc"]).tz_localize(None) if j["inicio_utc"] else None
        aviso = " (JA TINHA COMECADO na leitura)" if ini is not None and ini < lido else ""
        print(f"{j['casa']} x {j['fora']} · {j['liga']} · BO{j['bo'] or '?'} · {ini:%d/%m %H:%M} UTC{aviso}")
        print(f"   casou: {j['casa']} -> {tc} ({mc}, {n_ano.get(tc, 0)} mapas no ano, ultimo {ult[tc]:%d/%m/%y})" if tc else
              f"   casou: {j['casa']} -> NADA")
        print(f"          {j['fora']} -> {tf} ({mf}, {n_ano.get(tf, 0)} mapas no ano, ultimo {ult[tf]:%d/%m/%y})" if tf else
              f"          {j['fora']} -> NADA")
        fracos = [nome for nome, t in ((j["casa"], tc), (j["fora"], tf))
                  if not t or n_ano.get(t, 0) < MIN_MAPAS_ANO or (d.dt.max() - ult[t]).days > MAX_DIAS_PARADO]
        if fracos:
            print(f"   NAO PRECIFICADO: sem dado recente de {', '.join(fracos)} "
                  f"(precisa de {MIN_MAPAS_ANO}+ mapas no ano e jogo nos ultimos {MAX_DIAS_PARADO} dias)\n")
            continue
        fc, ff = ej.forca(tc, hoje, r_t, pr, el), ej.forca(tf, hoje, r_t, pr, el)
        pm = 1 / (1 + 10 ** (-(fc - ff) / 400))
        precisa = {1: 1, 3: 2, 5: 3}.get(j["bo"] or 3, 2)
        ps = be.p_serie(cal.ajusta(pm, C_SERIE), precisa)
        pin = justas(od["linhas"], j["id"])
        lin = [("serie", ps, pin.get(0))] + [(f"mapa {k}", pm, pin.get(k)) for k in (1, 2, 3) if k in pin]
        for nome, p, pp in lin:
            txt = f"   {nome:7s} modelo {j['casa']} {p:5.1%} (odd {1/p:5.2f}) x {j['fora']} {1-p:5.1%} (odd {1/(1-p):5.2f})"
            if pp:
                txt += f"  | Pinnacle justa {pp[0]:5.1%} x {pp[1]:5.1%}  dif {100*(p-pp[0]):+5.1f} pp"
            print(txt)
            saida.append({"jogo": j["id"], "casa": j["casa"], "fora": j["fora"], "mercado": nome,
                          "p_modelo_casa": round(p, 4), "p_pinnacle_casa": round(pp[0], 4) if pp else None})
        print()
    (RAIZ / "precos_cs2.json").write_text(json.dumps({"lido_em": od["lido_em"], "precos": saida},
                                                     ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
