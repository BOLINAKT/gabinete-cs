# -*- coding: utf-8 -*-
"""ATUALIZA os dados do modelo todo dia, gastando pouco da Liquipedia (26/10/2026).

Sem isto os mapas param no dia da coleta grande (25/10) e a nota de todo time
envelhece. Incremental e com ORCAMENTO de chamadas por corrida:
  1. torneios NOVOS: os 100 mais recentes de cada categoria S/A/B (3 chamadas);
     novo de 2020+ -> le a pagina dele (datas do infobox) e entra no indice;
  2. torneios ATIVOS (inicio <= hoje+2 e fim >= hoje-7): relidos SEM cache, com
     as subpaginas -- as linhas dessas paginas no mapas_cs.csv sao SUBSTITUIDAS
     (corrige placar editado depois);
  3. nomes de time NOVOS -> {{Team|...}} (chamada pesada: 1 a cada 31 s);
  4. elencos dos times que jogaram e cujo elenco tem 7+ dias (50 por chamada).
Para no primeiro 429 (liquipedia.Pausado) e sai com 75; o que ja leu fica salvo.
Indice dos torneios: torneios_cs.json (versionado, o robo nao tem o cache).

Uso: python atualizar_dados.py [--orcamento 80] [--hoje AAAA-MM-DD] [--so-cache]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

import extrator as ex
import liquipedia as lq

RAIZ = Path(__file__).resolve().parent
MAPAS = RAIZ / "mapas_cs.csv"
INDICE = RAIZ / "torneios_cs.json"
CANON = RAIZ / "times_canonicos.json"
PAGINAS = RAIZ / "times_paginas.json"
ELENCOS = RAIZ / "elencos.csv"
ELENCOS_LIDOS = RAIZ / "elencos_lidos.json"
# AGENDA (27/10/2026, pedido dele): os jogos vem da Liquipedia e as odds da
# Pinnacle entram depois, quando ela abrir o mercado. Proximos jogos dos torneios
# ativos, relidos junto com os mapas (as mesmas paginas, sem chamada a mais).
AGENDA = RAIZ / "agenda_cs.json"
AGENDA_DIAS = 10
TIERS = (("S", "Category:S-Tier Tournaments"), ("A", "Category:A-Tier Tournaments"),
         ("B", "Category:B-Tier Tournaments"))
ANO_MINIMO = 2020
DIAS_ELENCO = 7
# TIER C (26/10/2026, hipotese): MIBR/Astralis/fnatic/HOTU "parados" ha semanas e o
# "STK Ranked" deles fora das categorias S/A/B. Coleta AOS POUCOS (o que sobrar do
# orcamento diario), so 2025+, e entra so no TREINO -- a regua continua S/A/B.
CAT_C = "Category:C-Tier Tournaments"
ANO_MINIMO_C = 2025
RESERVA = 40     # chamadas guardadas para nomes e elencos depois do tier C
RC_PAUSA = 75


class Orcamento(Exception):
    """Acabou o orcamento de chamadas desta corrida."""


class Cliente:
    """liquipedia.chamar com contagem; so_cache = teste sem rede."""

    def __init__(self, limite: int, so_cache: bool):
        self.limite, self.usadas, self.so_cache = limite, 0, so_cache

    def __call__(self, **params) -> dict:
        if self.usadas >= self.limite:
            raise Orcamento()
        if self.so_cache:
            d = lq.do_cache(**params)
            if d is None:
                raise Orcamento("fora do cache")
            return d
        self.usadas += 1
        return lq.chamar(fresco=True, **params)

    def texto(self, pagina: str) -> str:
        d = self(action="query", prop="revisions", rvprop="content", rvslots="main", titles=pagina)
        ps = (d.get("query") or {}).get("pages") or []
        return ps[0]["revisions"][0]["slots"]["main"]["content"] if ps and "revisions" in ps[0] else ""


def datas_infobox(txt: str) -> tuple:
    def f(k):
        m = re.search(r"\|\s*" + k + r"\s*=\s*(\d{4}-\d{2}-\d{2})", txt or "")
        return m.group(1) if m else None
    return f("sdate") or f("date"), f("edate") or f("date")


def ativo(v: dict, hoje: date) -> bool:
    """Pura: o torneio pode ter jogo novo agora?"""
    if not v.get("inicio"):
        return False
    ini = date.fromisoformat(v["inicio"])
    fim = date.fromisoformat(v["fim"]) if v.get("fim") else ini + timedelta(days=60)
    return ini <= hoje + timedelta(days=2) and fim >= hoje - timedelta(days=7)


def tier_da_pagina(pagina: str, indice: dict, atual: str = "") -> str:
    """Pura: o tier do torneio MAIS ESPECIFICO que contem a pagina (26/10/2026).
    "PGL/2027/Bucharest/Qualifier" e B (torneio proprio), nao o S do evento-mae --
    antes a qualificatoria herdava S e misturava a regua do S-tier."""
    partes = str(pagina).split("/")
    for i in range(len(partes), 0, -1):
        v = indice.get("/".join(partes[:i]))
        if v:
            return v["tier"]
    return atual


def substituir_paginas(antigas: pd.DataFrame, novas: list, paginas_relidas: set) -> pd.DataFrame:
    """Pura: tira as linhas das paginas relidas e poe as novas (sem duplicar mapa)."""
    fica = antigas[~antigas.pagina.isin(paginas_relidas)]
    junto = pd.concat([fica, pd.DataFrame(novas, columns=antigas.columns)], ignore_index=True)
    chave = ["data", "time1", "time2", "mapa_n", "mapa", "rounds1", "rounds2"]
    return junto.drop_duplicates(subset=chave, keep="last")


def _torneios_novos(cli, indice: dict) -> int:
    novos = 0
    for tier, cat in TIERS:
        d = cli(action="query", list="categorymembers", cmtitle=cat, cmlimit=100, cmnamespace=0,
                cmsort="timestamp", cmdir="desc")
        for x in (d.get("query") or {}).get("categorymembers", []):
            t = x["title"]
            anos = [int(a) for a in re.findall(r"(?<!\d)(20\d\d)(?!\d)", t)]
            if t in indice or not anos or max(anos) < ANO_MINIMO:
                continue
            ini, fim = datas_infobox(cli.texto(t))
            indice[t] = {"tier": tier, "inicio": ini, "fim": fim}
            novos += 1
    return novos


def _reler_ativos(cli, indice: dict, hoje: date, agenda: list | None = None) -> tuple:
    ativos = sorted((t for t, v in indice.items() if ativo(v, hoje)),
                    key=lambda t: indice[t]["inicio"] or "", reverse=True)
    linhas, relidas = [], set()
    agenda = agenda if agenda is not None else []
    for t in ativos:
        d = cli(action="query", list="allpages", apprefix=t + "/", aplimit=100, apnamespace=0)
        subs = [p["title"] for p in (d.get("query") or {}).get("allpages", [])]
        for pg in [t, *subs]:
            txt = cli.texto(pg)
            if pg == t:   # datas do infobox mudam (adiamento, fim estendido)
                ini, fim = datas_infobox(txt)
                indice[t].update(inicio=ini or indice[t]["inicio"], fim=fim or indice[t]["fim"])
            if "{{Match" in txt:
                linhas.extend(ex.mapas_da_pagina(txt, pagina=pg, tier=indice[t]["tier"]))
                agenda.extend(ex.proximos_da_pagina(txt, pagina=pg, tier=indice[t]["tier"]))
            relidas.add(pg)
    return linhas, relidas, ativos


def gravar_agenda(novos: list, relidas: set, agora) -> int:
    """Junta a agenda nova com a anterior (paginas NAO relidas desta vez ficam),
    so jogos de agora-4 h ate agora+AGENDA_DIAS. Pura no calculo; grava AGENDA."""
    ini = (agora - pd.Timedelta(hours=4)).strftime("%Y-%m-%dT%H:%M:00Z")
    fim = (agora + pd.Timedelta(days=AGENDA_DIAS)).strftime("%Y-%m-%dT%H:%M:00Z")
    velhos = []
    if AGENDA.exists():
        try:
            velhos = [j for j in json.loads(AGENDA.read_text(encoding="utf-8")).get("jogos", [])
                      if j.get("pagina") not in relidas]
        except (OSError, ValueError):
            velhos = []
    vistos, jogos = set(), []
    for j in sorted(novos + velhos, key=lambda j: j["inicio_utc"]):
        k = (j["pagina"], j["time1"], j["time2"], j["inicio_utc"])
        if k in vistos or not (ini <= j["inicio_utc"] <= fim):
            continue
        vistos.add(k)
        jogos.append(j)
    AGENDA.write_text(json.dumps({"lido_em": agora.strftime("%Y-%m-%dT%H:%M:%SZ"), "jogos": jogos},
                                 ensure_ascii=False, indent=1), encoding="utf-8")
    return len(jogos)


def _listar_c(cli, indice: dict) -> int:
    """Uma vez: todos os torneios C de 2025+ entram no indice como 'pendente'."""
    if indice.get("_c_listado"):
        return 0
    cont, novos = {}, 0
    while True:
        d = cli(action="query", list="categorymembers", cmtitle=CAT_C, cmlimit=500, cmnamespace=0, **cont)
        for x in (d.get("query") or {}).get("categorymembers", []):
            t = x["title"]
            anos = [int(a) for a in re.findall(r"(?<!\d)(20\d\d)(?!\d)", t)]
            if t in indice or not anos or max(anos) < ANO_MINIMO_C:
                continue
            indice[t] = {"tier": "C", "inicio": None, "fim": None, "pendente": True}
            novos += 1
        if "continue" not in d:
            break
        cont = dict(d["continue"])
    indice["_c_listado"] = {"tier": "-", "inicio": None, "fim": None}
    return novos


def _coletar_pendentes(cli, indice: dict, linhas: list, relidas: set) -> tuple:
    """Torneios 'pendente' (tier C), do mais recente no nome para o mais antigo.
    linhas/relidas vem de fora e sao preenchidas no lugar: o que foi lido antes de
    acabar o orcamento NAO se perde."""
    pend = sorted((t for t, v in indice.items() if v.get("pendente")),
                  key=lambda t: max(re.findall(r"20\d\d", t) or ["0"]), reverse=True)
    feitos = 0
    for t in pend:
        d = cli(action="query", list="allpages", apprefix=t + "/", aplimit=100, apnamespace=0)
        subs = [p["title"] for p in (d.get("query") or {}).get("allpages", [])]
        paginas = []
        for pg in [t, *subs]:
            txt = cli.texto(pg)
            if pg == t:
                ini, fim = datas_infobox(txt)
                indice[t].update(inicio=ini, fim=fim)
            if "{{Match" in txt:
                paginas.extend(ex.mapas_da_pagina(txt, pagina=pg, tier="C"))
        linhas.extend(paginas)
        relidas.update([t, *subs])
        indice[t]["pendente"] = False
        feitos += 1
    return linhas, relidas, feitos


def _nomes_novos(cli, nomes: set) -> int:
    canon = json.loads(CANON.read_text(encoding="utf-8")) if CANON.exists() else {}
    pags = json.loads(PAGINAS.read_text(encoding="utf-8")) if PAGINAS.exists() else {}
    faltam = sorted(n for n in nomes if n and n not in canon and "@" not in n and "}" not in n and "|" not in n)
    import resolver_times as rt
    for i in range(0, len(faltam), rt.LOTE):
        lote = faltam[i:i + rt.LOTE]
        r = cli(action="expandtemplates", text="\n".join(f"@@{n}@@{{{{Team|{n}}}}}" for n in lote), prop="wikitext")
        w = r["expandtemplates"]["wikitext"]
        canon.update(rt.ler_lote(w))
        for c, pg in rt.ler_paginas(w).items():
            pags.setdefault(c, pg)
    CANON.write_text(json.dumps(canon, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")
    PAGINAS.write_text(json.dumps(pags, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")
    return len(faltam)


def _elencos(cli, times: set, hoje: date) -> int:
    import base_elo as be
    import elencos as eln
    lidos = json.loads(ELENCOS_LIDOS.read_text(encoding="utf-8")) if ELENCOS_LIDOS.exists() else {}
    canon = json.loads(CANON.read_text(encoding="utf-8"))
    pags = json.loads(PAGINAS.read_text(encoding="utf-8"))
    alvo = sorted({be.canonico(t, canon) for t in times}
                  - {t for t, d in lidos.items() if date.fromisoformat(d) > hoje - timedelta(days=DIAS_ELENCO)})
    if not alvo:
        return 0
    e = pd.read_csv(ELENCOS, dtype=str).fillna("") if ELENCOS.exists() else pd.DataFrame(
        columns=["time", "jogador", "entrada", "saida"])
    novas, feitos = [], set()
    try:
        for i in range(0, len(alvo), eln.LOTE):
            lote = alvo[i:i + eln.LOTE]
            de_pg = {pags.get(t, t): t for t in lote}
            r = cli(action="query", prop="revisions", rvprop="content", rvslots="main",
                    titles="|".join(de_pg), redirects=1)
            q = r.get("query") or {}
            volta = {x["to"]: x["from"] for x in (q.get("redirects") or []) + (q.get("normalized") or [])}
            for p in q.get("pages") or []:
                nome = p["title"]
                while nome in volta:
                    nome = volta[nome]
                nome = de_pg.get(nome, nome)
                feitos.add(nome)
                if "revisions" in p:
                    novas += [(nome, *j) for j in eln.jogadores(p["revisions"][0]["slots"]["main"]["content"])]
    finally:
        if feitos:
            e = pd.concat([e[~e.time.isin(feitos)], pd.DataFrame(novas, columns=e.columns)], ignore_index=True)
            e.to_csv(ELENCOS, index=False, quoting=csv.QUOTE_MINIMAL)
            lidos.update({t: hoje.isoformat() for t in feitos})
            ELENCOS_LIDOS.write_text(json.dumps(lidos, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")
    return len(feitos)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--orcamento", type=int, default=80)
    ap.add_argument("--hoje", default=None)
    ap.add_argument("--so-cache", action="store_true", help="teste: so o cache, sem rede")
    # 27/10/2026: coleta do tier C DESLIGADA por padrao -- previa com 237 torneios
    # (2,5 mil mapas, 2026 bem coberto): efeito zero na regua S/A/B, e nao achou os
    # jogos "sumidos" de MIBR/Astralis. Nao vale ~600 chamadas/dia da Liquipedia.
    ap.add_argument("--coletar-c", action="store_true", help="retoma a coleta aos poucos do tier C")
    ap.add_argument("--so-agenda", action="store_true",
                    help="corrida leve (3 em 3 h): so torneios novos e ativos; sem C, nomes e elencos")
    a = ap.parse_args()
    hoje = date.fromisoformat(a.hoje) if a.hoje else date.today()
    cli = Cliente(a.orcamento, a.so_cache)
    indice = json.loads(INDICE.read_text(encoding="utf-8")) if INDICE.exists() else {}
    antigas = pd.read_csv(MAPAS, dtype=str)
    rc, linhas, relidas, ativos, novos, agenda = 0, [], set(), [], 0, []
    try:
        if not a.so_cache:   # a lista "mais recentes" nunca esta no cache
            novos = _torneios_novos(cli, indice)
        linhas, relidas, ativos = _reler_ativos(cli, indice, hoje, agenda)
    except (lq.Pausado, Orcamento) as e:
        print(f"[dados] parou: {type(e).__name__} {e}")
        rc = RC_PAUSA if isinstance(e, lq.Pausado) else 0
    INDICE.write_text(json.dumps(indice, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")
    if relidas and not a.so_cache:
        print(f"[dados] agenda: {gravar_agenda(agenda, relidas, pd.Timestamp.now(tz='UTC').tz_localize(None))} "
              f"proximos jogos")
    if relidas:
        tudo = substituir_paginas(antigas, [{k: str(v) if v is not None else "" for k, v in l.items()}
                                            for l in linhas], relidas)
        tudo["tier"] = [tier_da_pagina(pg, indice, tr) for pg, tr in zip(tudo.pagina, tudo.tier)]
        tudo.to_csv(MAPAS, index=False)
        print(f"[dados] {len(ativos)} torneios ativos, {len(relidas)} paginas relidas, "
              f"mapas {len(antigas)} -> {len(tudo)} (+{len(tudo) - len(antigas)})")
    print(f"[dados] torneios novos no indice: {novos}")
    # TIER C com o que sobrou do orcamento (fora da regua; so treino)
    lc, rc_c, feitos_c = [], set(), 0
    pend_antes = sum(1 for v in indice.values() if isinstance(v, dict) and v.get("pendente"))
    if rc == 0 and not a.so_cache and a.coletar_c and not a.so_agenda:
        limite_total = cli.limite
        cli.limite = max(cli.usadas, limite_total - RESERVA)
        try:
            print(f"[dados] torneios C listados: {_listar_c(cli, indice)}")
            lc, rc_c, feitos_c = _coletar_pendentes(cli, indice, lc, rc_c)
        except (lq.Pausado, Orcamento) as e:
            print(f"[dados] tier C parou: {type(e).__name__}")
            rc = RC_PAUSA if isinstance(e, lq.Pausado) else 0
        finally:
            cli.limite = limite_total
            INDICE.write_text(json.dumps(indice, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")
    if lc or rc_c:
        base = pd.read_csv(MAPAS, dtype=str)
        tudo = substituir_paginas(base, [{k: str(v) if v is not None else "" for k, v in l.items()} for l in lc], rc_c)
        tudo.to_csv(MAPAS, index=False)
        linhas = linhas + lc
        pend = sum(1 for v in indice.values() if isinstance(v, dict) and v.get("pendente"))
        # conta pelo indice: o orcamento corta no meio e o retorno nao chega
        print(f"[dados] tier C: {pend_antes - pend} torneios coletados, +{len(tudo) - len(base)} mapas; faltam {pend}")
    if rc == 0 and not a.so_agenda:
        times = {l["time1"] for l in linhas} | {l["time2"] for l in linhas}
        todos = pd.read_csv(MAPAS, dtype=str, usecols=["time1", "time2"])
        try:
            # nomes: TODOS os do arquivo sem resolucao (nao so os desta corrida)
            print(f"[dados] nomes novos resolvidos: {_nomes_novos(cli, set(todos.time1) | set(todos.time2))}")
            print(f"[dados] elencos relidos: {_elencos(cli, times, hoje)}")
        except (lq.Pausado, Orcamento) as e:
            print(f"[dados] parou nos nomes/elencos: {type(e).__name__} {e}")
            rc = RC_PAUSA if isinstance(e, lq.Pausado) else 0
    print(f"[dados] chamadas usadas: {cli.usadas}/{cli.limite}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
