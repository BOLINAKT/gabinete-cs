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
from urllib.parse import quote

LIQUI = "https://liquipedia.net/counterstrike/"
HLTV = "https://www.hltv.org/matches/"

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
  .sub2 { color:var(--fraco); font-size:11px; padding:10px 12px 4px; border-top:1px solid var(--borda); }
  .rrow { display:grid; grid-template-columns:0.7fr 1.6fr 1fr; padding:4px 12px; font-size:12px;
          border-top:1px solid var(--linha); align-items:center; }
  .rrow .fonte { text-align:right; font-size:11.5px; }
  a { color:var(--modelo); text-decoration:none; } a:hover { text-decoration:underline; }
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
    return ('<div class="status"><span><b>{}</b> jogos (Liquipedia + Pinnacle)</span><span><b>{}</b> precificados</span>'
            '<span><b>{}</b> apostas com valor</span><span>odds lidas <b class="{}">{}</b></span>'
            '<span>mapas até <b>{}</b></span></div>').format(
        jogos, precificados, com_valor, "velho" if odds_velhas else "", escape(idade_odds), escape(dados_ate))


def html_jogo(j) -> str:
    """Topo + Modelo | Pinnacle (serie e mapa a mapa) + avisos."""
    meta = "{} · BO{} · {}{}".format(j["liga"], j["bo"], hora_br(j["inicio_utc"]),
                                       {"ao vivo": " · AO VIVO — odds de antes do jogo",
                                        "encerrado": " · ENCERRADO"}.get(j.get("situacao"), ""))
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
    # (26/10 a noite) o aviso "qualificatoria: modelo mais fraco" saiu: com os tiers
    # corrigidos, qualificatoria nao e pior (B: 0,639 x 0,653 no evento principal).
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


def html_serie(j) -> str:
    """Handicap de mapas, total de mapas e placar exato: Modelo | Pinnacle, coerentes com a serie."""
    ms = j.get("mercados_serie") or []
    if not ms:
        return ""
    mod, pin = [], []
    for m in ms:
        mod.append('<div class="row"><div class="merc">{}</div>{}</div>'.format(escape(m["mercado"]), "".join(
            '<div><span class="pct">{}</span> <span class="odd">{}</span><span class="pct">{}</span></div>'.format(
                escape(l["rotulo"]), _odd(l["odd_modelo"]), _pct(l["p_modelo"])) for l in m["lados"])))
        cel = []
        for l in m["lados"]:
            if l["odd_pinnacle"] is None:
                cel.append('<div><span class="nada">sem linha</span></div>')
                continue
            v = l["vantagem"]
            cel.append('<div class="{}"><span class="odd">{}</span><span class="v {}">{}</span></div>'.format(
                "verde" if v > 0 else "", _odd(l["odd_pinnacle"]), "b" if v > 0 else "r",
                f"{v:+.1f}%".replace(".", ",")))
        pin.append('<div class="row"><div class="merc">{}</div>{}</div>'.format(escape(m["mercado"]), "".join(cel)))

    def coluna(classe, nome, linhas):
        return '<div class="coluna {}"><div class="nome-col">{}</div><div class="secao">{}</div></div>'.format(
            classe, nome, "".join(linhas))
    return ('<div class="colunas">' + coluna("c-mod", "Série — odd justa do modelo", mod)
            + coluna("c-pin", "Pinnacle — odd paga", pin) + "</div>"
            '<div class="nota">Tudo sai da mesma chance da série acima, com a forma do dia: os mapas de uma série '
            'andam juntos (quem está bem no dia tende a varrer), então o −1,5 do favorito vale mais que '
            'mapa × mapa.</div>')


def altura_serie(j) -> int:
    n = len(j.get("mercados_serie") or [])
    return (40 + 46 * n + 60) if n else 0


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
        rec = "".join(
            '<div class="rrow"><div>{}</div><div>{} <b>{}</b></div><div class="fonte">{}{}</div></div>'.format(
                escape(r["data"]), escape(r["adversario"]), escape(r["placar"]),
                '<a href="{}" target="_blank" title="{}">Liquipedia</a>'.format(
                    escape(LIQUI + quote(r["pagina"].replace(" ", "_"))), escape(r["pagina"])),
                ' · <a href="{}{}/x" target="_blank">HLTV</a>'.format(HLTV, r["hltv"]) if r["hltv"] else "")
            for r in f.get("recentes") or [])
        link_time = '<a href="{}" target="_blank">página do time</a>'.format(escape(LIQUI + quote(f["time"].replace(" ", "_"))))
        out.append(('<div class="ficha"><h3>{} <span class="nada">({})</span></h3><div class="sub">{}</div>{}'
                    '<div class="sub2">Últimos jogos nos NOSSOS dados — confira no HLTV se falta algum mais '
                    'recente · {}</div>{}</div>')
                   .format(escape(nome), escape(f["time"]), escape(sub), linhas or
                           '<div class="jrow"><div class="nada">sem elenco</div></div>', link_time,
                           rec or '<div class="rrow"><div class="nada">nenhum</div></div>'))
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


CSS_MAPAS = """
<style>
  .mapas { background:var(--painel); border:1px solid var(--borda); border-top:3px solid var(--modelo);
           border-radius:12px; overflow-x:auto; margin-top:14px; }
  .mt { width:100%; border-collapse:collapse; font-variant-numeric:tabular-nums; min-width:760px; }
  .mt th { background:var(--cab); font-size:11.5px; font-weight:700; padding:7px 4px; opacity:0.9; }
  .mt th.time { font-size:12.5px; letter-spacing:0.02em; }
  .mt td { border-top:1px solid var(--linha); text-align:center; padding:5px 4px; height:44px; }
  .mt td.mapa { font-weight:800; font-size:13.5px; border-left:1px solid var(--linha);
                border-right:1px solid var(--linha); min-width:96px; }
  .mt .p { font-weight:800; font-size:13.5px; display:block; }
  .mt .q { color:var(--fraco); font-size:10.5px; display:block; }
  .mt .alto { background:var(--verde-fundo); } .mt .alto .p { color:var(--boa); }
  .mt .baixo { background:rgba(201,115,106,0.12); } .mt .baixo .p { color:var(--ruim); }
  .mt .vazio .p { color:var(--fraco); font-weight:600; }
  .pk { font-size:10px; font-weight:800; border-radius:6px; padding:1px 5px; margin-left:4px; }
  .pk.pick { color:var(--boa); border:1px solid var(--verde-borda); }
  .pk.ban { color:var(--ruim); border:1px solid rgba(201,115,106,0.55); }
</style>
"""

_COLS = (("w5", "5"), ("w10", "10"), ("w20", "20"), ("ano", "ano"))


def _cel_wr(v, n) -> str:
    if not n:
        return '<td class="vazio"><span class="p">-</span><span class="q">0 jogos</span></td>'
    p = v / n
    cls = "" if n < 3 else ("alto" if p >= 0.6 else "baixo" if p <= 0.4 else "")
    return '<td class="{}"><span class="p">{:.0f}%</span><span class="q">{}/{}</span></td>'.format(cls, 100 * p, v, n)


def _cel_joga(f, tag) -> str:
    s = f["saldo10"]
    saldo = "" if s is None else "{:+.1f} rd".format(s).replace(".", ",")
    return '<td><span class="p">{:.0f}%{}</span><span class="q">{}</span></td>'.format(
        100 * f["parte"], tag, saldo)


def html_mapas(j) -> str:
    """Winrate de cada time em cada mapa do pool: ultimos 5/10/20 e no ano, quanto
    joga o mapa (pick/ban provavel) e o saldo medio de rounds nos ultimos 10."""
    ma, mb = j["mapas"]
    if not ma and not mb:
        return '<div class="nada">Sem dados de mapa destes times.</div>'
    pool = list(ma or mb)
    vt = j.get("veto") or {}

    def tag(m, lado):
        if vt.get("pick_" + lado) == m:
            return '<span class="pk pick">pick?</span>'
        if vt.get("ban_" + lado) == m:
            return '<span class="pk ban">ban?</span>'
        return ""
    sub = "".join("<th>{}</th>".format(r) for _, r in _COLS)
    cab = ('<tr><th class="time" colspan="5">{}</th><th></th><th class="time" colspan="5">{}</th></tr>'
           '<tr><th>joga</th>{}<th>Mapa</th>{}<th>joga</th></tr>').format(
        escape(j["casa"]), escape(j["fora"]), "".join(reversed([f"<th>{r}</th>" for _, r in _COLS])), sub)
    linhas = []
    for m in pool:
        fa, fb = (ma or {}).get(m), (mb or {}).get(m)
        esq = (_cel_joga(fa, tag(m, "a")) + "".join(_cel_wr(*fa[k]) for k, _ in reversed(_COLS))) if fa \
            else '<td colspan="5" class="vazio">-</td>'
        dir_ = ("".join(_cel_wr(*fb[k]) for k, _ in _COLS) + _cel_joga(fb, tag(m, "b"))) if fb \
            else '<td colspan="5" class="vazio">-</td>'
        linhas.append(f'<tr>{esq}<td class="mapa">{escape(m)}</td>{dir_}</tr>')
    return (CSS_MAPAS + '<div class="mapas"><table class="mt">' + cab + "".join(linhas) + "</table></div>"
            '<div class="nota"><b>Só jogos de CS2</b> (desde 27/09/2023). <b>5 / 10 / 20</b>: vitórias nos últimos 5, 10 e 20 jogos do time NAQUELE mapa; '
            '<b>ano</b>: últimos 365 dias. Verde ≥ 60%, vermelho ≤ 40% (com 3+ jogos). <b>joga</b>: quanto dos '
            'mapas do time nos últimos 6 meses foi esse — o que mais joga costuma ser o pick (<b>pick?</b>), o '
            'que menos joga o ban (<b>ban?</b>); embaixo, o saldo médio de rounds nos últimos 10. O veto real '
            'sai minutos antes do jogo: isto é palpite para ler a tabela. O modelo de odd NÃO usa o mapa (o '
            'ganho medido foi pequeno demais).</div>')


def html_veto(j, linhas, pagina) -> str:
    """Os mapas do veto: base | sabendo o mapa | Pinnacle, por time, e o resultado."""
    if not linhas:
        return '<div class="nada">Os mapas ainda não estão na Liquipedia (o veto sai minutos antes do jogo).</div>'
    cab = ('<tr><th>#</th><th>Mapa</th><th colspan="2">Modelo base</th><th colspan="2">Sabendo o mapa</th>'
           '<th colspan="2">Pinnacle (vantagem c/ mapa)</th><th>Resultado</th></tr>'
           '<tr><th></th><th></th>' + ('<th>{}</th><th>{}</th>'.format(escape(j["casa"]), escape(j["fora"])) * 3)
           + '<th></th></tr>')

    def pin(odd, v):
        if odd is None:
            return '<td class="vazio"><span class="p">-</span><span class="q">sem linha</span></td>'
        cls = "alto" if v > 0 else ""
        return '<td class="{}"><span class="p">{:.2f}</span><span class="q">{}</span></td>'.format(
            cls, odd, f"{v:+.1f}%".replace(".", ","))
    corpo = []
    for l in linhas:
        pb, pm = l["p_base"], l["p_mapa"]
        res = "" if not l["terminado"] else (escape(j["casa"]) if l["vencedor_a"] == 1 else escape(j["fora"]))
        corpo.append(
            '<tr><td>{}</td><td class="mapa">{}</td>'.format(l["n"], escape(l["mapa"]))
            + "".join('<td><span class="p o-mod">{:.2f}</span><span class="q">{:.0f}%</span></td>'.format(1 / p, 100 * p)
                      for p in (pb, 1 - pb, pm, 1 - pm))
            + pin(l["odd_a"], l["vant_mapa_a"]) + pin(l["odd_b"], l["vant_mapa_b"])
            + '<td>{}</td></tr>'.format(f"<b>{res}</b>" if res else '<span class="q">a jogar</span>'))
    return (CSS_MAPAS + '<div class="mapas"><table class="mt">' + cab + "".join(corpo) + '</table></div>'
            '<div class="nota">Fonte: Liquipedia ({}). <b>Sabendo o mapa</b>: a chance base ajustada pela taxa de cada '
            'time NAQUELE mapa (ajuste da validação, fraco de propósito). Na média ele quase não muda o número, '
            'mas com vantagem clara de mapa o base subestimou o time em ~3 pp no teste. Cada previsão é gravada '
            'antes do mapa e vai para o <b>Placar dos mapas</b>.</div>'.format(escape(pagina or "")))


def html_placar(pl) -> str:
    if not pl.get("n"):
        return ('<div class="nada">Ainda sem mapa com resultado ({} previsão(ões) esperando). Busque o veto antes '
                'do jogo e de novo depois que acabar — ou rode o coletor.</div>').format(pl.get("pendentes", 0))
    melhor = "sabendo o mapa" if pl["ll_mapa"] < pl["ll_base"] else "base"
    topo = ('<div class="status"><span><b>{}</b> mapas com resultado</span><span><b>{}</b> esperando</span>'
            '<span>logloss base <b>{:.4f}</b> · com mapa <b>{:.4f}</b></span><span>acerto base <b>{:.0%}</b> · '
            'com mapa <b>{:.0%}</b></span><span>à frente: <b>{}</b></span></div>').format(
        pl["n"], pl["pendentes"], pl["ll_base"], pl["ll_mapa"], pl["acerto_base"], pl["acerto_mapa"], melhor)
    linhas = "".join(
        '<tr><td>{}</td><td>{} × {}</td><td class="mapa">{}</td><td>{:.0%}</td><td>{:.0%}</td><td><b>{}</b></td></tr>'.format(
            hora_br(l.get("inicio_utc")), escape(l["time_a"]), escape(l["time_b"]), escape(l["mapa"]),
            l["p_base"], l["p_mapa"], escape(l["time_a"] if l["venceu_a"] else l["time_b"]))
        for l in sorted(pl["linhas"], key=lambda l: l.get("inicio_utc") or "", reverse=True)[:40])
    return (CSS_MAPAS + topo + '<div class="mapas"><table class="mt"><tr><th>Quando</th><th>Jogo</th><th>Mapa</th>'
            '<th>Base (casa)</th><th>C/ mapa (casa)</th><th>Venceu</th></tr>' + linhas + '</table></div>'
            '<div class="nota">Com poucos mapas, a diferença é sorte: o teste histórico (15 mil mapas) deu +0,0003 '
            'para o "sabendo o mapa". Este placar serve para ver se, ao vivo, a história se repete — leva '
            'centenas de mapas para dizer algo.</div>')


def altura_mapas(j) -> int:
    n = len(j["mapas"][0] or j["mapas"][1] or {})
    return 64 + 44 * max(n, 1) + 62


def _par_rounds(linhas):
    """Junta as duas pontas de cada linha (over/under, casa/fora) numa linha da tabela."""
    pares = {}
    for l in linhas:
        h = l["pontos"] * (-1 if (l["tipo"] == "spread" and l["lado"] == "away") else 1)
        pares.setdefault((l["mapa"], l["tipo"], str(l["time"]), h), []).append(l)
    ordem = {"spread": 0, "team_total": 1, "total": 2}
    return [sorted(v, key=lambda l: l["lado"] in ("under", "away")) for k, v in
            sorted(pares.items(), key=lambda kv: (kv[0][0], ordem[kv[0][1]], kv[0][2], kv[0][3])) if len(v) == 2]


def html_rounds(j, linhas) -> str:
    """Mercados de rounds por mapa: Pinnacle x modelo, com a vantagem do modelo."""
    if not linhas:
        return '<div class="nada">Sem linhas de rounds da Pinnacle para este jogo (ou jogo sem preço do modelo).</div>'
    casa, fora = escape(j["casa"]), escape(j["fora"])

    def nome(l):
        if l["tipo"] == "spread":
            return "Handicap de rounds", f"{casa} {l['pontos']:+.1f}".replace(".", ","),                 f"{fora} {-l['pontos']:+.1f}".replace(".", ",")
        if l["tipo"] == "team_total":
            quem = casa if l["time"] == "home" else fora
            return f"Rounds de {quem}", f"+{l['pontos']:.1f}".replace(".", ","), f"−{l['pontos']:.1f}".replace(".", ",")
        return "Total de rounds", f"+{l['pontos']:.1f}".replace(".", ","), f"−{l['pontos']:.1f}".replace(".", ",")

    def cel(l):
        v = l["vantagem"]
        cls = "alto" if (v > 0 and l["validado"]) else ""
        return ('<td class="{}"><span class="p o-pin">{:.2f}</span><span class="q">modelo {:.2f} · {}</span></td>'
                .format(cls, l["odd"], 1 / max(l["p_modelo"], 1e-6), f"{v:+.1f}%".replace(".", ",")))
    corpo = []
    for a, b in _par_rounds(linhas):
        merc, ra, rb = nome(a)
        aviso = "" if a["validado"] else ' <span class="pk ban" title="o modelo empata com a média histórica">média</span>'
        corpo.append('<tr><td>{}</td><td class="mapa" style="text-align:left">{}{}</td><td>{}</td>{}<td>{}</td>{}</tr>'.format(
            a["mapa"], merc, aviso, ra, cel(a), rb, cel(b)))
    return (CSS_MAPAS + '<div class="mapas"><table class="mt"><tr><th>Mapa</th><th>Mercado</th><th>Lado</th>'
            '<th>Pinnacle (modelo · vantagem)</th><th>Lado</th><th>Pinnacle (modelo · vantagem)</th></tr>'
            + "".join(corpo) + '</table></div>')


NOTA_ROUNDS = ('<div class="nota">Do placar exato pelas regras do CS2 (MR12, prorrogação MR3), a partir da chance do '
               'mapa. Teste 2024-07+ (11 mil mapas): <b>handicap e rounds de um time passam</b> na régua (+0,03 a '
               '+0,04 sobre a média histórica); <b>total de rounds e prorrogação não</b> (marcados "média": o modelo '
               'só repete a frequência histórica — ~45% dos mapas passam de 21,5). Verde só no que passou. A '
               'vantagem herda o modelo do mapa: se a força do time estiver errada (dado velho), ela também está.</div>')


def altura_rounds(linhas) -> int:
    return 50 + 47 * max(1, len(_par_rounds(linhas)))


def html_outras_casas(j, linhas) -> str:
    """As casas DELE x o preco justo da Pinnacle (e o modelo). Verde: paga mais que o
    justo da Pinnacle; estrela: o modelo TAMBEM ve valor."""
    if not linhas:
        return '<div class="nada">Nenhuma das suas casas tem este jogo na leitura atual (OddsPapi).</div>'

    # a MELHOR odd de cada lado entre as casas dele (28/10/2026, como no LoL e no Dota)
    melhor = {}
    for l in linhas:
        if l["casa"] != "Pinnacle":
            for lado in ("casa", "fora"):
                melhor[(l["periodo"], lado)] = max(melhor.get((l["periodo"], lado), 0.0), l[f"odd_{lado}"])

    def cel(odd, vp, vm, top):
        cls = "alto" if (vp is not None and vp > 0) else ""
        est = " ★" if (vp is not None and vp > 0 and vm is not None and vm > 0) else ""
        vp_txt = "-" if vp is None else f"{vp:+.1f}%".replace(".", ",")
        return ('<td class="{}"><span class="p">{:.2f}{}{}</span><span class="q">vs Pinnacle {}</span></td>'
                .format(cls, odd, est, ' <span class="top">melhor</span>' if top else "", vp_txt))

    def _top(l, lado):
        return l["casa"] != "Pinnacle" and l[f"odd_{lado}"] >= melhor.get((l["periodo"], lado), 99)
    corpo = "".join(
        '<tr><td>{}</td><td class="mapa" style="text-align:left">{}</td>{}{}</tr>'.format(
            escape(l["mercado"]), escape(l["casa"]),
            cel(l["odd_casa"], l["valor_pin_casa"], l["valor_mod_casa"], _top(l, "casa")),
            cel(l["odd_fora"], l["valor_pin_fora"], l["valor_mod_fora"], _top(l, "fora")))
        for l in sorted(linhas, key=lambda l: (l["periodo"], l["casa"] != "Pinnacle", l["casa"])))
    return (CSS_MAPAS + '<style>.top{{font-size:10px;font-weight:800;color:#2daac4;border:1px solid #2daac4;'
            'border-radius:6px;padding:0 4px;vertical-align:middle}}</style>'
            '<div class="mapas"><table class="mt"><tr><th>Mercado</th><th>Casa</th>'
            '<th>{}</th><th>{}</th></tr>'.format(escape(j["casa"]), escape(j["fora"])) + corpo + '</table></div>'
            '<div class="nota">Odds das suas casas (OddsPapi, de 3 em 3 h). <b>Verde</b>: a casa paga MAIS que o '
            'preço justo da Pinnacle (sem margem) — é aposta de valor pela régua do mercado. <b>★</b>: o modelo '
            'também vê valor nesse preço. A medição de qual dos dois acerta mais vem com os resultados.</div>')


def altura_melhores(n, limite=15) -> int:
    return 34 + 47 * max(1, min(n, limite)) + 70


def pagina(corpo: str) -> str:
    return "<!doctype html><html><head><meta charset='utf-8'>" + CSS + "</head><body>" + corpo + "</body></html>"
