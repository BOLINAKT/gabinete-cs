# -*- coding: utf-8 -*-
"""A SERIE COERENTE (Fase 2 do plano do CS, 12/11/2026).

Os mapas de uma serie nao sao independentes: quem esta bem no dia tende a ganhar os dois (a
"forma do dia", medida no LoL em 29/10/2026). A chance de cada mapa vem de uma Beta com media p
e concentracao KAPPA; KAPPA None = mapas independentes (a conta antiga, p x p).
Tudo sai do MESMO numero -- a chance da serie do modelo: placar exato, +-1,5, total de mapas.
`python serie_cs.py` mede no cego (escolhe KAPPA antes do teste, confere no teste).
"""
from __future__ import annotations

import math
import sys
from typing import Dict, Optional

KAPPA_SERIE: Optional[float] = None      # sem Estado: independentes. O app usa kappa_atual().
# MEDIDO em 12/11/2026 (series S/A/B, serie oficial preservada, kappa MOVEL = o melhor nos 12
# meses anteriores, sem espiar): placar exato 2024+ +0,0079 IC95 [+0,0042; +0,0115] (n=6.827),
# 2025+ +0,0082, 2026 +0,0093; "teve varrida" +0,0070 [+0,0033; +0,0105]. Kappa fixo (4, escolhido
# na era CS:GO) passava por pouco e exagerava nos favoritos do CS2 -- por isso o movel (hoje ~6-8).
GRADE_KAPPA = (None, 3, 4, 5, 6, 8, 10, 15, 25)


def kappa_atual(series: list, hoje, c_serie: float = 1.0, meses: int = 12) -> Optional[float]:
    """O kappa para usar HOJE: o que melhor explica o PLACAR das series S/A/B dos `meses` anteriores."""
    import pandas as pd

    import base_elo as be
    import calibra_serie as cal
    ini = pd.Timestamp(hoje)
    j = [x for x in series if x["tier"] in ("S", "A", "B") and x["v1"] != x["v2"]
         and max(x["v1"], x["v2"]) in (2, 3) and x["v1"] + x["v2"] <= 5
         and ini - pd.DateOffset(months=meses) <= x["dt"] < ini]
    if len(j) < 200:
        return None

    def custo(k):
        t = 0.0
        for x in j:
            bo = 3 if max(x["v1"], x["v2"]) == 2 else 5
            ps = be.p_serie(cal.ajusta(x["p1"], c_serie), max(x["v1"], x["v2"]))
            t -= math.log(max(placares(mapa_coerente(ps, bo, k), bo, k)[f"{x['v1']}-{x['v2']}"], 1e-9))
        return t
    return min(GRADE_KAPPA, key=custo)


def _sem_margem(o1, o2):
    s = 1 / o1 + 1 / o2
    return (1 / o1) / s, (1 / o2) / s


def mercados_da_serie(p_serie_casa: float, bo: int, kappa, linhas_pinnacle, jogo_id, casa: str, fora: str) -> list:
    """As apostas da serie alem do vencedor, coerentes com ele: handicap de mapas, total de mapas e
    placar exato. Cada item: {"mercado", "lados": [{rotulo, p_modelo, odd_modelo, p_pinnacle,
    odd_pinnacle, vantagem}, ...]} (mesmo formato dos mercados de vencedor)."""
    if int(bo) not in (3, 5):
        return []
    mk = mercados(p_serie_casa, bo, kappa)
    pin_sp, pin_tot = {}, {}
    for l in linhas_pinnacle or []:
        if l.get("matchup") != jogo_id or l.get("periodo") != 0 or not l.get("odd"):
            continue
        if l["tipo"] == "spread":
            pin_sp[(l["lado"], float(l["pontos"]))] = l["odd"]
        elif l["tipo"] == "total":
            pin_tot[(l["lado"], float(l["pontos"]))] = l["odd"]

    def lado(rotulo, p, odd, p_pin):
        return {"rotulo": rotulo, "lado": rotulo, "p_modelo": p, "odd_modelo": 1 / p if p > 0 else None,
                "p_pinnacle": p_pin, "odd_pinnacle": odd, "vantagem": (p * odd - 1) * 100 if odd else None}

    def par(rot_a, p_a, rot_b, odd_a, odd_b, nome):
        pa = pb = None
        if odd_a and odd_b:
            pa, pb = _sem_margem(odd_a, odd_b)
        return {"mercado": nome, "periodo": 0, "lados": [lado(rot_a, p_a, odd_a, pa), lado(rot_b, 1 - p_a, odd_b, pb)]}
    f = lambda x: f"{x:g}".replace(".", ",")
    fora_ = []
    for h in ((1.5,) if int(bo) == 3 else (1.5, 2.5)):
        fora_.append(par(f"{casa} −{f(h)}", mk[f"time1 -{h}"], f"{fora} +{f(h)}",
                         pin_sp.get(("home", -h)), pin_sp.get(("away", h)), f"Mapas ±{f(h)}"))
        fora_.append(par(f"{casa} +{f(h)}", mk[f"time1 +{h}"], f"{fora} −{f(h)}",
                         pin_sp.get(("home", h)), pin_sp.get(("away", -h)), f"Mapas ±{f(h)}"))
    for L in ((2.5,) if int(bo) == 3 else (3.5, 4.5)):
        fora_.append(par(f"Mais de {f(L)} mapas", mk[f"mapas mais de {L}"], f"Menos de {f(L)} mapas",
                         pin_tot.get(("over", L)), pin_tot.get(("under", L)), "Total de mapas"))
    pl = {k[7:]: v for k, v in mk.items() if k.startswith("placar ")}
    for k in [k for k in pl if int(k[0]) > int(k[2])]:
        inv = f"{k[2]}-{k[0]}"
        fora_.append({"mercado": "Placar exato", "periodo": 0, "lados": [
            lado(f"{casa} {k}", pl[k], None, None), lado(f"{fora} {k}", pl[inv], None, None)]})
    return fora_


def _momento(p: float, a: int, b: int, kappa: Optional[float]) -> float:
    """E[t^a (1-t)^b] com t ~ Beta(p*kappa, (1-p)*kappa); kappa None = independentes."""
    q = 1.0 - p
    if kappa is None:
        return (p ** a) * (q ** b)
    al, be_ = p * kappa, q * kappa
    num = 1.0
    for i in range(a):
        num *= al + i
    for j in range(b):
        num *= be_ + j
    den = 1.0
    for k in range(a + b):
        den *= kappa + k
    return num / den


def placares(p_mapa: float, bo: int, kappa: Optional[float] = "padrao") -> Dict[str, float]:
    """{"2-0": p, "2-1": p, "1-2": p, "0-2": p} (mapas do time 1 - mapas do time 2)."""
    k = KAPPA_SERIE if kappa == "padrao" else kappa
    p = min(max(float(p_mapa), 1e-6), 1 - 1e-6)
    m = lambda a, b: _momento(p, a, b, k)
    if int(bo) == 3:
        return {"2-0": m(2, 0), "2-1": 2 * m(2, 1), "1-2": 2 * m(1, 2), "0-2": m(0, 2)}
    if int(bo) == 5:
        return {"3-0": m(3, 0), "3-1": 3 * m(3, 1), "3-2": 6 * m(3, 2),
                "2-3": 6 * m(2, 3), "1-3": 3 * m(1, 3), "0-3": m(0, 3)}
    return {"1-0": p, "0-1": 1 - p}


def p_serie(p_mapa: float, bo: int, kappa: Optional[float] = "padrao") -> float:
    return sum(v for k, v in placares(p_mapa, bo, kappa).items() if int(k[0]) > int(k[2]))


def mapa_coerente(p_serie_alvo: float, bo: int, kappa: Optional[float] = "padrao") -> float:
    """A chance do mapa que, com a forma do dia, da exatamente a chance da SERIE do modelo."""
    lo, hi = 1e-5, 1 - 1e-5
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if p_serie(mid, bo, kappa) < p_serie_alvo else (lo, mid)
    return (lo + hi) / 2


def mercados(p_serie_1: float, bo: int, kappa: Optional[float] = "padrao") -> Dict[str, float]:
    """Tudo coerente com a chance da serie: placares, handicaps de mapas (do time 1) e total."""
    pl = placares(mapa_coerente(p_serie_1, bo, kappa), bo, kappa)
    saldo = lambda k: int(k[0]) - int(k[2])
    n = lambda k: int(k[0]) + int(k[2])
    out = {f"placar {k}": v for k, v in pl.items()}
    for h in ((1.5,) if int(bo) == 3 else (1.5, 2.5)):
        out[f"time1 -{h}"] = sum(v for k, v in pl.items() if saldo(k) > h)
        out[f"time1 +{h}"] = sum(v for k, v in pl.items() if saldo(k) > -h)
    for L in ((2.5,) if int(bo) == 3 else (3.5, 4.5)):
        out[f"mapas mais de {L}"] = sum(v for k, v in pl.items() if n(k) > L)
    return out


def _medir() -> int:
    import pandas as pd

    import base_elo as be
    import calibra_movel as cm
    import calibra_serie as cal
    import elo_jogador as ej
    import troca_elenco as te
    import variantes as va

    sys.stdout.reconfigure(encoding="utf-8")
    d = be.carregar()
    _m, s = ej.rodar(d, te.carregar_elencos(), ej.W_OFICIAL, ej.KJ_OFICIAL)
    T = ("S", "A", "B")
    ser = [x for x in s if x["tier"] in T and x["v1"] != x["v2"] and max(x["v1"], x["v2"]) in (2, 3)
           and (x["v1"] + x["v2"]) <= 5]
    mes = lambda dt: pd.Timestamp(dt.year, dt.month, 1)
    cs: dict = {}

    def linha(x, kappa):
        """logloss do placar exato e do "teve varrida", com a serie do modelo oficial preservada."""
        bo = 3 if max(x["v1"], x["v2"]) == 2 else 5
        mm = mes(x["dt"])
        if mm not in cs:
            cs[mm] = cm.c_serie_atual(s, mm)
        ps = be.p_serie(cal.ajusta(x["p1"], cs[mm]), max(x["v1"], x["v2"]))       # a serie oficial
        pl = placares(mapa_coerente(ps, bo, kappa), bo, kappa)
        real = f"{x['v1']}-{x['v2']}"
        varr = [k for k in pl if "0" in (k[0], k[2])]
        p_varr = sum(pl[k] for k in varr)
        return -math.log(max(pl[real], 1e-9)), be.ll(p_varr, int(real in varr))

    treino = [x for x in ser if x["dt"] < be.INICIO_TESTE]
    teste = [x for x in ser if x["dt"] >= be.INICIO_TESTE]
    print(f"series S/A/B: treino {len(treino)} (antes de {be.INICIO_TESTE:%Y-%m}) | teste {len(teste)}")
    grade = [None, 2, 3, 4, 5, 6, 8, 10, 15, 25, 50]
    res = {k: va.media([linha(x, k)[0] for x in treino]) for k in grade}
    for k, v in res.items():
        print(f"  treino kappa={k}: placar {v:.4f}")
    k_star = min(res, key=res.get)
    print("kappa escolhido no treino:", k_star)
    B = {i: linha(x, None) for i, x in enumerate(teste)}
    V = {i: linha(x, k_star) for i, x in enumerate(teste)}
    for nome, j in (("placar exato", 0), ("teve varrida", 1)):
        g, lo, hi, p, n = va.pareado({i: v[j] for i, v in B.items()}, {i: v[j] for i, v in V.items()})
        print(f"TESTE {nome}: independentes {va.media([v[j] for v in B.values()]):.4f} -> forma do dia "
              f"{va.media([v[j] for v in V.values()]):.4f} ganho {g:+.4f} [{lo:+.4f}, {hi:+.4f}] p={p:.3f} n={n}")
    # a varrida prevista x real, por faixa de favoritismo (BO3)
    print("BO3 no teste -- favorito vence 2-0: previsto independente x forma do dia x real")
    for lo_, hi_ in ((0.5, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 1.01)):
        pi, pb, re, n = [], [], [], 0
        for x in teste:
            if max(x["v1"], x["v2"]) != 2:
                continue
            ps = be.p_serie(cal.ajusta(x["p1"], cs[mes(x["dt"])]), 2)
            fav1 = ps >= 0.5
            pf = ps if fav1 else 1 - ps
            if not (lo_ <= pf < hi_):
                continue
            n += 1
            pi.append(placares(mapa_coerente(pf, 3, None), 3, None)["2-0"])
            pb.append(placares(mapa_coerente(pf, 3, k_star), 3, k_star)["2-0"])
            re.append(int((x["v1"], x["v2"]) == ((2, 0) if fav1 else (0, 2))))
        if n:
            print(f"  serie {lo_:.0%}-{min(hi_, 1):.0%}: {va.media(pi):.1%} x {va.media(pb):.1%} x {va.media(re):.1%} (n={n})")
    return 0


if __name__ == "__main__":
    sys.exit(_medir())
