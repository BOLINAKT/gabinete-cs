# -*- coding: utf-8 -*-
"""NOTA DE CADA JOGADOR EM CADA MAPA, AJUSTADA PELO ADVERSARIO (26/11/2026). Ele: "teria que precificar baseado
nos times, e nao so nas winrates [...] os times para chegarem no major tem que ganhar de outros".

Por cima do motor (elo_jogador.rodar, previsao prequencial de cada mapa), cada jogador tem um desvio por mapa,
aprendido pela SURPRESA (y - p') de cada mapa jogado -- ganhar a Mirage de um time forte vale mais que de um fraco
-- e leva esse desvio quando troca de time (como a nota geral). O time = media dos desvios do elenco do dia;
sem elenco conhecido, o desvio do proprio time naquele mapa.
  logit(p') = logit(p_motor) + desvio(A, mapa) - desvio(B, mapa) ;  desvio += K * (y - p')
MEDIDO (_medicoes/medir_mapa_forca_cs*.py; escolha na validacao 2021-23, teste uma vez), ganho sobre o motor
sem mapa: 2024+ +0,0022 IC95 [+0,0014; +0,0031], 2026 +0,0025 [+0,0010; +0,0040]. O ajuste anterior (taxa de
vitoria crua, encolhida) dava +0,0007. Por time: +0,0016/+0,0020. Esquecimento, mistura com o time e margem de
rounds: nada a mais. Pesquisa (26/11): o melhor sistema publicado para CS e o POR JOGADOR (arXiv 2410.02831).
"""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Dict, Optional, Tuple

import troca_elenco as te

K_MAPA = 0.05


def _lg(p: float) -> float:
    p = min(max(p, 1e-6), 1 - 1e-6)
    return math.log(p / (1 - p))


def _elenco(el, t, dt):
    e = te.elenco(el, t, dt)
    return tuple(e) if e is not None and 3 <= len(e) <= 7 else None


def aprender(d, el, prev: dict, k: float = K_MAPA, previsoes: Optional[dict] = None) -> Tuple[Dict, Dict]:
    """Passa por todos os mapas em ordem. prev = 1o retorno de elo_jogador.rodar ({chave: (dt, tier, p, y)}).
    -> (desvio por (jogador, mapa), desvio por (time, mapa)). `previsoes` (dict) recebe a previsao de cada mapa."""
    dj: Dict = defaultdict(float)
    dtm: Dict = defaultdict(float)
    for x in d.itertuples(index=False):
        ch = (x.pagina, x.data, x.time1, x.time2, x.mapa_n)
        if ch not in prev:
            continue
        dt, _tier, p, y = prev[ch]
        a, b, m = x.time1, x.time2, x.mapa
        ea, eb = _elenco(el, a, dt), _elenco(el, b, dt)
        oa = sum(dj[(j, m)] for j in ea) / len(ea) if ea else dtm[(a, m)]
        ob = sum(dj[(j, m)] for j in eb) / len(eb) if eb else dtm[(b, m)]
        q = 1 / (1 + math.exp(-(_lg(p) + oa - ob)))
        if previsoes is not None:          # conferencia: a previsao prequencial com o mapa, igual a da medicao
            previsoes[ch] = (dt, _tier, q, y)
        for t, e, s in ((a, ea, 1), (b, eb, -1)):
            dtm[(t, m)] += s * k * (y - q)
            if e:
                for j in e:
                    dj[(j, m)] += s * k * (y - q)
    return dict(dj), dict(dtm)


def desvio(dj: Dict, dtm: Dict, el, t: str, mapa: str, hoje) -> float:
    """O desvio do time NAQUELE mapa hoje: media do elenco do dia; sem elenco, o do time."""
    e = _elenco(el, t, hoje)
    if e:
        return sum(dj.get((j, mapa), 0.0) for j in e) / len(e)
    return dtm.get((t, mapa), 0.0)


def p_mapa(p_base: float, dj: Dict, dtm: Dict, el, ta: str, tb: str, mapa: str, hoje) -> float:
    z = _lg(p_base) + desvio(dj, dtm, el, ta, mapa, hoje) - desvio(dj, dtm, el, tb, mapa, hoje)
    return 1 / (1 + math.exp(-z))
