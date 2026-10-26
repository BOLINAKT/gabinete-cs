# GabineteCS — modelo de CS2 (começo: 25/10/2026)

Roda no PC dele por enquanto (pedido dele). Pasta sem acento de propósito
(o acento no caminho já quebrou o LoL e o Dota — ver o CLAUDE.md do LoL).

## Passo 1 — de onde vêm os dados (sonda de 25/10/2026)

Duas sondas, uma chamada por fonte, User-Agent honesto:
`sonda_fontes_cs.py` → `sonda_fontes.json` e `sonda_fontes_cs_2.py` → `sonda_fontes_2.json`.

| fonte | respondeu daqui? | o que tem | termos |
|---|---|---|---|
| **bo3.gg** (API que o próprio site usa) | sim | **76.512 partidas** encerradas desde **15/06/2020**; por partida: times, placar, BO, torneio; **mapa a mapa**: nome do mapa, rounds (ex. 13×10), duração, demo | **NÃO LIDOS**: a página de termos é montada em JavaScript e não abriu por programa. Ele precisa ler no navegador antes de qualquer coleta. |
| **Liquipedia** (API MediaWiki) | sim, com gzip | resultados de torneios, em texto da wiki (mais trabalho para extrair) | lidos: grátis, **1 chamada a cada 2 s**, User-Agent com contato, gzip obrigatório, **citar a Liquipedia (CC-BY-SA 3.0)**, guardar em cache; páginas HTML por robô são **proibidas** (só a API) |
| **HLTV** | devolve o desafio do Cloudflare | a mais completa | robots.txt proíbe buscas filtradas de resultados/stats; o projeto público mais completo (CS2-Predictor) entra com cookie do Cloudflare — caminho frágil e de termos duvidosos |
| **Pinnacle** (a mesma API do coletor do LoL, esporte 12) | sim | **154 jogos de CS2** abertos (PGL Bucharest, Circuit X Curitiba, STK...) | o mesmo arranjo do LoL (sem chave, poucas chamadas) |
| csapi.de | conexão cortada | — | — |
| cs2-api.org, ggscore.net | página inicial abriu | prometem plano grátis (não conferido) | — |

## A régua a bater

[CS2-Predictor](https://github.com/ppxdpp17/CS2-Predictor) (aberto, ~3.000
partidas tier-1 desde out/2023, Elo + forma + confronto direto, teste nos 20%
mais recentes): **logloss 0,645 · Brier 0,226 · acerto 63%**. Não compara com
odds. Modelo nosso abaixo de 0,645 no mesmo tipo de teste = vale continuar.

## Decisão de 25/10/2026: Liquipedia

- **bo3.gg descartado**: o robots.txt deles diz `Disallow: /api/` para todos os
  robôs (a página de termos não tem texto legível por programa). Eles não querem
  robô na API, então não usamos — por melhor que o dado seja.
- **Liquipedia** (API MediaWiki, permitida nos termos): `liquipedia.py` faz o
  ritmo (1 chamada a cada 2,1 s), o User-Agent com contato, o gzip e o cache em
  disco (`cache/liquipedia/`). Cada partida traz cada mapa com os rounds por lado
  (CT/TR) e as prorrogações (`o1t1t`...), e o ID do HLTV.
- `extrator.py`: texto da wiki → uma linha por mapa. `coletor.py`: torneios S, A e
  B-Tier de 2020+ (1.023), com as subpáginas de fase → `mapas_cs.csv`.
  Teste com 5 torneios: 552 mapas em 72 s. Coleta inteira: ~4 h, retomável.
- **Fonte a citar sempre**: Liquipedia (CC-BY-SA 3.0).

## Próximo passo (antigo, antes da decisão acima)

1. Ele lê os termos do bo3.gg no navegador (bo3.gg/terms-of-use).
2. Se permitirem: baixar o histórico do bo3.gg devagar (1 chamada por segundo,
   guardando tudo em disco para nunca pedir duas vezes) e montar a tabela de
   mapas. Se não: Liquipedia pela API (mais lenta, mas permitida).
3. Primeiro modelo: o motor de ratings do LoL adaptado para mapas de CS, medido
   contra a régua acima e contra a Pinnacle.

## Dados coletados (26/10/2026)

`mapas_cs.csv`: **53.934 mapas** (jan/2020 → 25/10/2026, ~8 mil por ano, ~31 mil
séries; S 18,5 mil · A 10,4 mil · B 25 mil; 5.939 times). 5.561 com prorrogação.
Defeitos pequenos: 124 sem data, 21 "Default" (W.O.), 6 "Unknown" — ficam fora.
Atenção: até set/2023 é CS:GO (mapa a 16, MR15); CS2 vai a 13.

## Modelo de base: Elo por mapa (`base_elo.py`, 26/10/2026)

Prequencial (cada mapa previsto só com o passado). K escolhido em 2021-2023 (=40);
teste em 2024+ nunca usado para escolher.

| recorte (teste 2024+) | logloss mapa | logloss série | acerto série |
|---|---|---|---|
| S/A/B | 0,661 | 0,654 | 61,5% |
| S e A | 0,659 | 0,652 | 62,0% |
| S | 0,659 | **0,650** | 62,4% |
| S/A desde 06/2025 | — | 0,667 | 62,2% |

Régua externa (CS2-Predictor, tier-1): 0,645. **A base ainda não bate a régua.**
Ideias para o próximo passo, uma de cada vez e medidas: rating por MAPA (o pool
importa), esquecimento (peso maior no recente), separar CS:GO de CS2, força da
liga/tier, e a comparação com a Pinnacle.

## Rodada 1 de melhorias (`variantes.py`, 26/10/2026)

Mesmo protocolo; ganho pareado por série, régua da casa (ganho > 0,002, p < 0,05,
IC acima de 0). **K escolhido pelo logloss da SÉRIE na validação** (antes era o do
mapa): K = 24.

| ideia | S-Tier, teste 2024+ | veredito |
|---|---|---|
| base (K=24) | **0,6418** | — |
| ajuste por mapa | 0,6424 (−0,0006) | empate, reprovada |
| encolher ratings no início do CS2 | 0,6468 (−0,0050) | pior, reprovada |
| K maior no S-Tier | 0,6522 (−0,0104) | pior, reprovada |

Comparação com a régua externa (0,645, tier-1, CS2): S e A no CS2 inteiro (10/2023+)
**0,645** · S desde 06/2025 0,642 · S/A desde 06/2025 0,652. **Empatado com a régua**,
não melhor de forma clara (os recortes não são idênticos aos dele).
Próximas ideias: margem de vitória em ROUNDS (13×3 informa mais que 13×11) e a
comparação com a Pinnacle.

## O que os estudos dizem (pesquisa de 26/10/2026, fontes abertas)

1. **Margem de vitória no Elo ajuda.** Kovalchik (2020, International Journal of
   Forecasting) testou 4 formas de pôr a margem no Elo, em tênis com placar de
   sets/games (o análogo dos rounds do CS): **todas** previram melhor que o Elo de
   vitória/derrota, e só a forma **aditiva conjunta** deu ratings sem viés e com
   variância estável. → é a primeira coisa a testar, e nessa forma.
   https://ideas.repec.org/a/eee/intfor/v36y2020i4p1329-1341.html
   (G-Elo, Szczecinski: a mesma ideia modelando a margem discretizada —
   https://arxiv.org/abs/2010.11187)
2. **O teto de acerto do CS é baixo, e muita variável não ajuda.** UCT (≈11 mil
   partidas, 142 variáveis, XGBoost): 62,7% de acerto; muitas estatísticas a mais
   não melhoraram sobre poucas variáveis importantes; jogos **LAN** e **BO3** são
   mais previsíveis. https://open.uct.ac.za/items/26d92119-6b96-4af2-8408-232cb8f62200
   Lund (tese, 3 anos de dados): ~60%. → o nosso 62% já está no patamar.
3. **Bater a casa é difícil.** Lund comparou com as odds de várias casas num
   torneio: os modelos **não** superaram as casas (amostra pequena). O lucro do
   UCT é de back-test sem detalhes. Em apostas parimutuel de CS há o viés do
   favorito invertido (azarão mal precificado), mas isso não vale para a Pinnacle.
   https://lup.lub.lu.se/student-papers/record/9145457/file/9145459.pdf
   https://www.sciencedirect.com/science/article/abs/pii/S0167487020300660
4. **Veto de mapas é uma fonte pouco explorada:** os times escolhem e banem mapas de
   forma subótima (3.500 partidas, 25 mil decisões de veto).
   https://mihamerstan.github.io/pdfs/Bandit%20Modeling%20of%20Map%20Selection%20in%20CSGO.pdf

**Ordem que sai disso:** (1) margem em rounds na forma aditiva conjunta; (2) LAN ×
online e formato da série; (3) comparar com a Pinnacle cedo, porque é ela a régua
que importa; (4) veto, mais tarde (dá mais trabalho e o ganho é incerto).

## Rodada 2: margem em rounds, forma aditiva conjunta (`margem.py`, 26/10/2026) — ACEITA

s = a·vitória + (1−a)·fração de rounds; grade ampliada até achar o ótimo por dentro
(K=72, a=0,3), escolhido só na validação.

| previsão (teste 2024+) | antes | depois | ganho pareado | régua da casa |
|---|---|---|---|---|
| mapa S e A | 0,6566 | 0,6540 | +0,0026 [+0,0004; +0,0048] p=0,011 | passa |
| série S e A | 0,6438 | 0,6401 | +0,0037 [−0,0001; +0,0077] p=0,029 | por um fio |
| série S | 0,6418 | 0,6401 | +0,0017 | não |

Aceita (passa no mapa; na série, mesma direção). **Modelo atual: Elo com margem, K=72, a=0,3.**
Série S e A em 0,640 — abaixo da régua externa (0,645).

## Mapa conhecido (depois do veto) — `mapa_conhecido.py`

Taxa de vitória por mapa (encolhida): ganho +0,0006 no mapa, real (p≈0,045) mas
abaixo do mínimo da casa. Caso extremo (time com ≥75% no mapa, ≥15 jogos, modelo
≈50%): 404 jogos, o time ganhou 56% (o modelo dava 51%); com o adversário <50% no
mapa: 86 jogos, ganhou 63%. Efeito real nos extremos, pequeno na média. Retestar
SOBRE o modelo com margem, só para o mercado de mapa pós-veto.

## Plano (autonomia dada por ele em 26/10: "a odd mais precisa possível")
1. ✔ margem em rounds
2. taxa por mapa pós-veto, por cima da margem (só mercado de mapa)
3. LAN × online (a infobox do torneio na Liquipedia tem `type=`), formato da série
4. escalação (Liquipedia lista os jogadores; troca de jogador = time "novo")
5. **odds da Pinnacle de CS2**: começar a COLETAR já (sem histórico não há comparação)
6. depois: calibrar (Platt) e comparar com a Pinnacle no fechamento
