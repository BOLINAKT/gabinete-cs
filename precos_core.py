# -*- coding: utf-8 -*-
"""O CALCULO dos precos do dia, sem tela (26/10/2026): o app e o precificar_cs usam este.

Modelo oficial: Elo POR JOGADOR (elo_jogador.py) com nomes canonicos; forca =
media do elenco de hoje; serie com o p do mapa encolhido (C_SERIE). Pinnacle:
moneyline do jogo principal, periodo 0 = serie, 1..3 = mapa, margem tirada por
proporcao. Lado sem dado recente NAO e precificado.
"""
from __future__ import annotations

import difflib
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

import pandas as pd

import base_elo as be
import calibra_serie as cal
import elo_jogador as ej
import troca_elenco as te

RAIZ = Path(__file__).resolve().parent
APELIDOS = {"bb team": "BetBoom Team"}
# Sem isso o Elo de um time e o de 1500 da estreia (ou o de um elenco antigo de
# mesmo nome): numero sem base. Abaixo disso o lado NAO e precificado.
MIN_MAPAS_ANO, MAX_DIAS_PARADO = 30, 120
C_SERIE = 0.9   # validacao 26/10/2026; no mapa a calibracao nao passou
DIAS_TROCA_RECENTE = 60


def _n(s) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", s)


class Estado:
    """Tudo o que o modelo sabe ate o ultimo mapa coletado (caro: treinar uma vez)."""

    def __init__(self):
        self.d = be.carregar()
        self.el = te.carregar_elencos()
        self.r, self.pr = ej.rodar(self.d, self.el, ej.W_OFICIAL, ej.KJ_OFICIAL, estado=True)
        self.ult = {}
        for x in self.d.itertuples(index=False):
            self.ult[x.time1] = x.dt
            self.ult[x.time2] = x.dt
        self.fim = self.d.dt.max()
        self.desde = self.fim - pd.Timedelta(days=365)
        rec = self.d[self.d.dt >= self.desde]
        self.n_ano = pd.concat([rec.time1, rec.time2]).value_counts().to_dict()
        mapa = json.loads((RAIZ / "times_canonicos.json").read_text(encoding="utf-8"))
        self.idx = {}
        for cru in mapa:
            self.idx.setdefault(_n(cru), be.canonico(cru, mapa))
        for t in self.ult:
            self.idx[_n(t)] = t
        self.elencos = pd.read_csv(RAIZ / "elencos.csv", dtype=str).fillna("")

    def casar(self, nome):
        nome = APELIDOS.get(str(nome).lower(), nome)
        for chave in (_n(nome), _n("Team " + str(nome))):
            if chave in self.idx and self.idx[chave] in self.ult:
                return self.idx[chave], "exato"
        ativos = {_n(t): t for t, dt in self.ult.items() if dt >= self.desde}
        pref = [t for k, t in ativos.items() if k.startswith(_n(nome))]
        if len(pref) == 1:
            return pref[0], "comeco do nome"
        m = difflib.get_close_matches(_n(nome), list(ativos), n=1, cutoff=0.75)
        return (ativos[m[0]], "parecido") if m else (None, "sem time")

    def time(self, t, hoje):
        """Ficha do time: forca, elenco de hoje com a nota de cada um, trocas recentes."""
        if not t:
            return None
        e = te.elenco(self.el, t, hoje) or frozenset()
        g = self.elencos[self.elencos.time == t]
        jogs = []
        for j in sorted(e, key=lambda j: -self.pr.get(j, self.r[t])):
            ent = g[g.jogador == j].entrada.max() if not g.empty else ""
            novo = bool(ent) and (hoje - pd.Timestamp(ent)).days <= DIAS_TROCA_RECENTE
            jogs.append({"jogador": j, "nota": round(self.pr.get(j, self.r[t])), "entrou": ent,
                         "novo": novo, "visto": j in self.pr})
        parado = (self.fim - self.ult[t]).days if t in self.ult else None
        return {"time": t, "forca": round(ej.forca(t, hoje, self.r, self.pr, self.el)),
                "elo_time": round(self.r[t]), "mapas_ano": int(self.n_ano.get(t, 0)),
                "ultimo": self.ult[t].strftime("%d/%m/%y") if t in self.ult else "",
                "dias_parado": parado, "jogadores": jogs,
                "elenco_conhecido": 3 <= len(e) <= 7}


def justas(linhas, jogo):
    """{periodo: {'home': (p_justa, odd), 'away': (...)}} do jogo principal."""
    por = defaultdict(dict)
    for l in linhas:
        if l["matchup"] == jogo and l["tipo"] == "moneyline" and not l["alternativa"] and l["odd"]:
            por[l["periodo"]][l["lado"]] = l["odd"]
    fora = {}
    for per, v in por.items():
        if "home" in v and "away" in v:
            s = 1 / v["home"] + 1 / v["away"]
            fora[per] = {"home": ((1 / v["home"]) / s, v["home"]), "away": ((1 / v["away"]) / s, v["away"])}
    return fora


def calcular(est: Estado, odds: dict, hoje=None) -> list:
    """Pura sobre o Estado: um dict por jogo, com mercados e fichas dos dois times."""
    hoje = hoje if hoje is not None else pd.Timestamp.now().normalize()
    lido = pd.Timestamp(odds["lido_em"]).tz_localize(None)
    fora = []
    for j in sorted(odds["jogos"], key=lambda j: j.get("inicio_utc") or ""):
        tc, mc = est.casar(j["casa"])
        tf, mf = est.casar(j["fora"])
        ini = pd.Timestamp(j["inicio_utc"]).tz_localize(None) if j.get("inicio_utc") else None
        fc, ff = est.time(tc, hoje), est.time(tf, hoje)
        avisos = []
        for nome, t, f in ((j["casa"], tc, fc), (j["fora"], tf, ff)):
            if not t:
                avisos.append(f"{nome}: nao achei o time nos dados")
            elif f["mapas_ano"] < MIN_MAPAS_ANO or (f["dias_parado"] or 0) > MAX_DIAS_PARADO:
                avisos.append(f"{nome}: sem dado recente ({f['mapas_ano']} mapas no ano, ultimo {f['ultimo']})")
        jogo = {"id": j["id"], "liga": (j.get("liga") or "").replace("CS2 - ", ""), "casa": j["casa"],
                "fora": j["fora"], "bo": j.get("bo") or 3, "inicio_utc": j.get("inicio_utc"),
                "ja_comecou": bool(ini is not None and ini < lido), "casou": [(tc, mc), (tf, mf)],
                "fichas": [fc, ff], "precificado": not avisos, "avisos": avisos, "mercados": []}
        if not avisos:
            pm = 1 / (1 + 10 ** (-(fc["forca"] - ff["forca"]) / 400))
            precisa = {1: 1, 3: 2, 5: 3}.get(jogo["bo"], 2)
            ps = be.p_serie(cal.ajusta(pm, C_SERIE), precisa) if precisa > 1 else pm
            pin = justas(odds["linhas"], j["id"])
            merc = [("Série" if precisa > 1 else "Vencedor", 0, ps)]
            merc += [(f"Mapa {k}", k, pm) for k in (1, 2, 3) if k in pin]
            for nome, per, p in merc:
                pp = pin.get(per)
                lados = []
                for lado, pmod, chave in ((j["casa"], p, "home"), (j["fora"], 1 - p, "away")):
                    odd = pp[chave][1] if pp else None
                    lados.append({"lado": lado, "p_modelo": pmod, "odd_modelo": 1 / pmod,
                                  "p_pinnacle": pp[chave][0] if pp else None, "odd_pinnacle": odd,
                                  "vantagem": (pmod * odd - 1) * 100 if odd else None})
                jogo["mercados"].append({"mercado": nome, "periodo": per, "lados": lados})
        fora.append(jogo)
    return fora


def melhores(jogos, minimo=1.0, maximo=20.0) -> list:
    """Cada lado com vantagem entre minimo e maximo %, maior primeiro. Acima do
    maximo e quase sempre dado errado (time trocado, elenco novo), nao presente."""
    fora = []
    for j in jogos:
        if j["ja_comecou"]:
            continue
        for m in j["mercados"]:
            for l in m["lados"]:
                v = l["vantagem"]
                if v is not None and minimo <= v <= maximo:
                    fora.append({**l, "mercado": m["mercado"], "jogo": j})
    return sorted(fora, key=lambda x: -x["vantagem"])
