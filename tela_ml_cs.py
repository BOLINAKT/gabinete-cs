# -*- coding: utf-8 -*-
"""A TELA DE ML DO CS (25/11/2026). Ele: "no CS 99% dos casos vai ser ML [...] que eu consiga fazer a mesma
pesquisa como no LoL e no Dota: pesar os dois times, aparece uma telinha que diz o mapa, o justo do mapa, do
MD3, do MD5" + "mostrar os logos dos times" + "pode mostrar o rating".

So HTML (puro, testavel). Os numeros saem do MESMO caminho do app (precos_core.calcular e veto_cs.p_com_mapa):
nada de conta nova aqui. Imagens: imagens_cs.json (imagens_cs.py, Liquipedia, baixadas uma vez).
"""
from __future__ import annotations

import base64
import json
from functools import lru_cache
from html import escape
from pathlib import Path

import veto_cs as vc

RAIZ = Path(__file__).resolve().parent
COR_A, COR_B = "#2daac4", "#d9a441"
CICLO = (None, "A", "B", "ban", "decisivo")   # cada clique no cartao do mapa anda um passo


def proximo_estado(v):
    """Pura. O estado do mapa depois de um clique: nada -> pick esquerda -> pick direita -> ban -> decisivo."""
    return CICLO[(CICLO.index(v) + 1) % len(CICLO)] if v in CICLO else "A"


def curto(nome: str) -> str:
    """Pura. Nome que cabe no cartao do mapa: 'Team Vitality' -> 'Vitality', 'Natus Vincere' -> 'Natus'."""
    ps = [p for p in str(nome).split() if p.lower() not in ("team", "esports", "gaming", "club")] or [str(nome)]
    return ps[0][:9]


def slug(m: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "_", str(m).lower()).strip("_") or "x"


@lru_cache(maxsize=1)
def _indice() -> dict:
    try:
        return json.loads((RAIZ / "imagens_cs.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


@lru_cache(maxsize=2048)
def _uri(rel: str) -> str:
    if not rel:
        return ""
    try:
        dados = (RAIZ / rel).read_bytes()
    except OSError:
        return ""
    tipo = "image/png" if rel.endswith(".png") else "image/jpeg"
    return f"data:{tipo};base64," + base64.b64encode(dados).decode()


def logo(time_canonico: str | None) -> str:
    return _uri((_indice().get("times") or {}).get(time_canonico or "", ""))


def imagem_mapa(mapa: str) -> str:
    return _uri((_indice().get("mapas") or {}).get(mapa, ""))


def _odd(p: float) -> str:
    return f"{1 / p:.2f}" if p and p > 0 else "—"


def _pct(p: float) -> str:
    return f"{100 * p:.0f}%"


def _escudo(nome: str, canon: str | None, cor: str) -> str:
    u = logo(canon)
    if u:
        return f'<div class="escudo"><img src="{u}" alt=""></div>'
    ini = "".join(w[0] for w in str(nome).split()[:2]).upper() or "?"
    return f'<div class="escudo sem" style="border-color:{cor}">{escape(ini)}</div>'


CSS_ML = """
<style>
  .conf { border:1px solid var(--borda); border-radius:14px; background:var(--painel); padding:16px 18px 14px; }
  .conf-topo { display:grid; grid-template-columns:1fr auto 1fr; align-items:center; gap:14px; }
  .lado { display:flex; align-items:center; gap:12px; min-width:0; }
  .lado.dir { flex-direction:row-reverse; text-align:right; }
  .escudo { height:52px; min-width:52px; max-width:150px; display:flex; align-items:center; justify-content:center; }
  .escudo img { max-height:52px; max-width:150px; object-fit:contain; }
  .escudo.sem { width:52px; border:2px solid; border-radius:50%; font-weight:800; font-size:17px; }
  .nome { font-size:20px; font-weight:800; line-height:1.15; overflow-wrap:anywhere; }
  .rating { color:var(--fraco); font-size:12px; margin-top:3px; }
  .rating b { color:var(--texto); }
  .vs { color:var(--fraco); font-weight:700; font-size:13px; }
  .justos { display:grid; grid-template-columns:repeat(3, 1fr); gap:10px; margin-top:14px; }
  .tile { border:1px solid var(--linha); border-radius:10px; padding:8px 10px 9px; }
  .tile .t { font-size:11px; letter-spacing:.08em; text-transform:uppercase; color:var(--fraco); font-weight:700; }
  .tile .od { display:flex; justify-content:space-between; align-items:baseline; margin-top:4px; }
  .tile .od span { font-size:22px; font-weight:800; font-variant-numeric:tabular-nums; }
  .tile .bar { height:5px; border-radius:3px; margin-top:6px; background:@B@; overflow:hidden; }
  .tile .bar i { display:block; height:100%; background:@A@; }
  .tile .pc { display:flex; justify-content:space-between; color:var(--fraco); font-size:11.5px; margin-top:3px; }
  .ca { color:@A@; } .cb { color:@B@; }
  .mj { margin-top:4px; display:flex; flex-direction:column; gap:6px; }
  .mrow { display:grid; grid-template-columns:120px 1fr 150px 1fr; align-items:center; gap:12px;
          border:1px solid var(--linha); border-radius:10px; padding:6px 12px 6px 6px; }
  .mthumb { height:48px; border-radius:7px; background-size:cover; background-position:center; position:relative; }
  .mthumb b { position:absolute; left:8px; bottom:5px; color:#fff; font-size:13px; text-shadow:0 1px 3px #000; }
  .mlado { display:flex; align-items:baseline; gap:8px; font-variant-numeric:tabular-nums; }
  .mlado.dir { justify-content:flex-end; }
  .mlado .o { font-size:19px; font-weight:800; }
  .mlado .s { color:var(--fraco); font-size:12px; }
  .mmeio .bar { height:6px; border-radius:3px; background:@B@; overflow:hidden; }
  .mmeio .bar i { display:block; height:100%; background:@A@; }
  .mmeio .pc { display:flex; justify-content:space-between; font-size:11.5px; color:var(--fraco); margin-top:3px; }
  .forte { font-weight:800; }
  @media (max-width: 640px) { .justos { grid-template-columns:1fr; } .mrow { grid-template-columns:90px 1fr 1fr; }
                              .mmeio { display:none; } .nome { font-size:16px; } }
</style>
""" .replace("@A@", COR_A).replace("@B@", COR_B)


def html_confronto(j3: dict, j5: dict) -> str:
    """j3/j5: o mesmo confronto calculado por precos_core.calcular em MD3 e MD5. Topo com logos e rating,
    e as odds justas de ML: mapa (sem saber qual), serie MD3, serie MD5."""
    (ta, _), (tb, _) = j3["casou"]
    fa, fb = j3["fichas"]

    def lado(nome, canon, f, cor, classe):
        r = (f'<div class="rating">rating <b>{f["forca"]}</b> · {f["mapas_ano"]} mapas no ano · último {f["ultimo"]}</div>'
             if f else '<div class="rating">não achei nos dados</div>')
        return (f'<div class="lado {classe}">{_escudo(nome, canon, cor)}<div><div class="nome">{escape(nome)}</div>'
                f'{r}</div></div>')
    topo = ('<div class="conf-topo">' + lado(j3["casa"], ta, fa, COR_A, "") + '<div class="vs">×</div>'
            + lado(j3["fora"], tb, fb, COR_B, "dir") + "</div>")
    if not j3.get("precificado"):
        return CSS_ML + '<div class="conf">' + topo + "".join(
            f'<div class="aviso">{escape(a)}</div>' for a in j3.get("avisos") or []) + "</div>"

    def tile(titulo, p):
        return (f'<div class="tile"><div class="t">{titulo}</div><div class="od"><span class="ca">{_odd(p)}</span>'
                f'<span class="cb">{_odd(1 - p)}</span></div><div class="bar"><i style="width:{100 * p:.1f}%"></i></div>'
                f'<div class="pc"><span>{_pct(p)}</span><span>{_pct(1 - p)}</span></div></div>')
    p3 = j3["mercados"][0]["lados"][0]["p_modelo"]
    p5 = j5["mercados"][0]["lados"][0]["p_modelo"]
    tiles = ('<div class="justos">' + tile("Mapa (sem saber qual)", j3["p_mapa"]) + tile("Série MD3", p3)
             + tile("Série MD5", p5) + "</div>")
    avisos = "".join(f'<div class="aviso">{escape(a)} — o preço sai mesmo assim (medido), mas com menos base.</div>'
                     for a in j3.get("pouco_dado") or [])
    return CSS_ML + '<div class="conf">' + topo + tiles + avisos + "</div>"


def linhas_por_mapa(est, j: dict) -> list:
    """Uma linha por mapa do pool: a chance de A NAQUELE mapa (veto_cs.p_com_mapa, o mesmo do veto) e o
    retrospecto dos dois no ano. Ordenado do mapa mais a favor de A para o mais a favor de B."""
    if not j.get("precificado"):
        return []
    (ta, _), (tb, _) = j["casou"]
    ma, mb = j["mapas"]
    fora = []
    for m in sorted(getattr(est, "pool", []) or []):
        p = vc.p_com_mapa(est, ta, tb, m, j["p_mapa"])
        fora.append({"mapa": m, "p": p, "ano_a": (ma.get(m) or {}).get("ano", (0, 0)),
                     "ano_b": (mb.get(m) or {}).get("ano", (0, 0))})
    return sorted(fora, key=lambda x: -x["p"])


def html_mapas_justos(j: dict, linhas: list) -> str:
    if not linhas:
        return ""

    def rec(v):
        w, n = v
        return f"{w}-{n - w} no ano" if n else "sem jogo no ano"
    rows = []
    for l in linhas:
        p = l["p"]
        img = imagem_mapa(l["mapa"])
        fundo = f"background-image:url('{img}')" if img else "background:var(--cab)"
        rows.append(
            f'<div class="mrow"><div class="mthumb" style="{fundo}"><b>{escape(l["mapa"])}</b></div>'
            f'<div class="mlado"><span class="o ca {"forte" if p >= .5 else ""}">{_odd(p)}</span>'
            f'<span class="s">{_pct(p)} · {rec(l["ano_a"])}</span></div>'
            f'<div class="mmeio"><div class="bar"><i style="width:{100 * p:.1f}%"></i></div></div>'
            f'<div class="mlado dir"><span class="s">{rec(l["ano_b"])} · {_pct(1 - p)}</span>'
            f'<span class="o cb">{_odd(1 - p)}</span></div></div>')
    return (CSS_ML + f'<div class="nome-col">Odd justa por mapa — <span class="ca">{escape(j["casa"])}</span> × '
            f'<span class="cb">{escape(j["fora"])}</span></div><div class="mj">' + "".join(rows) + "</div>"
            '<div class="nota">Chance do mapa com o ajuste pela taxa de cada time NAQUELE mapa (o mesmo do veto: '
            'encolhida, peso pequeno — medido 26/10). Do mapa mais a favor do time da esquerda para o mais a favor '
            'do da direita.</div>')


def altura_mapas_justos(linhas: list) -> int:
    return 70 + 62 * len(linhas) + 50 if linhas else 0
