# -*- coding: utf-8 -*-
"""LOGOS DOS TIMES E IMAGENS DOS MAPAS (25/11/2026). Ele: "mostrar os logos dos times" e, no veto, "clicar no
mapa em vez de clicar num nome".

Fonte: Liquipedia (o arquivo do infobox de cada time -- `imagedark`, senao `image` -- e as capas CS2_de_*.png
dos mapas). Respeita as regras dela: User-Agent proprio, 1 chamada a cada 2,1 s (o mesmo liquipedia.py),
consultas em lote de 50 titulos, e cada imagem e baixada UMA vez em miniatura (logo 48 px de altura, mapa
320x180) e fica em imagens/ -- a tela nunca bate na Liquipedia. Incremental: so busca o que falta.
Times: os que jogaram >= MIN_MAPAS mapas no ultimo ano.
Uso: py -3.13 imagens_cs.py [--max N]
"""
from __future__ import annotations

import io
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

import pandas as pd

import liquipedia as lq

RAIZ = Path(__file__).resolve().parent
PASTA = RAIZ / "imagens"
INDICE = RAIZ / "imagens_cs.json"
MIN_MAPAS = 10
ALTURA_LOGO = 48
MAPAS = {"Ancient": "CS2_de_ancient.png", "Anubis": "CS2_de_anubis.png", "Cache": "CS2_de_cache.png",
         "Dust II": "CS2_Dust_2_A_Site.jpg", "Inferno": "CS2_de_inferno.png", "Mirage": "CS2_de_mirage.png",
         "Nuke": "CS2_de_nuke.png", "Overpass": "CS2_de_overpass.png", "Train": "CS2_de_train.png",
         "Vertigo": "CS2_de_vertigo.png"}


def slug(nome: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", nome.lower()).strip("_") or "x"


def campo_logo(wikitexto: str) -> str:
    """Pura. O arquivo do logo no infobox: o do tema escuro (o app e escuro), senao o padrao."""
    achados = dict((k.lower(), v.strip()) for k, v in re.findall(r"\|\s*(imagedark|image)\s*=\s*([^\n|}]*)", wikitexto))
    return achados.get("imagedark") or achados.get("image") or ""


def _baixar(url: str) -> bytes:
    espera = lq.INTERVALO_S - (time.monotonic() - lq._ultima[0])
    if espera > 0:
        time.sleep(espera)
    req = urllib.request.Request(url, headers={"User-Agent": lq.UA})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return r.read()
    finally:
        lq._ultima[0] = time.monotonic()


def _miniatura(dados: bytes, destino: Path, tamanho) -> None:
    from PIL import Image
    im = Image.open(io.BytesIO(dados))
    if tamanho == "logo":
        im = im.convert("RGBA")
        w = max(1, round(im.width * ALTURA_LOGO / im.height))
        im.resize((min(w, 4 * ALTURA_LOGO), ALTURA_LOGO), Image.LANCZOS).save(destino, "PNG", optimize=True)
    else:
        im.convert("RGB").resize((320, 180), Image.LANCZOS).save(destino, "JPEG", quality=78, optimize=True)


def _urls(arquivos: list, **tam) -> dict:
    """{arquivo: url da miniatura}, em lotes de 50."""
    fora = {}
    for i in range(0, len(arquivos), 50):
        lote = arquivos[i:i + 50]
        d = lq.chamar(action="query", prop="imageinfo", iiprop="url", titles="|".join("File:" + a for a in lote), **tam)
        norm = {x["to"]: x["from"] for x in (d.get("query") or {}).get("normalized") or []}
        for p in (d.get("query") or {}).get("pages") or []:
            ii = (p.get("imageinfo") or [{}])[0]
            nome = norm.get(p["title"], p["title"])[5:]
            if ii.get("thumburl") or ii.get("url"):
                fora[nome] = ii.get("thumburl") or ii["url"]
    return fora


def times_ativos() -> list:
    import base_elo as be     # os nomes canonicos (= titulo da pagina na Liquipedia), os mesmos do app
    d = be.carregar(incluir_c=True)
    d = d[d.dt >= d.dt.max() - pd.Timedelta(days=365)]
    n = pd.concat([d.time1, d.time2]).value_counts()
    return sorted(n[n >= MIN_MAPAS].index)


def main() -> int:
    maximo = int(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else 10 ** 6
    (PASTA / "logos").mkdir(parents=True, exist_ok=True)
    (PASTA / "mapas").mkdir(parents=True, exist_ok=True)
    idx = json.loads(INDICE.read_text(encoding="utf-8")) if INDICE.exists() else {}
    idx.setdefault("times", {})
    idx.setdefault("sem_logo", {})
    idx.setdefault("mapas", {})
    idx["fonte"] = "Liquipedia (liquipedia.net), miniaturas baixadas uma vez"
    # mapas
    faltam = {m: a for m, a in MAPAS.items() if m not in idx["mapas"]}
    if faltam:
        urls = _urls(list(faltam.values()), iiurlwidth=320)
        for m, a in faltam.items():
            if a in urls:
                arq = PASTA / "mapas" / f"{slug(m)}.jpg"
                _miniatura(_baixar(urls[a]), arq, "mapa")
                idx["mapas"][m] = arq.relative_to(RAIZ).as_posix()
    # times
    times = [t for t in times_ativos() if t not in idx["times"] and t not in idx["sem_logo"]][:maximo]
    print(f"mapas: {len(idx['mapas'])} | times a buscar: {len(times)}")
    arquivo_de = {}
    for i in range(0, len(times), 50):
        lote = times[i:i + 50]
        d = lq.chamar(action="query", prop="revisions", rvprop="content", rvslots="main", redirects=1,
                      titles="|".join(lote))
        q = d.get("query") or {}
        volta = {x["to"]: x["from"] for x in (q.get("normalized") or [])}
        for x in q.get("redirects") or []:
            volta[x["to"]] = volta.get(x["from"], x["from"])
        for p in q.get("pages") or []:
            orig = volta.get(p["title"], p["title"])
            txt = ((p.get("revisions") or [{}])[0].get("slots") or {}).get("main", {}).get("content", "")
            a = campo_logo(txt)
            if a:
                arquivo_de[orig] = a
    urls = _urls(sorted(set(arquivo_de.values())), iiurlheight=ALTURA_LOGO * 2)
    for t in times:
        a = arquivo_de.get(t)
        if not a or a.replace(" ", "_") not in {k.replace(" ", "_") for k in urls}:
            idx["sem_logo"][t] = "sem pagina ou sem logo no infobox da Liquipedia"
            continue
        url = next(v for k, v in urls.items() if k.replace(" ", "_") == a.replace(" ", "_"))
        arq = PASTA / "logos" / f"{slug(t)}.png"
        try:
            _miniatura(_baixar(url), arq, "logo")
            idx["times"][t] = arq.relative_to(RAIZ).as_posix()
        except Exception as e:  # noqa: BLE001 -- uma imagem ruim nao derruba o resto
            idx["sem_logo"][t] = f"falhou ao baixar ({type(e).__name__})"
        if len(idx["times"]) % 25 == 0:
            INDICE.write_text(json.dumps(idx, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    INDICE.write_text(json.dumps(idx, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    print(f"logos: {len(idx['times'])} | sem logo: {len(idx['sem_logo'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
