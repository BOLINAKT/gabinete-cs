# -*- coding: utf-8 -*-
"""App do CS2: modelo x Pinnacle, jogo a jogo (26/10/2026).

Rodar:  streamlit run app_cs.py   (na pasta C:\\Gabinetes\\GabineteCS)

As odds chegam pelo robo do GitHub (odds_cs2.yml, de 3 em 3 h); o botao
"Atualizar odds" so faz `git pull --ff-only` desta pasta. O modelo treina uma
vez por versao dos dados (cache) -- os mapas vem do coletor.py.
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import precos_core as pc
import tela_cs as tl

RAIZ = Path(__file__).resolve().parent
ODDS = RAIZ / "odds_cs2.json"
HORAS_VELHA = 6

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


@st.cache_resource(show_spinner="Treinando o modelo nos mapas coletados...")
def estado(_versao: tuple) -> pc.Estado:
    return pc.Estado()


def _idade(iso: str) -> tuple:
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    h = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
    txt = f"há {h:.0f} h" if h >= 1 else f"há {h * 60:.0f} min"
    return f"{tl.hora_br(iso)} ({txt})", h > HORAS_VELHA


def _dia(j) -> str:
    return tl.hora_br(j["inicio_utc"])[:5] or "?"


def main() -> None:
    st.title("Gabinete CS2")
    c1, c2 = st.columns([5, 1])
    with c2:
        if st.button("Atualizar odds", help="Puxa do GitHub o que o robô coletou (git pull)"):
            r = subprocess.run(["git", "pull", "--ff-only", "-q"], cwd=RAIZ, capture_output=True, text=True)
            st.toast("Odds atualizadas" if r.returncode == 0 else f"git pull falhou: {r.stderr.strip()[:200]}")
    if not ODDS.exists():
        st.warning("Ainda não há odds coletadas (odds_cs2.json). Clique em Atualizar odds.")
        return
    odds = json.loads(ODDS.read_text(encoding="utf-8"))
    est = estado(_versao_dados())
    jogos = pc.calcular(est, odds)
    melhores = pc.melhores(jogos)
    idade, velha = _idade(odds["lido_em"])
    with c1:
        components.html(tl.pagina(tl.html_status(
            jogos=len(jogos), precificados=sum(j["precificado"] for j in jogos), com_valor=len(melhores),
            idade_odds=idade, dados_ate=est.fim.strftime("%d/%m %H:%M"), odds_velhas=velha)), height=34)

    aba_jogos, aba_melhores, aba_como = st.tabs(["Jogos", "Melhores apostas", "Como ler"])
    with aba_jogos:
        if not jogos:
            st.info("A Pinnacle não tem jogo de CS2 nesta leitura.")
        else:
            dias = list(dict.fromkeys(_dia(j) for j in jogos))
            with st.container(key="gaveta_dia"):
                dia = st.radio("Dia", dias, horizontal=True, label_visibility="collapsed")
            do_dia = [j for j in jogos if _dia(j) == dia]
            rot = {j["id"]: "{} × {} · {}{}".format(j["casa"], j["fora"], tl.hora_br(j["inicio_utc"])[6:],
                                                     "" if j["precificado"] else " · sem preço")
                   for j in do_dia}
            with st.container(key="gaveta_jogo"):
                jid = st.radio("Jogo", list(rot), format_func=rot.get, horizontal=True,
                               label_visibility="collapsed")
            j = next(x for x in do_dia if x["id"] == jid)
            n_av = len(j["avisos"]) + sum(
                bool([x for x in f["jogadores"] if x["novo"]]) + (not f["elenco_conhecido"])
                + ((f["dias_parado"] or 0) > 30) for f in j["fichas"] if f) + bool(j.get("qualificatoria"))
            alt = 44 + (36 + 46 * len(j["mercados"]) + 26 if j["precificado"] else 0) + 46 * n_av + 52
            components.html(tl.pagina(tl.html_jogo(j)), height=alt, scrolling=False)
            st.markdown("##### Mapas")
            components.html(tl.pagina(tl.html_mapas(j)), height=tl.altura_mapas(j), scrolling=False)
            n_j = max([len(f["jogadores"]) for f in j["fichas"] if f] or [1])
            components.html(tl.pagina(tl.html_fichas(j)), height=110 + 34 * n_j, scrolling=False)
            with st.expander("Como o time foi achado nos dados"):
                for (t, como), nome in zip(j["casou"], (j["casa"], j["fora"])):
                    st.write(f"**{nome}** → {t or 'nada'} ({como})")
    with aba_melhores:
        components.html(tl.pagina(tl.html_melhores(melhores)), height=tl.altura_melhores(len(melhores)))
    with aba_como:
        st.markdown("""
**Modelo** — Elo por jogador: cada jogador tem uma nota que leva de time em time; a força do time é a
média do elenco de hoje (Liquipedia). Série: chance do mapa, encolhida (os mapas não são independentes),
combinada em BO3/BO5. Teste honesto 2024+: série S/A logloss 0,627 (régua externa 0,645).

**Não precificado** — time com menos de 30 mapas no último ano ou parado há mais de 120 dias.

**Cuidado com vantagem grande** — elenco novo (o jogador traz a nota do time anterior), time sem jogo
recente nos nossos dados (pode ter jogado torneio que não coletamos), ou mapa: a Pinnacle sabe o mapa
depois do veto, o modelo não. A conferência de verdade vem com os resultados, que o robô vai acumulando.
""")


main()
