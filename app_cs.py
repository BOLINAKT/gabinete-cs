# -*- coding: utf-8 -*-
"""App do CS2: modelo x Pinnacle, jogo a jogo (26/10/2026).

Rodar:  streamlit run app_cs.py   (na pasta C:\\Gabinetes\\GabineteCS)

As odds chegam pelo robo do GitHub (odds_cs2.yml, de 3 em 3 h); o botao
"Atualizar odds" faz `git pull` (historico do robo) e le a Pinnacle NA HORA
(coletar_odds_cs.py --local, 2 chamadas); a tela usa a leitura mais nova. O modelo treina uma
vez por versao dos dados (cache) -- os mapas vem do coletor.py.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import base_elo as be
import liquipedia as lq
import placar_pinnacle as plp
import precos_core as pc
import rondas as rd
import tela_cs as tl
import veto_cs as vc

RAIZ = Path(__file__).resolve().parent
ODDS = RAIZ / "odds_cs2.json"
ODDS_LOCAL = RAIZ / "odds_cs2_local.json"
AGENDA = RAIZ / "agenda_cs.json"     # jogos da Liquipedia (robo, de 3 em 3 h)
CASAS = RAIZ / "odds_casas_cs2.json"  # outras casas (OddsPapi, robo de 3 em 3 h)
POLY = RAIZ / "polymarket_cs.json"    # jogos e precos da Polymarket (robo, de hora em hora)
HORAS_VELHA = 6
MIN_RELER = 30   # ao abrir, odds mais velhas que isto: le a Pinnacle sozinho (2 chamadas)

st.set_page_config(page_title="Gabinete CS2", page_icon="🎯", layout="wide")
st.markdown("""
<style>
  .block-container { padding-top: 1.6rem; }
  .st-key-gaveta_dia div[role="radiogroup"], .st-key-gaveta_jogo div[role="radiogroup"] { gap: 6px; }
  .st-key-gaveta_dia div[role="radiogroup"] > label, .st-key-gaveta_jogo div[role="radiogroup"] > label {
      background: rgba(255,255,255,0.035); border: 1px solid rgba(255,255,255,0.12); border-radius: 10px;
      padding: 6px 12px; margin: 0; }
  .st-key-gaveta_dia div[role="radiogroup"] > label:has(input:checked),
  .st-key-gaveta_jogo div[role="radiogroup"] > label:has(input:checked) {
      border-color: #2daac4; box-shadow: inset 0 0 0 1px #2daac4; }
  .st-key-gaveta_dia div[role="radiogroup"] > label > div:first-child,
  .st-key-gaveta_jogo div[role="radiogroup"] > label > div:first-child { display: none; }
</style>
""", unsafe_allow_html=True)


def _versao_dados() -> tuple:
    # precos_core.py entra: codigo novo do Estado com cache velho = atributo faltando
    return tuple((RAIZ / n).stat().st_mtime
                 for n in ("mapas_cs.csv", "elencos.csv", "times_canonicos.json", "precos_core.py"))


@st.cache_resource
def tabela_rounds() -> rd.Tabela:
    return rd.Tabela(pc.KAPPA_ROUNDS)


@st.cache_resource(show_spinner="Treinando o modelo nos mapas coletados...")
def estado(_versao: tuple) -> pc.Estado:
    return pc.Estado()


def _idade(iso: str) -> tuple:
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    h = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
    txt = f"há {h:.0f} h" if h >= 1 else f"há {h * 60:.0f} min"
    return f"{tl.hora_br(iso)} ({txt})", h > HORAS_VELHA, h


def _ler_pinnacle_agora() -> bool:
    import coletar_odds_cs as co
    if co.pausa_local_restante() > 0:      # 403 antes: nao bate de novo (usa o robo)
        return False
    r = subprocess.run([sys.executable, "coletar_odds_cs.py", "--local"], cwd=RAIZ,
                       capture_output=True, text=True, timeout=90)
    return r.returncode == 0


def _tem_odd(j) -> bool:
    return any(l["odd_pinnacle"] for m in j["mercados"] for l in m["lados"])


def _odds_mais_nova():
    """A leitura mais nova entre a do robo (git) e a local (botao)."""
    lidas = []
    for arq in (ODDS, ODDS_LOCAL):
        try:
            lidas.append(json.loads(arq.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            continue
    return max(lidas, key=lambda o: o.get("lido_em", "")) if lidas else None


def _dia(j) -> str:
    return tl.hora_br(j["inicio_utc"])[:5] or "?"


@st.cache_data(ttl=600, show_spinner=False)
def _placar_pinnacle(_versao: tuple) -> dict:
    return plp.placar(be.carregar(incluir_c=True), plp.carregar_registros())


def _aba_modelo_pinnacle() -> None:
    """A regua de verdade: previsao gravada a cada leitura (robo) x fechamento."""
    versao = tuple(f.stat().st_mtime for f in (RAIZ / "mapas_cs.csv", plp.PREV) if f.exists())
    pl = _placar_pinnacle(versao)
    st.caption("A cada leitura de odds (de 3 em 3 h) o robô grava a chance do modelo NAQUELE momento. Aqui: "
               "a última antes do jogo × a Pinnacle sem margem, nos jogos que já têm resultado.")
    if not pl["n"]:
        regs = plp.carregar_registros()
        st.info(f"Ainda sem jogo com resultado. Previsões gravadas até agora: {len(regs)}. "
                "O placar aparece conforme os jogos acontecem e o robô de dados traz os resultados.")
        return
    lo, hi = pl["ic_dif"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Mercados com resultado", pl["n"])
    c2.metric("Logloss modelo", f"{pl['ll_modelo']:.4f}")
    c3.metric("Logloss Pinnacle", f"{pl['ll_pinnacle']:.4f}")
    c4.metric("Apostas (vantagem 1–20%)", pl["apostas"],
              None if pl["roi"] is None else f"ROI {100 * pl['roi']:+.1f}% · {pl['lucro']:+.2f} u")
    st.caption(f"Vantagem do modelo sobre a Pinnacle no logloss: IC95 [{lo:+.4f}; {hi:+.4f}] — "
               "se o intervalo cruza o zero, ainda é sorte. Leva centenas de jogos para dizer algo.")
    df = pd.DataFrame([{"jogo": f"{l['casa']} × {l['fora']}", "mercado": l["mercado"],
                        "modelo (casa)": f"{l['p_modelo_casa']:.0%}", "Pinnacle (casa)": f"{l['p_pinnacle_casa']:.0%}",
                        "venceu": l["casa"] if l["venceu_casa"] else l["fora"],
                        "aposta": l["apostou"] or "", "lucro": round(l["lucro"], 2)}
                       for l in sorted(pl["linhas"], key=lambda l: l["inicio_utc"], reverse=True)])
    st.dataframe(df, hide_index=True, width="stretch")


def _bloco_polymarket(j) -> None:
    """O preco da Polymarket do jogo (do robo polymarket_cs.yml), na orientacao casa/fora."""
    pm = j.get("poly")
    if not pm or pm.get("p_a") is None:
        return
    pa, pb = (pm["p_b"], pm["p_a"]) if pm.get("invertido") else (pm["p_a"], pm["p_b"])
    if not (pa and pb):
        return
    liq = pm.get("liquidez")
    st.caption("**Polymarket (vencedor):** {} {:.2f} · {} {:.2f}{}{}".format(
        j["casa"], 1 / pa, j["fora"], 1 / pb,
        "" if pm.get("spread") is None else " · spread {:.0f} pontos".format(100 * pm["spread"]),
        "" if liq is None else " · liquidez US$ {:,.0f}".format(liq).replace(",", ".")
    ) + ("" if j.get("precificado") else " — o modelo não tem dados destes times: sem fair."))


def _bloco_outras_casas(est, j) -> None:
    try:
        casas = json.loads(CASAS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    linhas = pc.outras_casas(j, casas.get("jogos", []), est)
    st.markdown("##### Suas casas × Pinnacle")
    # 28/10/2026, ele: "so estou usando basicamente a stake e polymarket". A Pinnacle fica
    # sempre, como regua.
    nomes = [n for _, n in pc.MARCAS if n != "Pinnacle"]
    escolhidas = st.multiselect("Casas que você usa (a Pinnacle entra sempre, como régua)", nomes,
                                default=["Stake", "Polymarket"], key="cs_casas_escolhidas")
    linhas = [l for l in linhas if l["casa"] == "Pinnacle" or l["casa"] in escolhidas]
    # 15/11/2026: a OddsPapi da 250 leituras por mes -- 1 por dia. A idade da leitura fica a vista.
    try:
        _h = (pd.Timestamp.utcnow().tz_localize(None) - pd.Timestamp(casas["lido_em"]).tz_localize(None)).total_seconds() / 3600
        _quando = (pd.Timestamp(casas["lido_em"]).tz_convert("America/Sao_Paulo")).strftime("%d/%m %H:%M")
        if _h > 36:
            st.warning(f"As odds das suas casas (OddsPapi) estão paradas desde {_quando} — a cota grátis do mês acabou "
                       "e volta no dia 1º. A Polymarket acima e a Pinnacle seguem atualizadas pelos robôs próprios.")
        else:
            st.caption(f"Leitura das casas: {_quando} (Brasília), há {_h:.0f} h. Uma leitura por dia (cota grátis da OddsPapi).")
    except Exception:
        pass
    components.html(tl.pagina(tl.html_outras_casas(j, linhas)),
                    height=60 + 46 * max(1, len(linhas)) + 70, scrolling=False)


def _bloco_rounds(j, odds) -> None:
    # 15/11/2026: os rounds da Polymarket (handicap -3,5 e total 21,5 por mapa), pela odd de compra
    try:
        lp = pc.rounds_da_polymarket(j, tabela_rounds())
    except Exception:
        lp = []
    if lp:
        st.markdown("##### Rounds por mapa — Polymarket")
        components.html(tl.pagina(tl.html_rounds(j, lp, "Polymarket")), height=tl.altura_rounds(lp) + 10, scrolling=False)
        st.caption("Odd de compra na Polymarket (meio do livro + meio spread); mercados com o livro vazio não aparecem. "
                   "Verde só no handicap, que é o que o modelo prevê; o total de rounds fica marcado \"média\".")
    linhas = pc.rounds_do_jogo(j, odds["linhas"], tabela_rounds())
    if not linhas:
        return
    st.markdown("##### Rounds por mapa")
    princ = [l for l in linhas if not l["alternativa"]]
    alt = [l for l in linhas if l["alternativa"]]
    components.html(tl.pagina(tl.html_rounds(j, princ) + tl.NOTA_ROUNDS),
                    height=tl.altura_rounds(princ) + 80, scrolling=False)
    if alt:
        with st.expander(f"Linhas alternativas ({len(alt) // 2})"):
            components.html(tl.pagina(tl.html_rounds(j, alt)), height=tl.altura_rounds(alt), scrolling=False)


def _perto_do_jogo(j, agora=None) -> bool:
    """De 60 min antes ate 4 h depois do inicio: a janela em que o veto sai e os mapas rolam."""
    import pandas as pd
    try:
        ini = pd.Timestamp(str(j.get("inicio_utc") or "").replace(" ", "T"))
        ini = ini.tz_localize("UTC") if ini.tzinfo is None else ini
    except (ValueError, TypeError):
        return False
    agora = agora or pd.Timestamp.now(tz="UTC")
    return ini - pd.Timedelta(minutes=60) <= agora <= ini + pd.Timedelta(hours=4)


def _bloco_veto(est, j) -> None:
    """Mapas do veto. SUPER-LIVE (16/11/2026, ele: "gostaria que pegasse sozinho... posso digitar
    tranquilo"): perto do jogo (60 min antes a 4 h depois) a tela busca sozinha na Liquipedia, no
    maximo 1 vez a cada 5 min por jogo (as mesmas 1 a 4 leituras do botao, no ritmo de 2,1 s);
    se a Liquipedia ainda nao tiver, da para digitar os mapas."""
    import time as _t
    st.markdown("##### Mapas do veto")
    chave = f"veto_{j['id']}"
    pausa = lq.pausa_restante()
    ultimo = st.session_state.get(f"t_{chave}", 0.0)
    auto = (pausa <= 0 and j["precificado"] and _perto_do_jogo(j) and _t.time() - ultimo > 300
            and not (chave in st.session_state and st.session_state[chave][1] == "digitado"))
    c1, c2 = st.columns([1, 4])
    with c1:
        clicou = st.button("Buscar mapas do veto", key=f"b_{chave}", disabled=pausa > 0 or not j["precificado"],
                           help="Lê a página do torneio na Liquipedia agora (o veto sai minutos antes do jogo)")
    with c2:
        if pausa > 0:
            st.caption(f"A Liquipedia pediu pausa (429): liberado em {pausa / 60:.0f} min. Não insistimos.")
        elif not j["precificado"]:
            st.caption("Jogo sem preço do modelo: nada para comparar mapa a mapa.")
        else:
            st.caption("Perto do jogo (1 h antes até 4 h depois) a busca é sozinha, a cada 5 min; o botão força agora.")
    if clicou or auto:
        st.session_state[f"t_{chave}"] = _t.time()
        try:
            with st.spinner("Lendo a Liquipedia..."):
                v = vc.buscar_veto(est, j["casou"][0][0], j["casou"][1][0])
            linhas = vc.linhas_do_veto(est, j, v)
            novos = vc.registrar(j, linhas, v["pagina"]) if linhas else 0
            vc.registrar_resultados(j, linhas)
            st.session_state[chave] = (linhas, v["pagina"])
            if novos:
                st.toast(f"{novos} previsão(ões) de mapa gravada(s) para o placar")
        except lq.Pausado as e:
            st.warning(str(e))
        except Exception as e:  # rede: aviso, nunca derruba a tela
            st.warning(f"Não consegui ler a Liquipedia agora ({type(e).__name__}).")
    if j["precificado"]:
        _clicar_mapas(est, j, chave)
    if chave in st.session_state:
        linhas, pagina = st.session_state[chave]
        components.html(tl.pagina(tl.html_veto(j, linhas, pagina)),
                        height=110 + 46 * max(1, len(linhas)) + 70, scrolling=False)
        if linhas:
            bo = int(j.get("bo") or 3)
            ps = [float(l["p_mapa"]) for l in linhas]
            s0, s1 = vc.serie_com_mapas(est, j, [], bo), vc.serie_com_mapas(est, j, [l["mapa"] for l in linhas], bo)
            st.markdown(f"**Série MD{bo}** — {j['casa']}: antes do veto **{100 * s0:.0f}%** ({1 / s0:.2f}) → "
                        f"com estes mapas **{100 * s1:.0f}%** ({1 / s1:.2f}) · {j['fora']}: {1 / (1 - s1):.2f}"
                        + ("" if len(ps) >= bo else f" · mapas que faltam contam como o último conhecido"))


def _clicar_mapas(est, j, chave, dentro_de_expander: bool = True) -> list:
    """MAPAS POR CLIQUE NA IMAGEM (25/11/2026). Ele: "clicar no mapa em vez de clicar num nome". Cada mapa da
    pool e um cartao com a capa do mapa; cada clique anda: pick do time da esquerda -> pick do da direita ->
    ban -> decisivo -> nada. A borda tem a cor do time que pickou. A ordem M1, M2... e a ordem em que os picks
    foram marcados; o decisivo vai por ultimo. Devolve a sequencia [(mapa, quem)]."""
    import hashlib
    import tela_ml_cs as tm
    pool = sorted(getattr(est, "pool", []) or [])
    if not pool:
        return []
    ss = st.session_state
    h = hashlib.md5(str(chave).encode()).hexdigest()[:8]
    ordem = ss.setdefault(f"ord_{chave}", {})
    a_curto, b_curto = str(j["casa"])[:14], str(j["fora"])[:14]
    rot = {None: "", "A": f"Pick {tm.curto(j['casa'])}", "B": f"Pick {tm.curto(j['fora'])}", "ban": "Ban",
           "decisivo": "Decisivo"}
    cor = {None: "rgba(255,255,255,0.15)", "A": tm.COR_A, "B": tm.COR_B, "ban": "#6e7681", "decisivo": "#a371f7"}

    def clicou(m):
        k = f"mc_{chave}_{m}"
        ss[k] = tm.proximo_estado(ss.get(k))
        if ss[k] in ("A", "B"):
            ordem[m] = max(ordem.values(), default=0) + 1
        else:
            ordem.pop(m, None)

    css = []
    for m in pool:
        v = ss.get(f"mc_{chave}_{m}")
        img = tm.imagem_mapa(m)
        escuro = "0.78" if v == "ban" else "0.35"
        css.append(
            f'.st-key-mcard_{h}_{tm.slug(m)} button {{ height:96px; width:100%; border:3px solid {cor[v]} !important;'
            f' border-radius:12px; color:#fff; font-weight:800; text-shadow:0 1px 3px #000;'
            f' background:linear-gradient(rgba(0,0,0,{escuro}),rgba(0,0,0,{escuro})), url("{img}") center/cover; }}'
            f' .st-key-mcard_{h}_{tm.slug(m)} button:hover {{ filter:brightness(1.15); }}')
    st.markdown("<style>" + "".join(css) + "</style>", unsafe_allow_html=True)
    caixa = st.expander("Marcar os mapas — clique na imagem: pick da esquerda → pick da direita → ban → decisivo",
                        expanded=True) if dentro_de_expander else st.container()
    with caixa:
        colunas = st.columns(min(len(pool), 7))
        for i, m in enumerate(pool):
            v = ss.get(f"mc_{chave}_{m}")
            with colunas[i % len(colunas)]:
                st.button(f"{m}  \n{rot[v]}" if v else m, key=f"mcard_{h}_{tm.slug(m)}", on_click=clicou, args=(m,),
                          width="stretch")
        marcas = {m: ss.get(f"mc_{chave}_{m}") for m in pool}
        seq = vc.ordem_dos_mapas(marcas, ordem)
        if seq:
            st.caption("Ordem: " + " · ".join(f"M{n + 1} {m}" + (f" (pick {a_curto if q == 'A' else b_curto})" if q else
                                                                  " (decisivo)") for n, (m, q) in enumerate(seq)))
        if not dentro_de_expander:
            return seq
        if st.button("Usar estes mapas", key=f"u_{chave}", disabled=not seq):
            v = {"pagina": "digitado", "mapas": [{"n": n + 1, "mapa": m, "terminado": False, "vencedor_a": None}
                                                 for n, (m, _q) in enumerate(seq)]}
            linhas = vc.linhas_do_veto(est, j, v)
            novos = vc.registrar(j, linhas, "digitado") if linhas else 0
            ss[chave] = (linhas, "digitado")
            if novos:
                st.toast(f"{novos} previsão(ões) de mapa gravada(s) para o placar")
            st.rerun()
    return seq


@st.fragment
def _veto_pesquisa(est, j3, ta, tb) -> None:
    """Fragmento: o clique num mapa recarrega so este bloco (o app inteiro levava segundos)."""
    st.markdown("##### Veto")
    c1, _c2 = st.columns([2, 5])
    with c1:
        bo = st.segmented_control("Formato", [1, 3, 5], default=3, format_func=lambda b: f"MD{b}", key="pq_bo")
    seq = _clicar_mapas(est, j3, f"pq_{ta}_{tb}", dentro_de_expander=False) or []
    (ca, _), (cb, _) = j3["casou"]
    if seq:
        ps = [vc.p_com_mapa(est, ca, cb, m, j3["p_mapa"]) for m, _q in seq]
        s = vc.serie_com_mapas(est, j3, [m for m, _q in seq], int(bo or 3))
        st.markdown(" · ".join(f"**M{n + 1} {m}**: {ta} {1 / p:.2f} / {tb} {1 / (1 - p):.2f}"
                               for n, ((m, _q), p) in enumerate(zip(seq, ps))))
        st.markdown(f"**Série MD{bo} com estes mapas** — {ta} **{1 / s:.2f}** ({100 * s:.0f}%) · "
                    f"{tb} **{1 / (1 - s):.2f}** ({100 * (1 - s):.0f}%)"
                    + ("" if len(ps) >= int(bo or 3) else " · mapas que faltam contam como o último marcado"))


def _aba_pesquisar(est) -> None:
    """PESQUISA LIVRE (25/11/2026), como no LoL e no Dota: ele escolhe os dois times e ve o ML -- mapa, MD3, MD5,
    a odd justa em cada mapa da pool e, clicando nos mapas do veto, a serie com aqueles mapas. Os numeros saem
    do mesmo precos_core.calcular dos jogos da agenda (jogo montado na hora, sem odd de casa)."""
    import tela_ml_cs as tm
    ativos = sorted([t for t, dt in est.ult.items() if dt >= est.desde], key=lambda t: str(t).lower())
    c1, c2 = st.columns(2)
    ta = c1.selectbox("Time da esquerda", ativos, index=None, placeholder="Digite o nome do time...", key="pq_a")
    tb = c2.selectbox("Time da direita", ativos, index=None, placeholder="Digite o nome do time...", key="pq_b")
    if not ta or not tb:
        st.caption(f"Escolha os dois times ({len(ativos)} com jogo no último ano).")
        return
    if ta == tb:
        st.warning("Escolha dois times diferentes.")
        return
    agora = pd.Timestamp.utcnow().tz_localize(None)
    jogos = [{"id": f"pq{bo}", "casa": ta, "fora": tb, "bo": bo, "liga": "Pesquisa"} for bo in (3, 5)]
    j3, j5 = pc.calcular(est, {"lido_em": agora.isoformat(), "jogos": jogos, "linhas": []})
    components.html(tl.pagina(tm.html_confronto(j3, j5)), height=250 if j3.get("precificado") else 160,
                    scrolling=False)
    if not j3.get("precificado"):
        return
    linhas = tm.linhas_por_mapa(est, j3)
    components.html(tl.pagina(tm.html_mapas_justos(j3, linhas)), height=tm.altura_mapas_justos(linhas),
                    scrolling=False)
    _veto_pesquisa(est, j3, ta, tb)
    with st.expander("Elenco e rating de cada jogador"):
        n_j = max([len(f["jogadores"]) for f in j3["fichas"] if f] or [1])
        n_r = max([len(f.get("recentes") or []) for f in j3["fichas"] if f] or [1])
        components.html(tl.pagina(tl.html_fichas(j3)), height=140 + 34 * n_j + 29 * n_r, scrolling=False)
    with st.expander("Retrospecto de cada time em cada mapa"):
        components.html(tl.pagina(tl.html_mapas(j3)), height=tl.altura_mapas(j3), scrolling=False)


def main() -> None:
    st.title("Gabinete CS2")
    # FAIXA DE CONFIANCA (24/11/2026): ate que jogo a base vai e se a ultima coleta deu certo
    # (confianca_base_core.py, o mesmo do LoL/Dota; o robo grava status_coleta_cs.json em toda rodada).
    try:
        import confianca_base_core as _cb
        _cb.render_faixa(st, RAIZ, "cs")
    except Exception as _e:  # noqa: BLE001
        st.warning(f"A faixa de confiança da base não abriu ({type(_e).__name__}).")
    c1, c2 = st.columns([5, 1])
    with c2:
        if st.button("Atualizar odds", help="Lê a Pinnacle agora (2 chamadas) e puxa o histórico do robô"):
            subprocess.run(["git", "pull", "--ff-only", "-q"], cwd=RAIZ, capture_output=True, text=True)
            st.toast("Odds lidas agora" if _ler_pinnacle_agora() else
                     "A Pinnacle recusou o seu PC (pausa de 6 h, sem insistir) — usando a leitura do robô")
    odds = _odds_mais_nova()
    # Jogo que acabou SOME da Pinnacle: com leitura fresca, encerrado nao aparece.
    # Ao abrir com leitura velha, le sozinho -- uma vez por MIN_RELER, nao a cada clique.
    if odds is None or _idade(odds["lido_em"])[2] > MIN_RELER / 60:
        if st.session_state.get("_releu_em", 0) < datetime.now().timestamp() - MIN_RELER * 60:
            st.session_state["_releu_em"] = datetime.now().timestamp()
            with st.spinner("Lendo a Pinnacle..."):
                if _ler_pinnacle_agora():
                    odds = _odds_mais_nova()
    if odds is None:
        st.warning("Ainda não há odds coletadas. Clique em Atualizar odds.")
        return
    est = estado(_versao_dados())
    # Jogos da LIQUIPEDIA; odds da Pinnacle penduradas em quem ja tem mercado (27/10/2026)
    try:
        agenda = json.loads(AGENDA.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        agenda = {}
    # 29/10/2026: jogos que SO a Polymarket tem (o robo polymarket_cs.yml, de hora em hora)
    try:
        poly = json.loads(POLY.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        poly = {}
    jogos = pc.calcular(est, pc.montar_jogos(est, agenda, odds, poly=poly))
    melhores = pc.melhores(jogos)
    idade, velha, _ = _idade(odds["lido_em"])
    with c1:
        components.html(tl.pagina(tl.html_status(
            jogos=len(jogos), precificados=sum(j["precificado"] for j in jogos), com_valor=len(melhores),
            idade_odds=idade, dados_ate=est.fim.strftime("%d/%m %H:%M"), odds_velhas=velha)), height=34)

    # 25/11/2026, ele: "no de CS nao precisa" de Melhores apostas / Modelo x Pinnacle / Placar / Como ler
    aba_pesq, aba_jogos = st.tabs(["Pesquisar", "Jogos"])
    with aba_pesq:
        _aba_pesquisar(est)
    with aba_jogos:
        encerrados = [j for j in jogos if j["situacao"] == "encerrado"]
        if encerrados and not st.toggle(f"Mostrar {len(encerrados)} jogo(s) já encerrado(s)", value=False):
            jogos = [j for j in jogos if j["situacao"] != "encerrado"]
        if not jogos:
            st.info("Nenhum jogo de CS2 por vir nesta leitura. Clique em Atualizar odds.")
        else:
            dias = list(dict.fromkeys(_dia(j) for j in jogos))
            with st.container(key="gaveta_dia"):
                dia = st.radio("Dia", dias, horizontal=True, label_visibility="collapsed")
            do_dia = [j for j in jogos if _dia(j) == dia]
            # FILTRO POR CAMPEONATO (16/11/2026, ele: "para nao ficar assim [30 jogos soltos],
            # gostaria que fosse possivel filtrar por campeonato"). A escolha
            # vale para todos os dias (fica na sessao); campeonato sem jogo no dia nao aparece.
            def _camp(x):
                return x.get("liga") or "(sem campeonato)"
            contagem = {}
            for x in do_dia:
                contagem[_camp(x)] = contagem.get(_camp(x), 0) + 1
            camps = sorted(contagem, key=lambda c: (-contagem[c], c))
            guardados = st.session_state.setdefault("_camps_escolhidos", set())
            marcados = st.pills("Campeonato", camps, selection_mode="multi",
                                default=[c for c in camps if c in guardados],
                                format_func=lambda c: f"{c} ({contagem[c]})", key=f"camps_{dia}")
            st.session_state["_camps_escolhidos"] = (guardados - set(camps)) | set(marcados or [])
            # 17/11/2026 (ele: "deixe mostrando so o campeonato"): sem campeonato marcado, so os
            # botoes de campeonato; os jogos aparecem depois de escolher.
            if not marcados:
                st.caption("Escolha um ou mais campeonatos acima para ver os jogos.")
            else:
                do_dia = [x for x in do_dia if _camp(x) in marcados]
                rot = {j["id"]: "{} × {} · {}{}{}".format(
                    j["casa"], j["fora"], tl.hora_br(j["inicio_utc"])[6:],
                    {"ao vivo": " · AO VIVO", "encerrado": " · encerrado"}.get(j["situacao"], ""),
                    "" if j["precificado"] else " · sem preço") + (
                    "" if _tem_odd(j) or not j["precificado"] else " · sem odd ainda")
                       for j in do_dia}
                with st.container(key="gaveta_jogo"):
                    jid = st.radio("Jogo", list(rot), format_func=rot.get, horizontal=True,
                                   label_visibility="collapsed")
                j = next(x for x in do_dia if x["id"] == jid)
                n_av = len(j["avisos"]) + len(j.get("pouco_dado") or []) + sum(
                    bool([x for x in f["jogadores"] if x["novo"]]) + (not f["elenco_conhecido"])
                    + ((f["dias_parado"] or 0) > 14) for f in j["fichas"] if f) + bool(j.get("qualificatoria")) \
                    + bool(j.get("fonte_sem_mapas"))
                alt = 44 + (36 + 46 * len(j["mercados"]) + 26 if j["precificado"] else 0) + 46 * n_av + 52
                if j["precificado"]:
                    # 25/11/2026: o mesmo cartao da Pesquisa (logos, rating, justo do mapa/MD3/MD5) no topo
                    import tela_ml_cs as tm
                    _jj = [{"id": f"cf{bo}", "casa": j["casa"], "fora": j["fora"], "bo": bo, "liga": j["liga"]}
                           for bo in (3, 5)]
                    _j3, _j5 = pc.calcular(est, {"lido_em": pd.Timestamp.utcnow().tz_localize(None).isoformat(),
                                                 "jogos": _jj, "linhas": []})
                    if _j3.get("precificado"):
                        components.html(tl.pagina(tm.html_confronto(_j3, _j5)), height=250, scrolling=False)
                components.html(tl.pagina(tl.html_jogo(j)), height=alt, scrolling=False)
                _bloco_polymarket(j)
                _bloco_outras_casas(est, j)
                _bloco_veto(est, j)
                st.markdown("##### Mapas")
                components.html(tl.pagina(tl.html_mapas(j)), height=tl.altura_mapas(j), scrolling=False)
                n_j = max([len(f["jogadores"]) for f in j["fichas"] if f] or [1])
                n_r = max([len(f.get("recentes") or []) for f in j["fichas"] if f] or [1])
                components.html(tl.pagina(tl.html_fichas(j)), height=140 + 34 * n_j + 29 * n_r, scrolling=False)
                with st.expander("Como o time foi achado nos dados"):
                    for (t, como), nome in zip(j["casou"], (j["casa"], j["fora"])):
                        st.write(f"**{nome}** → {t or 'nada'} ({como})")


main()
