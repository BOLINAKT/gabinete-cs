# -*- coding: utf-8 -*-
"""Calibracao do modelo de margem (26/10/2026): p' = sigmoide(c*logit(p)+b).

c e b ajustados SO na validacao 2021-2023 (mapa S/A); aplicados no TESTE 2024+.
Mostra tambem a tabela de confiabilidade no teste (faixas de p x taxa real).
"""
from __future__ import annotations

import math
import sys

import pandas as pd

import base_elo as be
import pausa_e_estreia as pe
import variantes as va

VAL = (pd.Timestamp("2021-01-01"), be.INICIO_TESTE)


def ajusta(p, c, b):
    z = c * math.log(p / (1 - p)) + b
    return 1 / (1 + math.exp(-z))


def main() -> int:
    d = be.carregar()
    f = pe.rodar(d)
    sel = lambda desde, ate=None: [(i, p, y) for i, (dt, t, p, y) in f.items()
                                   if dt >= desde and (ate is None or dt < ate) and t in ("S", "A")]
    val, tes = sel(*VAL), sel(be.INICIO_TESTE)
    grade = [(c / 100, b / 100) for c in range(70, 131, 5) for b in range(-10, 11, 2)]
    c, b = min(grade, key=lambda g: va.media([be.ll(ajusta(p, *g), y) for _, p, y in val]))
    base = {i: be.ll(p, y) for i, p, y in tes}
    cal = {i: be.ll(ajusta(p, c, b), y) for i, p, y in tes}
    g, lo, hi, pv, n = va.pareado(base, cal)
    ok = g > 0.002 and pv < 0.05 and lo > 0
    print(f"c={c} b={b}: {va.media(list(base.values())):.4f} -> {va.media(list(cal.values())):.4f} "
          f"ganho {g:+.4f} IC95 [{lo:+.4f}, {hi:+.4f}] p={pv:.3f} {'PASSA' if ok else 'nao passa'}")
    print("confiabilidade no teste (p do time1 -> taxa real):")
    for a0 in range(0, 100, 10):
        fx = [(p, y) for _, p, y in tes if a0 / 100 <= p < (a0 + 10) / 100]
        if len(fx) >= 50:
            print(f"  {a0:2d}-{a0+10:3d}%  n={len(fx):5d}  previsto {va.media([p for p, _ in fx]):.3f}  real {va.media([y for _, y in fx]):.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
