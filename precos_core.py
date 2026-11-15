# -*- coding: utf-8 -*-
"""O CALCULO dos precos do dia, sem tela (26/10/2026): o app e o precificar_cs usam este.

Modelo oficial: Elo POR JOGADOR (elo_jogador.py) com nomes canonicos; forca =
media do elenco de hoje; serie com o p do mapa encolhido (c movel, calibra_movel). Pinnacle:
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
import calibra_movel as cm
import serie_cs as sc
import calibra_serie as cal
import elo_jogador as ej
import troca_elenco as te

RAIZ = Path(__file__).resolve().parent
# "sinners" (15/11/2026): a Pinnacle escreve "SINNERS" e existe um "Sinners" parado desde 2020;
# o time de hoje e o SINNERS Esports.
APELIDOS = {"bb team": "BetBoom Team", "sinners": "SINNERS Esports"}
# Time casado mas PARADO ha mais de um ano: quase sempre homonimo antigo, nao o time de hoje.
MAX_DIAS_SEM_JOGO = 365
# Sem isso o Elo de um time e o de 1500 da estreia (ou o de um elenco antigo de
# mesmo nome): numero sem base. Abaixo disso o lado NAO e precificado.
MIN_MAPAS_ANO, MAX_DIAS_PARADO = 30, 120
# Serie: c MOVEL (calibra_movel.py, aceito 26/10/2026 a noite): o melhor nos 12
# meses anteriores; o fixo (0,9) foi escolhido com a regua de tiers misturados.
DIAS_TROCA_RECENTE = 60
# Tabela de MAPAS so com CS2 (26/10/2026, pergunta dele): mapas refeitos no CS2 e
# rounds do CS:GO (MR15) nao comparam com MR12. O Elo segue com o historico todo:
# treinar so com CS2 piorou o teste 2024+ em -0,014 (habilidade atravessa a troca).
INICIO_CS2 = pd.Timestamp("2023-09-27")


def _n(s) -> str:
    cru = str(s)
    s = unicodedata.normalize("NFKD", cru).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9]", "", s)
    # 15/11/2026: nome so em chines/cirilico virava a chave VAZIA e todos esses times colidiam
    # (e um nome qualquer sem letra latina casava com o ultimo deles). Sem ASCII: o proprio nome.
    return s if s else "~" + re.sub(r"\s+", "", cru.lower())


class Estado:
    """Tudo o que o modelo sabe ate o ultimo mapa coletado (caro: treinar uma vez)."""

    def __init__(self):
        # FASE 3 (15/11/2026): treina com o tier C tambem. Medido: a regua S/A/B nao piora (mapa
        # 2025+ +0,0012 [-0,0002; +0,0027], 2026 +0,0025) e os times de tier C passam a ter nota.
        self.d = be.carregar(incluir_c=True)
        self.el = te.carregar_elencos()
        self.r, self.pr = ej.rodar(self.d, self.el, ej.W_OFICIAL, ej.KJ_OFICIAL, estado=True)
        _, series = ej.rodar(self.d, self.el, ej.W_OFICIAL, ej.KJ_OFICIAL)
        self.c_serie = cm.c_serie_atual(series, self.d.dt.max() + pd.Timedelta(days=1))
        # a forma do dia (Fase 2, 12/11/2026): kappa movel, ver serie_cs.py
        try:
            self.kappa_serie = sc.kappa_atual(series, self.d.dt.max() + pd.Timedelta(days=1), self.c_serie)
        except Exception:
            self.kappa_serie = None
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
        # 15/11/2026: "Heroic" (americano, parado em 2023) e "HEROIC" (o de hoje) viram a mesma chave;
        # ganhava o ultimo da lista e a Pinnacle "HEROIC" casava com o time morto. Agora, em nomes que
        # so diferem por caixa/acento, ganha quem jogou por ultimo.
        for t in sorted(self.ult, key=lambda t: self.ult[t]):
            self.idx[_n(t)] = t
        self.elencos = pd.read_csv(RAIZ / "elencos.csv", dtype=str).fillna("")
        # mapas: o POOL sai dos dados (>= 5% dos mapas dos ultimos 120 dias), nao
        # de lista fixa -- acompanha a proxima troca de mapa da Valve sozinho.
        rec = self.d[self.d.dt >= self.fim - pd.Timedelta(days=120)]
        freq = rec.mapa.value_counts(normalize=True)
        self.pool = list(freq[freq >= 0.05].index)
        # por_mapa: historico todo (o ajuste "sabendo o mapa" foi validado assim);
        # por_mapa_cs2: so CS2, para a TABELA que ele le.
        self.por_mapa = defaultdict(list)          # (time, mapa) -> [(dt, venceu, rounds +/-)]
        self.por_mapa_cs2 = defaultdict(list)
        for x in self.d.itertuples(index=False):
            v1 = 1 if x.vencedor == 1 else 0
            for alvo in ((self.por_mapa, self.por_mapa_cs2) if x.dt >= INICIO_CS2 else (self.por_mapa,)):
                alvo[(x.time1, x.mapa)].append((x.dt, v1, x.rounds1 - x.rounds2))
                alvo[(x.time2, x.mapa)].append((x.dt, 1 - v1, x.rounds2 - x.rounds1))

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
                "elenco_conhecido": 3 <= len(e) <= 7, "recentes": self.recentes(t)}

    def recentes(self, t, n=5) -> list:
        """As ultimas n SERIES do time nos nossos dados, com a fonte para conferir:
        pagina da Liquipedia e partida no HLTV (numero que a propria Liquipedia guarda).
        E a prova do "ultimo jogo" e do "parado ha X dias" (26/10/2026, pergunta dele)."""
        g = self.d[(self.d.time1 == t) | (self.d.time2 == t)]
        if g.empty:
            return []
        fora = []
        for (pag, data, t1, t2), s in list(g.groupby(["pagina", "data", "time1", "time2"], sort=False))[-60:]:
            eu1 = t1 == t
            v = int(((s.vencedor == 1) == eu1).sum())
            hl = str(s.hltv.iloc[0]).split(".")[0].strip()
            fora.append({"dt": s.dt.iloc[0], "data": s.dt.iloc[0].strftime("%d/%m/%y"),
                         "adversario": t2 if eu1 else t1, "placar": f"{v}-{len(s) - v}",
                         "pagina": pag, "tier": s.tier.iloc[0],
                         "hltv": hl if hl.isdigit() else ""})
        return sorted(fora, key=lambda x: x["dt"], reverse=True)[:n]


JANELAS = (5, 10, 20)


def mapas_do_time(est: Estado, t, hoje) -> dict:
    """{mapa: {'w5': (vit, jogos), 'w10', 'w20', 'ano', 'saldo10', 'ultimo', 'parte'}} no pool atual,
    SO jogos de CS2.

    'parte' = fracao dos mapas do time nos ultimos 180 dias que foram ESTE mapa:
    muito alta sugere pick; zero com o time ativo sugere ban permanente."""
    if not t:
        return {}
    meio_ano = hoje - pd.Timedelta(days=180)
    tot6 = sum(1 for m in est.pool for dt, _, _ in est.por_mapa_cs2.get((t, m), []) if dt >= meio_ano)
    fora = {}
    for m in est.pool:
        h = est.por_mapa_cs2.get((t, m), [])
        f = {}
        for n in JANELAS:
            u = h[-n:]
            f[f"w{n}"] = (sum(v for _, v, _ in u), len(u))
        ano = [v for dt, v, _ in h if dt >= hoje - pd.Timedelta(days=365)]
        f["ano"] = (sum(ano), len(ano))
        u10 = h[-10:]
        f["saldo10"] = sum(s for _, _, s in u10) / len(u10) if u10 else None
        f["ultimo"] = h[-1][0].strftime("%d/%m/%y") if h else ""
        f["parte"] = (sum(1 for dt, _, _ in h if dt >= meio_ano) / tot6) if tot6 else 0.0
        fora[m] = f
    return fora


def veto_provavel(ma: dict, mb: dict) -> dict:
    """Leitura simples do veto: cada time tende a BANIR o que menos joga e a
    PICKAR o que mais joga (ultimos 180 dias). So um palpite para olhar a
    tabela -- o veto real sai minutos antes do jogo."""
    def ordem(mx):
        return sorted(mx, key=lambda m: mx[m]["parte"])
    if not ma or not mb:
        return {}
    oa, ob = ordem(ma), ordem(mb)
    return {"ban_a": oa[0], "ban_b": ob[0], "pick_a": oa[-1], "pick_b": ob[-1]}


def e_qualificatoria(jogo_liga: str) -> bool:
    return any(p in (jogo_liga or "").lower() for p in ("qualifier", "qualif", "open", "closed"))


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


HORAS_DE_JOGO = 3    # depois disso o jogo conta como encerrado (BO3 longo ~2h30)


def situacao(inicio_utc, agora=None) -> str:
    """'a jogar' | 'ao vivo' | 'encerrado', pelo relogio de AGORA (nao o da leitura)."""
    if not inicio_utc:
        return "a jogar"
    agora = agora if agora is not None else pd.Timestamp.utcnow().tz_localize(None)
    ini = pd.Timestamp(inicio_utc).tz_localize(None)
    if agora < ini:
        return "a jogar"
    return "ao vivo" if agora < ini + pd.Timedelta(hours=HORAS_DE_JOGO) else "encerrado"


JANELA_CASAR_H = 8   # Pinnacle x Liquipedia: mesma dupla, inicio a ate 8 h (fuso/atraso)


def _nome_torneio(pagina: str) -> str:
    return str(pagina).replace("_", " ").replace("/", " · ")


def casar_estrito(est: Estado, nome: str, mapa: dict = None):
    """So nome exato ou apelido/canonico conhecido -- nada de "parecido". 29/10/2026: na
    Polymarket "DimoniX Esports" casava com "Diamant Esports" (difflib 0,75) e herdava o preco
    de outro time. Para os times pequenos que so a Polymarket lista, na duvida: sem time."""
    t, modo = est.casar(nome)
    if t and modo == "exato":
        return t
    # 15/11/2026: "Luminosity" = "Luminosity Gaming", "Prestige" = "Prestige Esport". Comeco do nome
    # com UM unico time ativo e nome de 5+ letras e seguro (o erro de 29/10 era o "parecido").
    if t and modo == "comeco do nome" and len(_n(nome)) >= 5:
        return t
    if mapa:
        c = be.canonico(nome, mapa)
        if c:
            t2, modo2 = est.casar(c)
            if t2 and modo2 == "exato":
                return t2
    return None


def montar_jogos(est: Estado, agenda: dict, odds: dict, agora=None, dias: int = 3, poly: dict = None) -> dict:
    """Os jogos VEM DA LIQUIPEDIA e as odds da Pinnacle entram quando ela abrir o
    mercado (27/10/2026, pedido dele). Devolve no formato das odds ({lido_em, jogos,
    linhas}) para o calcular() de sempre:
      - jogo da agenda COM jogo da Pinnacle (mesma dupla, ate JANELA_CASAR_H): usa o
        da Pinnacle (id e casa/fora dela -- e assim que as odds batem);
      - jogo da agenda SEM Pinnacle: entra sem odd ("lp-..."), so com o preco do modelo;
      - jogo da Pinnacle fora da agenda (ex.: torneio tier C): entra como antes;
      - jogo SO da Polymarket (29/10/2026, ele: "talvez pegar os jogos da polymarket? ja que
        ela pega todos os jogos" -- ex.: Aurora Young Blud x DimoniX): entra com o preco
        dela; se o modelo nao conhece os times, aparece sem preco do modelo e avisa."""
    agora = agora if agora is not None else pd.Timestamp.utcnow().tz_localize(None)
    mapa = json.loads((RAIZ / "times_canonicos.json").read_text(encoding="utf-8"))
    pin = list(odds.get("jogos") or [])
    casados = {pg["id"]: frozenset(t for t, _ in (est.casar(pg["casa"]), est.casar(pg["fora"])) if t) for pg in pin}
    usados, fora = set(), []
    for a in (agenda or {}).get("jogos", []):
        ini = pd.Timestamp(a["inicio_utc"]).tz_localize(None)
        if not (agora - pd.Timedelta(hours=4) <= ini <= agora + pd.Timedelta(days=dias)):
            continue
        ta, tb = be.canonico(a["time1"], mapa), be.canonico(a["time2"], mapa)
        par = frozenset((ta, tb))
        g = next((pg for pg in pin if pg["id"] not in usados and casados[pg["id"]] == par and pg.get("inicio_utc")
                  and abs(pd.Timestamp(pg["inicio_utc"]).tz_localize(None) - ini) <= pd.Timedelta(hours=JANELA_CASAR_H)),
                 None)
        if g:
            usados.add(g["id"])
            fora.append({**g, "fonte": "liquipedia+pinnacle"})
        else:
            fora.append({"id": f"lp-{a['pagina']}-{a['time1']}-{a['time2']}-{a['inicio_utc']}",
                         "liga": _nome_torneio(a["pagina"]), "casa": ta, "fora": tb, "bo": a.get("bo") or 3,
                         "inicio_utc": a["inicio_utc"], "fonte": "liquipedia"})
    fora += [{**pg, "fonte": "pinnacle"} for pg in pin if pg["id"] not in usados]

    def _chave(nome):
        return casar_estrito(est, nome, mapa) or be.canonico(nome, mapa) or str(nome).strip().lower()

    def _ts(x):
        t = pd.Timestamp(x)
        return t.tz_convert(None) if t.tzinfo is not None else t
    for p in (poly or {}).get("partidas", []):
        if not p.get("inicio_utc"):
            continue
        ini = _ts(p["inicio_utc"])
        if not (agora - pd.Timedelta(hours=4) <= ini <= agora + pd.Timedelta(days=dias)):
            continue
        par = frozenset((_chave(p["time_a"]), _chave(p["time_b"])))
        dono = next((j for j in fora if j.get("inicio_utc")
                     and frozenset((_chave(j["casa"]), _chave(j["fora"]))) == par
                     and abs(_ts(j["inicio_utc"]) - ini) <= pd.Timedelta(hours=JANELA_CASAR_H)), None)
        info = {"p_a": p.get("p_a"), "p_b": p.get("p_b"), "time_a": p["time_a"], "time_b": p["time_b"],
                "spread": p.get("spread"), "liquidez": p.get("liquidez"), "mercados": p.get("mercados") or []}
        if dono is None:
            # 10/11/2026: a Polymarket escreve "Toobisie" e a Liquipedia "Teletubisie" -- o jogo
            # aparecia duas vezes. Um time nao joga duas partidas ao mesmo tempo: se UM lado bate
            # exato e o horario e o mesmo (ate 1 h), e o mesmo jogo -- desde que so haja um.
            ka, kb = _chave(p["time_a"]), _chave(p["time_b"])
            cands = [j for j in fora if j.get("inicio_utc") and not j.get("poly")
                     and abs(_ts(j["inicio_utc"]) - ini) <= pd.Timedelta(hours=1)
                     and len({ka, kb} & {_chave(j["casa"]), _chave(j["fora"])}) == 1]
            if len(cands) == 1:
                dono = cands[0]
                lado_a_casa = ka == _chave(dono["casa"]) or kb == _chave(dono["fora"])
                dono["poly"] = dict(info, invertido=not lado_a_casa)
                # o lado que o modelo nao conhece herda o nome que ele conhece (a Pinnacle diz
                # "Toobisie", a Polymarket "Teletubisie"); as odds casam pelo id, nao pelo nome
                pares = (("casa", p["time_a"]), ("fora", p["time_b"])) if lado_a_casa else \
                        (("casa", p["time_b"]), ("fora", p["time_a"]))
                for lado, nome_p in pares:
                    conhecido = casar_estrito(est, nome_p, mapa)
                    if conhecido and not casar_estrito(est, dono[lado], mapa):
                        dono[lado] = conhecido
                continue
        if dono is not None:
            # a orientacao: o time_a da Polymarket e a casa ou a fora deste jogo?
            dono.setdefault("poly", dict(info, invertido=_chave(p["time_a"]) != _chave(dono["casa"])))
            continue
        info["invertido"] = False
        ta = casar_estrito(est, p["time_a"], mapa) or p["time_a"].strip()
        tb = casar_estrito(est, p["time_b"], mapa) or p["time_b"].strip()
        fora.append({"id": f"pm-{p.get('evento') or (p['time_a'] + '-' + p['time_b'])}",
                     "liga": p.get("torneio") or "", "casa": ta, "fora": tb, "bo": p.get("bo") or 3,
                     "inicio_utc": p["inicio_utc"], "fonte": "polymarket", "poly": info, "estrito": True})
    return {"lido_em": odds.get("lido_em") or agora.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "jogos": fora, "linhas": odds.get("linhas") or []}


def calcular(est: Estado, odds: dict, hoje=None, agora=None) -> list:
    """Pura sobre o Estado: um dict por jogo, com mercados e fichas dos dois times."""
    hoje = hoje if hoje is not None else pd.Timestamp.now().normalize()
    lido = pd.Timestamp(odds["lido_em"]).tz_localize(None)
    fora = []
    for j in sorted(odds["jogos"], key=lambda j: j.get("inicio_utc") or ""):
        if j.get("estrito"):          # jogo so da Polymarket: sem casar por "parecido"
            tc, tf = casar_estrito(est, j["casa"]), casar_estrito(est, j["fora"])
            mc = "exato" if tc else "sem time"
            mf = "exato" if tf else "sem time"
        else:
            tc, mc = est.casar(j["casa"])
            tf, mf = est.casar(j["fora"])
        ini = pd.Timestamp(j["inicio_utc"]).tz_localize(None) if j.get("inicio_utc") else None
        fc, ff = est.time(tc, hoje), est.time(tf, hoje)
        # FASE 3 (15/11/2026): time com POUCO DADO deixa de ser recusado. Medido no cego 2025+
        # (pouco_dado.py, todos os tiers): o modelo ganha da moeda nesses jogos tanto ou mais que
        # nos outros (estreia +0,045, 1-9 mapas +0,050, 10-29 +0,056; 30+ +0,035) e sem precisar
        # encolher a chance (c ~ 1,0). So "nao achei o time" continua sem preco.
        avisos, pouco = [], []
        for nome, t, f in ((j["casa"], tc, fc), (j["fora"], tf, ff)):
            if not t:
                avisos.append(f"{nome}: nao achei o time nos dados")
            elif (f["dias_parado"] or 0) > MAX_DIAS_SEM_JOGO:
                avisos.append(f"{nome}: o time com esse nome nos dados ({t}) nao joga desde {f['ultimo']} — "
                              "provavel homonimo antigo, sem preco")
            elif f["mapas_ano"] < MIN_MAPAS_ANO or (f["dias_parado"] or 0) > MAX_DIAS_PARADO:
                pouco.append(f"{nome}: pouco dado recente ({f['mapas_ano']} mapas no ano, ultimo {f['ultimo']})")
        jogo = {"id": j["id"], "liga": (j.get("liga") or "").replace("CS2 - ", ""), "casa": j["casa"],
                "fora": j["fora"], "bo": j.get("bo") or 3, "inicio_utc": j.get("inicio_utc"),
                "ja_comecou": bool(ini is not None and ini < lido), "casou": [(tc, mc), (tf, mf)],
                "situacao": situacao(j.get("inicio_utc"), agora),
                "fonte": j.get("fonte", "pinnacle"), "poly": j.get("poly"),
                "fichas": [fc, ff], "precificado": not avisos, "avisos": avisos, "pouco_dado": pouco,
                "mercados": [],
                "mapas": [mapas_do_time(est, tc, hoje), mapas_do_time(est, tf, hoje)],
                "qualificatoria": e_qualificatoria(j.get("liga") or "")}
        jogo["veto"] = veto_provavel(*jogo["mapas"])
        if not avisos:
            pm = 1 / (1 + 10 ** (-(fc["forca"] - ff["forca"]) / 400))
            jogo["p_mapa"] = pm
            precisa = {1: 1, 3: 2, 5: 3}.get(jogo["bo"], 2)
            c_jogo = 1.0 if pouco else est.c_serie       # pouco dado: sem o encolhimento dos S/A/B
            ps = be.p_serie(cal.ajusta(pm, c_jogo), precisa) if precisa > 1 else pm
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
            # handicap/total de mapas e placar exato, coerentes com a serie (Fase 2, 12/11/2026)
            jogo["mercados_serie"] = sc.mercados_da_serie(ps, jogo["bo"], getattr(est, "kappa_serie", None),
                                                          odds["linhas"], j["id"], j["casa"], j["fora"])
            sc.anexar_polymarket(jogo["mercados_serie"], j.get("poly"))
        fora.append(jogo)
    return fora


KAPPA_ROUNDS = 25   # rondas.py, validacao 26/10/2026


def p_linha_rounds(dist: dict, tipo: str, lado: str, pontos: float, time: str | None) -> float | None:
    """Chance do modelo para UMA linha de rounds (A = casa). dist = {(rounds A, rounds B): p}."""
    def pr(f):
        return sum(v for (a, b), v in dist.items() if f(a, b))
    if pontos is None:
        return None
    if tipo == "total":
        acima = pr(lambda a, b: a + b > pontos)
        return acima if lado == "over" else 1 - acima if lado == "under" else None
    if tipo == "spread":     # pontos = handicap do lado: casa -2,5 => vence por 3+
        if lado == "home":
            return pr(lambda a, b: a - b + pontos > 0)
        if lado == "away":
            return pr(lambda a, b: b - a + pontos > 0)
    if tipo == "team_total" and time in ("home", "away"):
        acima = pr(lambda a, b: (a if time == "home" else b) > pontos)
        return acima if lado == "over" else 1 - acima if lado == "under" else None
    return None


def rounds_do_jogo(jogo: dict, linhas: list, tabela) -> list:
    """Cada linha de rounds da Pinnacle (por mapa) com a chance do modelo e a vantagem.

    A distribuicao do placar vem da chance do mapa (o modelo oficial) via rondas.Tabela.
    Validado 26/10: handicap e rounds de um time PASSAM; total e prorrogacao empatam
    com a frequencia historica (o modelo nao sabe prever total melhor que a media)."""
    if not jogo["precificado"] or jogo.get("p_mapa") is None:
        return []
    dist = tabela.dist(jogo["p_mapa"])
    grupos = defaultdict(list)
    for l in linhas:
        if l["matchup"] == jogo["id"] and l["tipo"] in ("total", "spread", "team_total")                 and l["periodo"] in (1, 2, 3) and l["odd"]:
            # par = as duas pontas da MESMA linha: no handicap, casa h com visitante -h
            # ("casa -2,5 / fora +2,5" nao se mistura com a alternativa "casa +2,5 / fora -2,5")
            h = (l["pontos"] or 0) * (-1 if (l["tipo"] == "spread" and l["lado"] == "away") else 1)
            grupos[(l["periodo"], l["tipo"], l.get("time"), h, l["alternativa"])].append(l)
    fora = []
    for (per, tipo, time, _, _), ls in sorted(grupos.items(), key=lambda x: (x[0][0], x[0][1], str(x[0][2]), x[0][3])):
        if len(ls) != 2:
            continue
        s = sum(1 / l["odd"] for l in ls)
        for l in ls:
            pm = p_linha_rounds(dist, tipo, l["lado"], l["pontos"], time)
            if pm is None:
                continue
            fora.append({"mapa": per, "tipo": tipo, "time": time, "lado": l["lado"], "pontos": l["pontos"],
                         "alternativa": l["alternativa"], "odd": l["odd"], "p_pinnacle": (1 / l["odd"]) / s,
                         "p_modelo": pm, "vantagem": (pm * l["odd"] - 1) * 100,
                         "validado": tipo in ("spread", "team_total")})
    return fora


def rounds_da_polymarket(jogo: dict, tabela) -> list:
    """As linhas de rounds da POLYMARKET (handicap e total por mapa) no mesmo formato de
    rounds_do_jogo, com a odd de COMPRA (15/11/2026, Fase 1/5). Livro vazio fica de fora."""
    pm = jogo.get("poly") or {}
    if not jogo.get("precificado") or jogo.get("p_mapa") is None or not pm.get("mercados"):
        return []
    dist = tabela.dist(jogo["p_mapa"])
    inv = bool(pm.get("invertido"))
    fora = []
    for m in pm["mercados"]:
        tipo = str(m.get("tipo") or "")
        od = sc.odds_de_compra(m)
        if not od or m.get("linha") is None or len(m.get("lados") or []) != 2:
            continue
        try:
            mapa = int(tipo.rsplit("_", 1)[1])
        except (IndexError, ValueError):
            continue
        if tipo.startswith("round_handicap_game_"):
            primeiro_e_casa = (str(m["lados"][0]) == str(pm.get("time_a"))) != inv
            h_casa = float(m["linha"]) if primeiro_e_casa else -float(m["linha"])
            pares = (("spread", "home", h_casa, od[0] if primeiro_e_casa else od[1]),
                     ("spread", "away", -h_casa, od[1] if primeiro_e_casa else od[0]))
        elif tipo.startswith("round_over_under_game_"):
            over_primeiro = str(m["lados"][0]).lower() == "over"
            pares = (("total", "over", float(m["linha"]), od[0] if over_primeiro else od[1]),
                     ("total", "under", float(m["linha"]), od[1] if over_primeiro else od[0]))
        else:
            continue
        for tp, lado, pontos, odd in pares:
            p = p_linha_rounds(dist, tp, lado, pontos, None)
            if p is None:
                continue
            fora.append({"mapa": mapa, "tipo": tp, "time": None, "lado": lado, "pontos": pontos,
                         "alternativa": False, "odd": odd, "p_pinnacle": None, "p_modelo": p,
                         "vantagem": (p * odd - 1) * 100, "validado": tp == "spread", "casa": "Polymarket"})
    return fora


def melhores(jogos, minimo=1.0, maximo=20.0) -> list:
    """Cada lado com vantagem entre minimo e maximo %, maior primeiro. Acima do
    maximo e quase sempre dado errado (time trocado, elenco novo), nao presente."""
    fora = []
    for j in jogos:
        if j["ja_comecou"] or j.get("situacao", "a jogar") != "a jogar":
            continue
        for m in j["mercados"]:
            for l in m["lados"]:
                v = l["vantagem"]
                if v is not None and minimo <= v <= maximo:
                    fora.append({**l, "mercado": m["mercado"], "jogo": j})
    return sorted(fora, key=lambda x: -x["vantagem"])


# ---- OUTRAS CASAS (OddsPapi, 27/10/2026) -----------------------------------------
# A Pinnacle e a REGUA (preco justo); o valor esta nas casas moles. Para cada casa
# DELE, a versao brasileira (".bet.br") se existir, senao a principal.
MARCAS = (("pinnacle", "Pinnacle"), ("bet365", "bet365"), ("superbet", "Superbet"),
          ("polymarket", "Polymarket"), ("estrelabet", "Estrela Bet"), ("blaze", "Blaze"),
          ("betano", "Betano"), ("stake", "Stake"))
MERCADO_PERIODO = {"171": 0, "1747": 1, "1749": 2, "1751": 3}


def _versao_da_marca(casas: dict, marca: str):
    for slug in (f"{marca}.bet.br", marca):
        if slug in casas:
            return slug
    return None


def outras_casas(jogo: dict, casas_jogos: list, est: Estado) -> list:
    """Linhas {mercado, periodo, casa, odd_casa, odd_fora, valor_pin_*, valor_mod_*} do
    jogo do app (orientacao casa/fora DELE), casando o jogo da OddsPapi pela dupla e hora."""
    if not jogo.get("inicio_utc"):
        return []
    ini = pd.Timestamp(jogo["inicio_utc"]).tz_localize(None)
    ta, tb = jogo["casou"][0][0], jogo["casou"][1][0]
    if not (ta and tb):
        return []
    alvo = None
    for g in casas_jogos:
        if not g.get("inicio_utc"):
            continue
        t1, t2 = est.casar(g["time1"])[0], est.casar(g["time2"])[0]
        if {t1, t2} == {ta, tb} and abs(pd.Timestamp(g["inicio_utc"]).tz_localize(None) - ini) <= pd.Timedelta(hours=8):
            alvo, invertido = g, (t1 == tb)
            break
    if alvo is None:
        return []
    merc = {m["periodo"]: m for m in jogo["mercados"]}
    fora = []
    for mid, per in MERCADO_PERIODO.items():
        # preco justo da Pinnacle DO MESMO INSTANTE das outras casas (a da propria
        # OddsPapi); a do nosso robo so na falta -- momentos diferentes inventam valor
        m = merc.get(per)
        p_pin = None
        if "pinnacle" in alvo["casas"] and mid in alvo["casas"]["pinnacle"]:
            o1, o2 = alvo["casas"]["pinnacle"][mid][::-1] if invertido else alvo["casas"]["pinnacle"][mid]
            p_pin = (1 / o1) / (1 / o1 + 1 / o2)
        elif m:
            p_pin = m["lados"][0]["p_pinnacle"]
        p_mod = m["lados"][0]["p_modelo"] if m else None
        for marca, nome in MARCAS:
            slug = _versao_da_marca(alvo["casas"], marca)
            if not slug or mid not in alvo["casas"][slug]:
                continue
            o1, o2 = alvo["casas"][slug][mid][::-1] if invertido else alvo["casas"][slug][mid]
            if 1 / o1 + 1 / o2 > 1.15:
                # cotacao furada (28/10/2026: Polymarket 1,85 x 1,04 = 150%, livro vazio de
                # um lado); casa de verdade fica em 100-108%
                continue
            lin = {"mercado": "Série" if per == 0 else f"Mapa {per}", "periodo": per, "casa": nome, "slug": slug,
                   "odd_casa": o1, "odd_fora": o2}
            for lado, odd, p_pin_l, p_mod_l in (("casa", o1, p_pin, p_mod),
                                               ("fora", o2, None if p_pin is None else 1 - p_pin,
                                                None if p_mod is None else 1 - p_mod)):
                lin[f"valor_pin_{lado}"] = None if p_pin_l is None else (p_pin_l * odd - 1) * 100
                lin[f"valor_mod_{lado}"] = None if p_mod_l is None else (p_mod_l * odd - 1) * 100
            fora.append(lin)
    return fora
