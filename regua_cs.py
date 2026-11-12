# -*- coding: utf-8 -*-
"""A REGUA do plano do CS (Fase 0, 12/11/2026): o que o modelo vale HOJE, antes de mexer.

Tudo com previsao gravada NA HORA (previsoes_cs2.jsonl) e a ultima leitura antes do jogo:
  1) modelo x Pinnacle sem margem (logloss, IC95), por mercado e por tier;
  2) inclinacao do modelo (1 = calibrado; < 1 = confiante demais) e o peso do modelo na mistura
     com a Pinnacle (0 = o modelo nao acrescenta nada ao mercado);
  3) nas casas DELE (odds_casas_cs2_historico.jsonl, serie): apostar onde ha valor contra a
     Pinnacle sem margem, e onde ha valor contra o modelo -- lucro e ROI nas odds reais.
`python regua_cs.py --congelar NOME` grava regua_<NOME>.json; cada fase compara com a anterior.
"""
from __future__ import annotations

import json
import math
import random
import sys
from pathlib import Path

import pandas as pd

import base_elo as be
import placar_pinnacle as pp

RAIZ = Path(__file__).resolve().parent
CASAS_HIST = RAIZ / "odds_casas_cs2_historico.jsonl"
CASAS_DELE = ("stake", "polymarket")
VALOR_MIN, VALOR_MAX = 1.0, 20.0


def _lg(p: float) -> float:
    p = min(max(p, 1e-6), 1 - 1e-6)
    return math.log(p / (1 - p))


def _sig(z: float) -> float:
    return 1 / (1 + math.exp(-z))


def _ll(ps, ys) -> float:
    return sum(be.ll(p, y) for p, y in zip(ps, ys)) / len(ys)


def _ic(dif, n_boot: int = 2000, seed: int = 7):
    rnd = random.Random(seed)
    b = sorted(sum(rnd.choice(dif) for _ in dif) / len(dif) for _ in range(n_boot))
    return b[int(0.025 * n_boot)], b[int(0.975 * n_boot) - 1]


def _melhor(f, lo: float, hi: float, passos: int = 60) -> float:
    """Minimo de f em [lo, hi] por busca na grade fina (f e de uma variavel, suave)."""
    xs = [lo + (hi - lo) * i / passos for i in range(passos + 1)]
    return min(xs, key=f)


def tier_do_jogo(d: pd.DataFrame, r: dict):
    ini = pd.Timestamp(r["inicio_utc"]).tz_localize(None)
    j = d[(d.dt >= ini - pd.Timedelta(hours=12)) & (d.dt <= ini + pd.Timedelta(hours=18))]
    a, b = r["time_casa"], r["time_fora"]
    s = j[((j.time1 == a) & (j.time2 == b)) | ((j.time1 == b) & (j.time2 == a))]
    return None if s.empty else str(s.tier.iloc[0])


def recorte(linhas: list) -> dict:
    """Pura: os numeros de um recorte de linhas do placar."""
    if not linhas:
        return {"n": 0}
    ys = [l["venceu_casa"] for l in linhas]
    pm = [l["p_modelo_casa"] for l in linhas]
    pk = [l["p_pinnacle_casa"] for l in linhas]
    dif = [be.ll(b, y) - be.ll(a, y) for a, b, y in zip(pm, pk, ys)]
    out = {"n": len(linhas), "ll_modelo": round(_ll(pm, ys), 4), "ll_pinnacle": round(_ll(pk, ys), 4),
           "vantagem_modelo": round(sum(dif) / len(dif), 4),
           "acerto_modelo": round(sum((p >= 0.5) == (y == 1) for p, y in zip(pm, ys)) / len(ys), 3),
           "acerto_pinnacle": round(sum((p >= 0.5) == (y == 1) for p, y in zip(pk, ys)) / len(ys), 3)}
    if len(linhas) >= 30:
        out["ic95"] = [round(x, 4) for x in _ic(dif)]
        out["inclinacao_modelo"] = round(_melhor(lambda c: _ll([_sig(c * _lg(p)) for p in pm], ys), 0.2, 2.0, 90), 2)
        out["peso_modelo_na_mistura"] = round(_melhor(
            lambda w: _ll([_sig(w * _lg(a) + (1 - w) * _lg(b)) for a, b in zip(pm, pk)], ys), 0.0, 1.0, 50), 2)
    ap = [l for l in linhas if l.get("apostou")]
    if ap:
        out["apostas_na_pinnacle"] = {"n": len(ap), "lucro": round(sum(l["lucro"] for l in ap), 2),
                                      "roi": round(sum(l["lucro"] for l in ap) / len(ap), 3)}
    return out


def ultima_das_casas(caminho: Path = CASAS_HIST) -> dict:
    """{(time1, time2, dia do inicio, casa): (odd1, odd2, inicio)} -- a ultima odd da SERIE antes do jogo."""
    fora: dict = {}
    if not caminho.exists():
        return fora
    for t in caminho.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(t)
        except ValueError:
            continue
        casa = str(r.get("casa", "")).split(".")[0]
        if r.get("mercado") != "Série" or casa not in CASAS_DELE or not r.get("inicio_utc"):
            continue
        if str(r["lido_em"])[:19] >= str(r["inicio_utc"])[:19]:
            continue
        k = (r["time1"], r["time2"], str(r["inicio_utc"])[:10], casa)
        if k not in fora or r["lido_em"] > fora[k][3]:
            fora[k] = (r["odds"][0], r["odds"][1], r["inicio_utc"], r["lido_em"])
    return fora


def _norm(x: str) -> str:
    return "".join(ch for ch in str(x).lower() if ch.isalnum())


def casas_dele(linhas: list, casas: dict, resolver=None) -> dict:
    """Serie: aposta nas casas dele onde ha valor contra a Pinnacle e contra o modelo.
    resolver(nome da casa) -> nome canonico do time (a OddsPapi escreve "Team Liquid", "Furia")."""
    res_ = resolver or (lambda n: n)
    por_jogo = {}
    for (t1, t2, dia, casa), (o1, o2, _ini, _l) in casas.items():
        por_jogo.setdefault((_norm(res_(t1)), _norm(res_(t2)), dia), []).append((casa, o1, o2))
    res = {"pinnacle": [], "modelo": [], "os_dois": []}
    vistos = 0
    for l in linhas:
        if l["periodo"] != 0:
            continue
        a, b, dia = _norm(l.get("time_casa") or l["casa"]), _norm(l.get("time_fora") or l["fora"]), str(l["inicio_utc"])[:10]
        cs = por_jogo.get((a, b, dia))
        inv = False
        if cs is None:
            cs, inv = por_jogo.get((b, a, dia)), True
        if not cs:
            continue
        vistos += 1
        y = l["venceu_casa"]
        for casa, o1, o2 in cs:
            oc, of = (o2, o1) if inv else (o1, o2)
            for lado, odd, pk, pm, ganhou in (("casa", oc, l["p_pinnacle_casa"], l["p_modelo_casa"], y == 1),
                                              ("fora", of, 1 - l["p_pinnacle_casa"], 1 - l["p_modelo_casa"], y == 0)):
                lucro = (odd - 1) if ganhou else -1.0
                vk, vm = (pk * odd - 1) * 100, (pm * odd - 1) * 100
                ok_k, ok_m = VALOR_MIN <= vk <= VALOR_MAX, VALOR_MIN <= vm <= VALOR_MAX
                if ok_k:
                    res["pinnacle"].append(lucro)
                if ok_m:
                    res["modelo"].append(lucro)
                if ok_k and ok_m:
                    res["os_dois"].append(lucro)
    fora = {"series_com_odd_das_casas": vistos}
    for k, v in res.items():
        fora[f"valor_contra_{k}"] = {"n": len(v), "lucro": round(sum(v), 2),
                                     "roi": round(sum(v) / len(v), 3) if v else None}
    return fora


def _resolver():
    """Nome da OddsPapi -> time canonico do modelo (so casamento exato ou apelido conhecido)."""
    import precos_core as pc
    est = pc.Estado()
    mapa = json.loads((RAIZ / "times_canonicos.json").read_text(encoding="utf-8"))
    cache: dict = {}

    def f(nome):
        if nome not in cache:
            limpo = str(nome).replace("Team ", "").strip() if str(nome).startswith("Team ") else str(nome)
            cache[nome] = pc.casar_estrito(est, nome, mapa) or pc.casar_estrito(est, limpo, mapa) or nome
        return cache[nome]
    return f


def medir() -> dict:
    d = be.carregar(incluir_c=True)
    pl = pp.placar(d, pp.carregar_registros())
    linhas = pl.get("linhas", [])
    for l in linhas:
        l["tier"] = tier_do_jogo(d, l)
    serie = [l for l in linhas if l["periodo"] == 0]
    mapa = [l for l in linhas if l["periodo"] > 0]
    out = {"medido_em": pd.Timestamp.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
           "janela": [min(l["inicio_utc"] for l in linhas)[:10], max(l["inicio_utc"] for l in linhas)[:10]] if linhas else [],
           "serie": recorte(serie), "mapa": recorte(mapa),
           "serie_por_tier": {t: recorte([l for l in serie if l["tier"] == t])
                              for t in sorted({str(l["tier"]) for l in serie})},
           "casas_dele": casas_dele(linhas, ultima_das_casas(), _resolver())}
    return out


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    r = medir()
    print(json.dumps(r, ensure_ascii=False, indent=1))
    if "--congelar" in sys.argv:
        nome = sys.argv[sys.argv.index("--congelar") + 1]
        (RAIZ / f"regua_{nome}.json").write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"gravado regua_{nome}.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
