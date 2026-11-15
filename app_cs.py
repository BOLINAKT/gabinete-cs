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


def _bloco_veto(est, j) -> None:
    """Mapas do veto, sob demanda (botao): 1 a 4 leituras da Liquipedia sem cache."""
    st.markdown("##### Mapas do veto")
    chave = f"veto_{j['id']}"
    pausa = lq.pausa_restante()
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
            st.caption("Clique perto do horário do jogo; de novo depois que acabar, para o placar.")
    if clicou:
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
    if chave in st.session_state:
        linhas, pagina = st.session_state[chave]
        components.html(tl.pagina(tl.html_veto(j, linhas, pagina)),
                        height=110 + 46 * max(1, len(linhas)) + 70, scrolling=False)


def main() -> None:
    st.title("Gabinete CS2")
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

    aba_jogos, aba_melhores, aba_pin, aba_placar, aba_como = st.tabs(
        ["Jogos", "Melhores apostas", "Modelo × Pinnacle", "Placar dos mapas", "Como ler"])
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
                + ((f["dias_parado"] or 0) > 30) for f in j["fichas"] if f) + bool(j.get("qualificatoria"))
            alt = 44 + (36 + 46 * len(j["mercados"]) + 26 if j["precificado"] else 0) + 46 * n_av + 52
            components.html(tl.pagina(tl.html_jogo(j)), height=alt, scrolling=False)
            if j.get("mercados_serie"):
                components.html(tl.pagina(tl.html_serie(j)), height=tl.altura_serie(j), scrolling=False)
            _bloco_polymarket(j)
            _bloco_outras_casas(est, j)
            _bloco_rounds(j, odds)
            _bloco_veto(est, j)
            st.markdown("##### Mapas")
            components.html(tl.pagina(tl.html_mapas(j)), height=tl.altura_mapas(j), scrolling=False)
            n_j = max([len(f["jogadores"]) for f in j["fichas"] if f] or [1])
            n_r = max([len(f.get("recentes") or []) for f in j["fichas"] if f] or [1])
            components.html(tl.pagina(tl.html_fichas(j)), height=140 + 34 * n_j + 29 * n_r, scrolling=False)
            with st.expander("Como o time foi achado nos dados"):
                for (t, como), nome in zip(j["casou"], (j["casa"], j["fora"])):
                    st.write(f"**{nome}** → {t or 'nada'} ({como})")
    with aba_melhores:
        # 15/11/2026 (Fases 4 e 6): primeiro o que da para apostar NAS CASAS DELE
        st.markdown("##### Nas suas casas (Polymarket e Stake)")
        try:
            import apostas_cs as ap
            try:
                _casas = json.loads(CASAS.read_text(encoding="utf-8"))
                _h = (pd.Timestamp.utcnow().tz_localize(None) - pd.Timestamp(_casas["lido_em"]).tz_localize(None)).total_seconds() / 3600
                _casas_jogos = _casas.get("jogos", []) if _h <= 36 else []
            except (OSError, ValueError, KeyError):
                _casas_jogos = []
            _tab = tabela_rounds()
            _c = []
            for _j in jogos:
                if not _j.get("precificado"):
                    continue
                _c += ap.candidatos(_j, pc.rounds_da_polymarket(_j, _tab),
                                    pc.outras_casas(_j, _casas_jogos, est) if _casas_jogos else None)
            _m = ap.melhores_nas_casas(_c)
            components.html(tl.pagina(tl.html_melhores_casas(_m)), height=tl.altura_melhores(min(len(_m), 25)) + 40,
                            scrolling=True)
            if not _casas_jogos:
                st.caption("A Stake está fora desta lista: a leitura da OddsPapi está parada (a cota grátis volta no dia 1º).")
        except Exception as _e:
            st.caption(f"Lista das suas casas indisponível agora ({type(_e).__name__}).")
        st.markdown("##### Na Pinnacle (modelo × Pinnacle)")
        components.html(tl.pagina(tl.html_melhores(melhores)), height=tl.altura_melhores(len(melhores)))
    with aba_pin:
        _aba_modelo_pinnacle()
    with aba_placar:
        pl = vc.placar(est.d)
        n = min(len(pl.get("linhas", [])), 40)
        components.html(tl.pagina(tl.html_placar(pl)), height=150 + 45 * n + (40 if n else 0))
    with aba_como:
        st.markdown("""
**Modelo** — Elo por jogador: cada jogador tem uma nota que leva de time em time; a força do time é a
média do elenco de hoje (Liquipedia). Série: chance do mapa encolhida por uma calibração MÓVEL (o c dos
últimos 12 meses — hoje o modelo pede bastante encolhimento), combinada em BO3/BO5. Teste honesto 2024+,
jogos S/A/B (o universo com odd): mapa logloss 0,651, acerto 62%; série 0,632. Por tier: S 0,652, A 0,667
(o mais difícil), B 0,647. Os dados se atualizam sozinhos todo dia (robô no GitHub, 06:41).

**Não precificado** — time com menos de 30 mapas no último ano ou parado há mais de 120 dias.

**Cuidado com vantagem grande** — elenco novo (o jogador traz a nota do time anterior), time sem jogo
recente nos nossos dados (pode ter jogado torneio que não coletamos), ou mapa: a Pinnacle sabe o mapa
depois do veto, o modelo não. A conferência de verdade vem com os resultados, que o robô vai acumulando.
""")


main()
