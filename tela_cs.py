# -*- coding: utf-8 -*-
"""O desenho do app do CS, no tema da "Linha justa" do LoL (26/10/2026).

Mesmo CSS e mesmas cores do app do LoL (modelo_mercado_html_core): cartoes
escuros, borda de cima colorida por fonte, ODDS no formato da casa, verde onde
o modelo ve valor. modelo #2daac4 · Pinnacle #d9a441 · valor #3fb950.
So HTML (puro, testavel); o app so monta a pagina.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from html import escape

CSS = """
<style>
  :root { --texto:#e6e6e6; --fraco:#9aa0a6; --painel:rgba(255,255,255,0.035);
          --borda:rgba(255,255,255,0.12); --cab:rgba(255,255,255,0.06); --linha:rgba(255,255,255,0.07);
          --modelo:#2daac4; --pin:#d9a441; --boa:#3fb950; --ruim:#c9736a;
          --verde-fundo:rgba(63,185,80,0.14); --verde-borda:rgba(63,185,80,0.55); }
  @media (prefers-color-scheme: light) {
    :root { --texto:#1f2328; --fraco:#6a737d; --painel:rgba(0,0,0,0.025); --borda:rgba(0,0,0,0.12);
            --cab:rgba(0,0,0,0.045); --linha:rgba(0,0,0,0.07); }
  }
  * { box-sizing:border-box; }
  body { margin:0; background:transparent; color:var(--texto);
         font-family:"Source Sans Pro","Segoe UI",Arial,sans-serif; font-size:13.5px; }
  .status { color:var(--fraco); font-size:12px; padding:2px 2px 10px; display:flex; gap:14px; flex-wrap:wrap; }
  .status b { color:var(--texto); font-weight:700; }
  .status .velho { color:var(--pin); }
  .topo { display:flex; align-items:baseline; gap:12px; flex-wrap:wrap; padding:0 2px 10px; }
  .topo .times { font-size:19px; font-weight:800; }
  .topo .meta { color:var(--fraco); font-size:12.5px; }
  .colunas { display:flex; gap:14px; align-items:flex-start; flex-wrap:wrap; }
  .coluna { flex:1 1 300px; min-width:260px; }
  .nome-col { font-weight:800; letter-spacing:0.07em; font-size:12px; padding:0 2px 6px; text-transform:uppercase; }
  .c-mod .nome-col { color:var(--modelo); } .c-pin .nome-col { color:var(--pin); }
  .secao { background:var(--painel); border:1px solid var(--borda); border-top:3px solid var(--modelo);
           border-radius:12px; overflow:hidden; }
  .c-pin .secao { border-top-color:var(--pin); }
  .cab, .row { display:grid; grid-template-columns:0.9fr 1fr 1fr; }
  .cab { background:var(--cab); font-weight:700; font-size:11.5px; opacity:0.85; }
  .cab div { padding:7px 6px; text-align:center; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .row { border-top:1px solid var(--linha); }
  .row > div { min-height:45px; display:flex; align-items:center; justify-content:center; gap:7px; }
  .row > div + div { border-left:1px solid var(--linha); }
  .row .merc { color:var(--fraco); font-size:12.5px; justify-content:flex-start; padding-left:12px; }
  .odd { font-weight:800; }
  .c-mod .odd { color:var(--modelo); } .c-pin .odd { color:var(--pin); }
  .pct { color:var(--fraco); font-size:11px; }
  .verde { background:var(--verde-fundo); box-shadow:inset 0 0 0 1px var(--verde-borda); }
  .v { font-size:11px; font-weight:700; } .v.b { color:var(--boa); } .v.r { color:var(--ruim); }
  .nada { color:var(--fraco); font-size:11.5px; }
  .nota { color:var(--fraco); font-size:11.5px; padding:8px 2px 0; line-height:1.45; }
  .aviso { margin-top:10px; font-size:12.5px; padding:7px 10px; border-radius:8px;
           border:1px solid rgba(217,164,65,0.55); color:var(--pin); }
  .fichas { display:flex; gap:14px; flex-wrap:wrap; margin-top:14px; }
  .ficha { flex:1 1 300px; min-width:260px; background:var(--painel); border:1px solid var(--borda);
           border-radius:12px; overflow:hidden; }
  .ficha h3 { margin:0; padding:10px 12px 2px; font-size:13.5px; }
  .ficha .sub { color:var(--fraco); font-size:11.5px; padding:0 12px 8px; }
  .jrow { display:grid; grid-template-columns:1.4fr 0.8fr 1fr; border-top:1px solid var(--linha);
          padding:6px 12px; align-items:center; font-variant-numeric:tabular-nums; }
  .jrow .n { font-weight:800; color:var(--modelo); text-align:right; }
  .jrow .e { color:var(--fraco); font-size:11.5px; text-align:right; }
  .tag { font-size:10.5px; font-weight:800; border-radius:6px; padding:1px 6px; margin-left:6px;
         color:var(--pin); border:1px solid rgba(217,164,65,0.55); }
  .lista { background:var(--painel); border:1px solid var(--borda); border-top:3px solid var(--modelo);
           border-radius:12px; overflow:hidden; }
  .lcab, .lrow { display:grid; grid-template-columns: 2.2fr 0.9fr 1.6fr 0.8fr 0.8fr 0.9fr;
                 align-items:center; column-gap:10px; padding:0 14px; }
  .lcab { background:var(--cab); font-weight:700; font-size:11.5px; opacity:0.85; height:34px; }
  .lrow { border-top:1px solid var(--linha); height:47px; }
  .lrow b { font-size:13.5px; display:block; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .lrow .sub { color:var(--fraco); font-size:11px; display:block; white-space:nowrap; }
  .lrow .fraco { color:var(--fraco); font-size:12.5px; }
  .lrow .aposta { font-weight:800; font-size:14px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .c { text-align:center; }
  .o-pin { color:var(--pin); } .o-mod { color:var(--modelo); }
  .badge { font-weight:800; font-size:12px; color:var(--boa); background:var(--verde-fundo);
           border:1px solid var(--verde-borda); border-radius:8px; padding:2px 8px; }
</style>
"""


def hora_br(iso) -> str:
    """'2026-10-27T18:45:00Z' -> '27/10 15:45' (Brasilia, UTC-3)."""
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        if dt.utcoffset() is not None:
            dt = (dt - dt.utcoffset()).replace(tzinfo=None)
        return (dt - timedelta(hours=3)).strftime("%d/%m %H:%M")
    except (TypeError, ValueError):
        return ""


def _odd(x) -> str:
    return "-" if x is None or x <= 1 else f"{x:.2f}"


def _pct(p) -> str:
    return "" if p is None else f"{100 * p:.0f}%"


def html_status(*, jogos, precificados, com_valor, idade_odds, dados_ate, odds_velhas=False) -> str:
    return ('<div class="status"><span><b>{}</b> jogos na Pinnacle</span><span><b>{}</b> precificados</span>'
            '<span><b>{}</b> apostas com valor</span><span>odds lidas <b class="{}">{}</b></span>'
            '<span>mapas até <b>{}</b></span></div>').format(
        jogos, precificados, com_valor, "velho" if odds_velhas else "", escape(idade_odds), escape(dados_ate))


def html_jogo(j) -> str:
    """Topo + Modelo | Pinnacle (serie e mapa a mapa) + avisos."""
    meta = "{} · BO{} · {}{}".format(j["liga"], j["bo"], hora_br(j["inicio_utc"]),
                                       " · já tinha começado na leitura" if j["ja_comecou"] else "")
    html = '<div class="topo"><span class="times">{} × {}</span><span class="meta">{}</span></div>'.format(
        escape(j["casa"]), escape(j["fora"]), escape(meta))
    if not j["precificado"]:
        return html + "".join('<div class="aviso">Não precificado — {}.</div>'.format(escape(a))
                              for a in j["avisos"]) + (
            '<div class="nota">Sem 30+ mapas no último ano ou parado há mais de 120 dias, a nota do '
            'time não tem base: o modelo prefere não dar número.</div>')
    cab = '<div class="cab"><div></div><div>{}</div><div>{}</div></div>'.format(escape(j["casa"]), escape(j["fora"]))
    mod, pin = [], []
    for m in j["mercados"]:
        a, b = m["lados"]
        mod.append('<div class="row"><div class="merc">{}</div>{}{}</div>'.format(
            escape(m["mercado"]),
            *('<div><span class="odd">{}</span><span class="pct">{}</span></div>'.format(
                _odd(l["odd_modelo"]), _pct(l["p_modelo"])) for l in (a, b))))
        cel = []
        for l in (a, b):
            if l["odd_pinnacle"] is None:
                cel.append('<div><span class="nada">sem linha</span></div>')
                continue
            v = l["vantagem"]
            cel.append('<div class="{}"><span class="odd">{}</span><span class="v {}">{}</span></div>'.format(
                "verde" if v > 0 else "", _odd(l["odd_pinnacle"]), "b" if v > 0 else "r",
                f"{v:+.1f}%".replace(".", ",")))
        pin.append('<div class="row"><div class="merc">{}</div>{}</div>'.format(escape(m["mercado"]), "".join(cel)))

    def coluna(classe, nome, linhas):
        return ('<div class="coluna {}"><div class="nome-col">{}</div><div class="secao">{}{}</div></div>'
                .format(classe, nome, cab, "".join(linhas)))
    html += '<div class="colunas">' + coluna("c-mod", "Modelo — odd justa", mod) \
        + coluna("c-pin", "Pinnacle — odd paga", pin) + "</div>"
    for f, nome in zip(j["fichas"], (j["casa"], j["fora"])):
        novos = [x["jogador"] for x in f["jogadores"] if x["novo"]]
        if novos:
            html += ('<div class="aviso">{}: {} entrou nos últimos 60 dias — a nota dele vem do time '
                     'anterior e pode não valer aqui.</div>').format(escape(nome), escape(", ".join(novos)))
        if not f["elenco_conhecido"]:
            html += '<div class="aviso">{}: elenco desconhecido na Liquipedia — força = Elo do time.</div>'.format(
                escape(nome))
        if (f["dias_parado"] or 0) > 30:
            html += '<div class="aviso">{}: último mapa nos nossos dados em {} ({} dias) — pode ter jogado ' \
                    'torneio que não coletamos.</div>'.format(escape(nome), f["ultimo"], f["dias_parado"])
    html += ('<div class="nota">Modelo: a odd justa (1/chance) e a chance. Pinnacle: a odd que ela paga e a '
             'vantagem do modelo nesse preço (chance do modelo × odd − 1). Verde: o modelo vê valor. Mapa: '
             'o modelo não sabe qual mapa é — a Pinnacle sabe depois do veto.</div>')
    return html


def html_fichas(j) -> str:
    out = []
    for f, nome in zip(j["fichas"], (j["casa"], j["fora"])):
        if not f:
            out.append('<div class="ficha"><h3>{}</h3><div class="sub">não achei nos dados</div></div>'.format(
                escape(nome)))
            continue
        sub = "força {} · {} mapas no ano · último {}".format(f["forca"], f["mapas_ano"], f["ultimo"])
        linhas = "".join(
            '<div class="jrow"><div>{}{}</div><div class="n">{}</div><div class="e">desde {}</div></div>'.format(
                escape(x["jogador"]), '<span class="tag">novo</span>' if x["novo"] else "",
                x["nota"], escape(x["entrou"] or "?")) for x in f["jogadores"])
        out.append('<div class="ficha"><h3>{} <span class="nada">({})</span></h3><div class="sub">{}</div>{}</div>'
                   .format(escape(nome), escape(f["time"]), escape(sub), linhas or
                           '<div class="jrow"><div class="nada">sem elenco</div></div>'))
    return ('<div class="fichas">' + "".join(out) + '</div><div class="nota">Nota de cada jogador: o Elo '
            'que ele leva de time em time. A força do time é a média do elenco de hoje.</div>')


def html_melhores(lista, limite=15) -> str:
    if not lista:
        return '<div class="nada">Nenhuma aposta com vantagem entre 1% e 20% nesta leitura.</div>'
    cab = ('<div class="lcab"><div>Jogo</div><div>Mercado</div><div>Aposta</div><div class="c">Pinnacle</div>'
           '<div class="c">Modelo</div><div class="c">Vantagem</div></div>')
    corpo = "".join(
        ('<div class="lrow"><div><b>{} × {}</b><span class="sub">{} · {}</span></div><div class="fraco">{}</div>'
         '<div class="aposta">{}</div><div class="c"><span class="odd o-pin">{}</span></div>'
         '<div class="c"><span class="odd o-mod">{}</span></div><div class="c"><span class="badge">{}</span>'
         '</div></div>').format(
            escape(x["jogo"]["casa"]), escape(x["jogo"]["fora"]), escape(x["jogo"]["liga"]),
            escape(hora_br(x["jogo"]["inicio_utc"])), escape(x["mercado"]), escape(x["lado"]),
            _odd(x["odd_pinnacle"]), _odd(x["odd_modelo"]), f"{x['vantagem']:+.1f}%".replace(".", ","))
        for x in lista[:limite])
    return ('<div class="lista">' + cab + corpo + '</div><div class="nota">Vantagem acima de 20% fica de fora: '
            'quase sempre é dado errado (elenco novo, time trocado), não presente. Jogo já começado também.</div>')


def altura_melhores(n, limite=15) -> int:
    return 34 + 47 * max(1, min(n, limite)) + 70


def pagina(corpo: str) -> str:
    return "<!doctype html><html><head><meta charset='utf-8'>" + CSS + "</head><body>" + corpo + "</body></html>"
