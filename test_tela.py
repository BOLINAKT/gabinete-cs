# -*- coding: utf-8 -*-
"""O desenho do app do CS: jogo precificado, nao precificado e lista de apostas."""
import unittest

import precos_core as pc
import tela_cs as tl


def _ficha(nome, novo=False):
    return {"time": nome, "forca": 1800, "elo_time": 1790, "mapas_ano": 90, "ultimo": "25/10/26",
            "dias_parado": 1, "elenco_conhecido": True,
            "jogadores": [{"jogador": "a", "nota": 1900, "entrou": "2026-10-13", "novo": novo, "visto": True}]}


def _jogo(precificado=True, novo=False):
    lados = [{"lado": "MIBR", "p_modelo": 0.6, "odd_modelo": 1 / 0.6, "p_pinnacle": 0.55, "odd_pinnacle": 1.9,
              "vantagem": 14.0},
             {"lado": "EF", "p_modelo": 0.4, "odd_modelo": 2.5, "p_pinnacle": 0.45, "odd_pinnacle": 2.0,
              "vantagem": -20.0}]
    return {"id": 1, "liga": "STK", "casa": "MIBR", "fora": "EF", "bo": 3, "inicio_utc": "2026-10-27T18:45:00Z",
            "ja_comecou": False, "casou": [], "fichas": [_ficha("MIBR", novo), _ficha("EF")],
            "precificado": precificado, "avisos": [] if precificado else ["EF: sem dado recente"],
            "mercados": [{"mercado": "Série", "periodo": 0, "lados": lados}] if precificado else [],
            "mapas": [{"Mirage": _mapa(4, 5, 0.4)}, {"Mirage": _mapa(1, 5, 0.0)}],
            "veto": {"pick_a": "Mirage", "ban_b": "Mirage"}, "qualificatoria": False}


def _mapa(v, n, parte):
    return {"w5": (v, n), "w10": (v, n), "w20": (v, n), "ano": (v, n), "saldo10": 1.5, "ultimo": "", "parte": parte}


class TestTela(unittest.TestCase):
    def test_hora_em_brasilia(self):
        self.assertEqual(tl.hora_br("2026-10-27T18:45:00Z"), "27/10 15:45")

    def test_jogo_precificado_tem_as_duas_colunas_e_verde_no_valor(self):
        h = tl.html_jogo(_jogo())
        self.assertIn("Modelo — odd justa", h)
        self.assertIn("Pinnacle — odd paga", h)
        self.assertIn('class="verde"', h)
        self.assertIn("+14,0%", h)

    def test_nao_precificado_mostra_o_motivo_e_nao_da_numero(self):
        h = tl.html_jogo(_jogo(precificado=False))
        self.assertIn("Não precificado", h)
        self.assertNotIn("odd justa", h)

    def test_jogador_novo_gera_aviso(self):
        self.assertIn("entrou nos últimos 60 dias", tl.html_jogo(_jogo(novo=True)))

    def test_melhores_fica_entre_1_e_20_e_ordena(self):
        lst = pc.melhores([_jogo()])
        self.assertEqual([x["lado"] for x in lst], ["MIBR"])
        self.assertIn("MIBR", tl.html_melhores(lst))


class TestMapas(unittest.TestCase):
    def test_tabela_pinta_alto_e_baixo_e_marca_pick_ban(self):
        h = tl.html_mapas(_jogo())
        self.assertIn('class="alto"', h)   # 4/5
        self.assertIn('class="baixo"', h)  # 1/5
        self.assertIn("pick?", h)
        self.assertIn("ban?", h)

    def test_veto_provavel_bane_o_menos_jogado(self):
        a = {"Mirage": _mapa(1, 1, 0.5), "Nuke": _mapa(1, 1, 0.0)}
        b = {"Mirage": _mapa(1, 1, 0.1), "Nuke": _mapa(1, 1, 0.6)}
        v = pc.veto_provavel(a, b)
        self.assertEqual((v["ban_a"], v["pick_a"], v["ban_b"], v["pick_b"]), ("Nuke", "Mirage", "Mirage", "Nuke"))

    def test_situacao_pelo_relogio_de_agora(self):
        import pandas as pd
        ini = "2026-10-26T14:15:00Z"
        self.assertEqual(pc.situacao(ini, pd.Timestamp("2026-10-26 14:00")), "a jogar")
        self.assertEqual(pc.situacao(ini, pd.Timestamp("2026-10-26 15:00")), "ao vivo")
        self.assertEqual(pc.situacao(ini, pd.Timestamp("2026-10-26 17:30")), "encerrado")

    def test_melhores_ignora_jogo_ao_vivo(self):
        j = _jogo()
        j["situacao"] = "ao vivo"
        self.assertEqual(pc.melhores([j]), [])

    def test_qualificatoria_pelo_nome_da_liga(self):
        self.assertTrue(pc.e_qualificatoria("BLAST Open Qualifier"))
        self.assertFalse(pc.e_qualificatoria("PGL Masters Bucharest"))


if __name__ == "__main__":
    unittest.main()


class TestMontarJogos(unittest.TestCase):
    def test_agenda_com_e_sem_pinnacle(self):
        import pandas as pd

        class E:   # Estado minimo: casa os nomes da Pinnacle pelo canonico
            def casar(self, nome):
                return ({"Liquid": "Team Liquid", "FURIA": "FURIA", "X": "X", "Y": "Y"}.get(nome), "exato")
        agenda = {"jogos": [
            {"pagina": "PGL/2026/Masters", "time1": "furia", "time2": "tl", "inicio_utc": "2026-10-28T14:00:00Z", "bo": 3},
            {"pagina": "PGL/2026/Masters", "time1": "mongolz", "time2": "nemiga", "inicio_utc": "2026-10-28T11:00:00Z", "bo": 3}]}
        odds = {"lido_em": "2026-10-28T08:00:00Z", "linhas": [], "jogos": [
            {"id": 7, "casa": "Liquid", "fora": "FURIA", "liga": "CS2 - PGL", "bo": 3, "inicio_utc": "2026-10-28T14:15:00Z"},
            {"id": 8, "casa": "X", "fora": "Y", "liga": "CS2 - STK", "bo": 3, "inicio_utc": "2026-10-28T15:00:00Z"}]}
        m = pc.montar_jogos(E(), agenda, odds, agora=pd.Timestamp("2026-10-28 08:00"))
        fontes = {(j["casa"], j["fonte"]) for j in m["jogos"]}
        self.assertIn(("Liquid", "liquipedia+pinnacle"), fontes)   # casou: usa o jogo da Pinnacle
        self.assertIn(("X", "pinnacle"), fontes)                   # so na Pinnacle: continua
        self.assertEqual(len(m["jogos"]), 3)                        # MongolZ x Nemiga entra sem odd

    def test_jogo_so_da_polymarket_entra(self):
        # 29/10/2026: Aurora Young Blud x DimoniX so existia na Polymarket
        import pandas as pd

        class E:
            def casar(self, nome):
                return ({"Liquid": "Team Liquid", "FURIA": "FURIA"}.get(nome), "exato")
        odds = {"lido_em": "2026-10-28T08:00:00Z", "linhas": [], "jogos": [
            {"id": 7, "casa": "Liquid", "fora": "FURIA", "liga": "CS2 - PGL", "bo": 3, "inicio_utc": "2026-10-28T14:15:00Z"}]}
        poly = {"partidas": [
            {"time_a": "Aurora Young Blud", "time_b": "DimoniX", "p_a": 0.68, "p_b": 0.32, "bo": 3,
             "torneio": "European Pro League", "inicio_utc": "2026-10-28T16:00:00Z", "evento": "cs2-ayb-dmx"},
            {"time_a": "FURIA", "time_b": "Liquid", "p_a": 0.55, "p_b": 0.45, "bo": 3,
             "torneio": "PGL", "inicio_utc": "2026-10-28T14:00:00Z", "evento": "cs2-fur-liq"}]}
        m = pc.montar_jogos(E(), {}, odds, agora=pd.Timestamp("2026-10-28 08:00"), poly=poly)
        self.assertEqual(len(m["jogos"]), 2)                        # FURIA x Liquid nao duplica
        so_poly = next(j for j in m["jogos"] if j["fonte"] == "polymarket")
        self.assertEqual(so_poly["casa"], "Aurora Young Blud")
        self.assertEqual(so_poly["poly"]["p_a"], 0.68)
        self.assertTrue(so_poly["estrito"])
        pin = next(j for j in m["jogos"] if j["fonte"] == "pinnacle")
        self.assertEqual(pin["poly"]["p_a"], 0.55)                  # o preco da Polymarket pendura no jogo


    def test_um_lado_exato_na_mesma_hora_e_o_mesmo_jogo(self):
        # 10/11/2026: "Toobisie" (Polymarket) = "Teletubisie" (Liquipedia), contra o 9INE Academy
        import pandas as pd

        class E:
            def casar(self, nome):
                return ({"9INE Academy": "9INE Academy", "Teletubisie": "Teletubisie"}.get(nome), "exato")
        odds = {"lido_em": "2026-11-11T08:00:00Z", "linhas": [], "jogos": [
            {"id": 9, "casa": "9INE Academy", "fora": "Teletubisie", "liga": "X", "bo": 3,
             "inicio_utc": "2026-11-11T09:00:00Z"}]}
        poly = {"partidas": [
            {"time_a": "Toobisie", "time_b": "9INE Academy", "p_a": 0.4, "p_b": 0.6, "bo": 3,
             "torneio": "X", "inicio_utc": "2026-11-11T09:00:00Z", "evento": "e1"},
            {"time_a": "9INE Academy", "time_b": "Outro", "p_a": 0.5, "p_b": 0.5, "bo": 3,
             "torneio": "X", "inicio_utc": "2026-11-11T15:00:00Z", "evento": "e2"}]}
        m = pc.montar_jogos(E(), {}, odds, agora=pd.Timestamp("2026-11-11 08:00"), poly=poly)
        self.assertEqual(len(m["jogos"]), 2)                       # o das 15h e outro jogo
        j = next(x for x in m["jogos"] if x["id"] == 9)
        self.assertTrue(j["poly"]["invertido"])                    # time_a da Polymarket e a fora
        self.assertEqual(j["poly"]["p_b"], 0.6)

    def test_lado_desconhecido_herda_o_nome_conhecido(self):
        import pandas as pd

        class E:
            def casar(self, nome):
                return ({"9INE Academy": "9INE Academy", "Teletubisie": "Teletubisie"}.get(nome), "exato")
        odds = {"lido_em": "2026-11-11T08:00:00Z", "linhas": [], "jogos": [
            {"id": 9, "casa": "9INE Academy", "fora": "Toobisie", "liga": "X", "bo": 3,
             "inicio_utc": "2026-11-11T09:00:00Z"}]}
        poly = {"partidas": [{"time_a": "9INE Academy", "time_b": "Teletubisie", "p_a": 0.6, "p_b": 0.4,
                              "bo": 3, "torneio": "X", "inicio_utc": "2026-11-11T09:30:00Z", "evento": "e1"}]}
        m = pc.montar_jogos(E(), {}, odds, agora=pd.Timestamp("2026-11-11 08:00"), poly=poly)
        self.assertEqual(len(m["jogos"]), 1)
        self.assertEqual((m["jogos"][0]["casa"], m["jogos"][0]["fora"]), ("9INE Academy", "Teletubisie"))
        self.assertFalse(m["jogos"][0]["poly"]["invertido"])

    def test_nome_parecido_nao_casa_na_polymarket(self):
        class E:
            def casar(self, nome):
                return ("Diamant Esports", "parecido") if "dimonix" in nome.lower() else (None, "sem time")
        self.assertIsNone(pc.casar_estrito(E(), "DimoniX Esports"))


class TestMelhorOddDasCasas(unittest.TestCase):
    def test_selo_melhor_na_maior_odd_de_cada_lado(self):
        import tela_cs as tl
        L = [{"mercado": "Série", "periodo": 0, "casa": c, "odd_casa": a, "odd_fora": b, "valor_pin_casa": 0.0,
              "valor_pin_fora": 0.0, "valor_mod_casa": None, "valor_mod_fora": None}
             for c, a, b in (("Pinnacle", 1.60, 2.70), ("Stake", 1.55, 2.50), ("Polymarket", 1.52, 2.62))]
        h = tl.html_outras_casas({"casa": "A", "fora": "B"}, L)
        self.assertEqual(h.count('class="top"'), 2)      # Stake 1,55 e Polymarket 2,62; Pinnacle nao conta
