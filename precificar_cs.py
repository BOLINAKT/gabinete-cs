# -*- coding: utf-8 -*-
"""Odd justa do modelo x Pinnacle sem margem, no terminal (26/10/2026).

O calculo mora em precos_core.py (o mesmo do app_cs.py); aqui so imprime e
grava precos_cs2.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import precos_core as pc
import tela_cs as tl

RAIZ = Path(__file__).resolve().parent


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    est = pc.Estado()
    od = json.loads((RAIZ / "odds_cs2.json").read_text(encoding="utf-8"))
    jogos = pc.calcular(est, od)
    print(f"dados ate {est.fim:%d/%m %H:%M} · odds lidas {tl.hora_br(od['lido_em'])} (Brasilia)\n")
    saida = []
    for j in jogos:
        print(f"{j['casa']} x {j['fora']} · {j['liga']} · BO{j['bo']} · {tl.hora_br(j['inicio_utc'])}"
              + (" (JA TINHA COMECADO na leitura)" if j["ja_comecou"] else ""))
        for (t, como), nome, f in zip(j["casou"], (j["casa"], j["fora"]), j["fichas"]):
            print(f"   {nome} -> {t} ({como}, {f['mapas_ano']} mapas no ano, ultimo {f['ultimo']})" if t
                  else f"   {nome} -> NADA")
        for a in j["avisos"]:
            print(f"   NAO PRECIFICADO: {a}")
        for m in j["mercados"]:
            a, b = m["lados"]
            txt = (f"   {m['mercado']:7s} modelo {a['lado']} {a['p_modelo']:5.1%} (odd {a['odd_modelo']:5.2f}) "
                   f"x {b['lado']} {b['p_modelo']:5.1%} (odd {b['odd_modelo']:5.2f})")
            if a["p_pinnacle"] is not None:
                txt += f"  | Pinnacle justa {a['p_pinnacle']:5.1%}  dif {100 * (a['p_modelo'] - a['p_pinnacle']):+5.1f} pp"
            print(txt)
            saida.append({"jogo": j["id"], "casa": j["casa"], "fora": j["fora"], "mercado": m["mercado"],
                          "p_modelo_casa": round(a["p_modelo"], 4),
                          "p_pinnacle_casa": None if a["p_pinnacle"] is None else round(a["p_pinnacle"], 4)})
        print()
    (RAIZ / "precos_cs2.json").write_text(json.dumps({"lido_em": od["lido_em"], "precos": saida},
                                                     ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
