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

## Rodada 3 (26/10/2026, tarde) — tudo SOBRE o modelo de margem, mapa S/A, teste 2024+

| ideia | script | escolhido na validação | ganho pareado | régua |
|---|---|---|---|---|
| desvio do time por mapa | `mapa_sobre_margem.py` | K_mapa=10 | +0,0005 [−0,0001; +0,0012] | não |
| taxa por mapa encolhida | `mapa_sobre_margem.py` | m=20, peso 0,2 | +0,0007 [+0,0003; +0,0011] p=0,001 | não (real, pequeno) |
| K próprio para LAN/online | `lan_online.py` | K igual (72/72) | 0 | não |
| desvio do time LAN/online | `lan_online.py --desvio` | K_d=20 | −0,0002 | não |
| encolher após pausa longa | `pausa_e_estreia.py` | meia-vida 120 d, 20% | −0,0048 | não (piora) |
| nota de estreia por tier | `pausa_e_estreia.py` | 0 em todos | 0 | não |
| calibração simétrica c·logit | `calibracao.py` | c=1,2 | mapa +0,0013; série −0,0007 | não |

Tipo LAN/online lido do cache (infobox `type=`), sem chamada nova: 10.517 mapas LAN, 43.266 online.

**Achado (não adotado): a ORDEM da Liquipedia carrega informação.** No teste, o time1
ganha 56,2% dos mapas e o modelo dava 52,9%; uma calibração com intercepto (b=0,1)
passa na régua (+0,0029), mas o ganho é quase todo o intercepto. O time1 da
Liquipedia costuma ser o cabeça de chave / quem vem da chave de cima — dado de
antes do jogo, mas só utilizável se soubermos essa ordem para o jogo que formos
precificar (a Pinnacle tem casa/fora próprios). Caminho: virar uma variável
explícita (seed / chave de cima) quando houver a lista de próximos jogos da
Liquipedia; não usar a ordem crua.

Robô de odds (`odds_cs2.yml`): primeira corrida 26/10 14:21 UTC — 9 jogos, 1.385 linhas
(moneyline, spread, total, team_total, série e mapa a mapa). Daqui a semanas: comparar
o modelo com a Pinnacle no fechamento.

## BUG DOS NOMES corrigido (26/10/2026) — `resolver_times.py`, `times_canonicos.json`

A Liquipedia escreve o time pelo nome curto do modelo, e ele mudou com o tempo:
"liquid" → "tl", "vitality" → "vit", "gamerlegion" → "gl", "eternal fire" → "ef",
"fnatic" → "fnc". O Elo tratava cada troca como time NOVO e jogava fora o histórico.
Cura: `{{Team|nome}}` da própria Liquipedia diz a página do time (expandtemplates,
lotes de 80, 75 chamadas). 702 nomes fundidos. NÃO fundidos (de propósito):
"Orgless", elencos femininos, sub-elencos de seleção (`base_elo.canonico`).

**Tudo antes desta seção foi medido com o bug.** Com os nomes certos (teste 2024+):

| modelo | série S | série S e A | mapa S e A |
|---|---|---|---|
| Elo K=24, nomes crus (antes) | 0,6418 | 0,6438 | 0,6566 |
| Elo K=24, nomes certos | 0,6348 | 0,6378 | 0,6526 |
| margem K=72 a=0,3, nomes certos | 0,6344 | 0,6351 | 0,6510 |

A correção dos nomes valeu mais que qualquer ideia testada (série −0,006). A
margem, com nomes certos, ganha +0,0016 no mapa (p=0,088) e +0,0027 na série S/A
(p=0,10): **não passa mais na régua → modelo oficial volta a ser o Elo K=24** (K de
novo o melhor na validação). As rodadas 2 e 3 precisam ser medidas de novo sobre
os nomes certos (pendente).

## Preços do dia — `precificar_cs.py` → `precos_cs2.json`

Odd justa do modelo (série e mapa) × Pinnacle sem margem, para os jogos do robô.
Casamento de nomes aparece na tela para conferir. Lado sem 30+ mapas no último
ano ou parado há mais de 120 dias: NÃO precificado (Elo sem base). Primeira
leitura (26/10): 6 de 9 jogos precificados; o modelo foi mais "favorito" que a
Pinnacle em quase todos (MIBR +10 pp, Astralis +10 pp) — anotar para conferir
com os resultados.

## Rodada 4: ELENCO (26/10/2026) — `elencos.py`, `troca_elenco.py`, `elo_jogador.py` — ACEITA

Elencos com datas das páginas de time da Liquipedia (`{{Squad}}`/`{{Person}}`,
joindate/leavedate/inactivedate; blocos `type=staff` fora — o "Presidente do
Conselho" do MIBR contava como jogador desde 2021). 16 chamadas de 50 páginas;
12.990 passagens de jogador em 440 times; 79% das aparições S/A com elenco.

| ideia | escolhido na validação | mapa S/A | série S | série S/A | régua |
|---|---|---|---|---|---|
| encolher o time na troca | nada (f=0) — encolher piora | 0 | 0 | 0 | não |
| **Elo por jogador** (leva a nota ao mudar de time) | w=0, kj=32 | +0,0058 [+0,0036; +0,0082] | +0,0073 [+0,0025; +0,0119] | +0,0084 [+0,0039; +0,0128] | **passa** |
| + calibração da série (c·logit do mapa) | c=0,9 | — | +0,0021 [+0,0011; +0,0031] | +0,0022 [+0,0013; +0,0031] | **passa** (só série) |
| calibração do mapa | c=0,95 | +0,0004 | — | — | não |

**Modelo oficial agora:** força do time = média das notas dos jogadores do elenco
atual (sem elenco conhecido: Elo do time, K=24); série com c=0,9. Teste 2024+:
**mapa 0,6468 · série S 0,6253 · série S/A 0,6272** (régua externa 0,645 → abaixo).

Por que encolher na troca piora e o Elo por jogador ganha: quem troca costuma
trocar para melhor — o que informa é QUEM chegou, e a nota dele vem junto.

Calibração (antes do c=0,9): série BO3 favorito 70-80% previsto 0,748 → real
0,686; 80-90% 0,847 → 0,776. Mapas não são independentes.

## Plano (autonomia dada por ele em 26/10: "a odd mais precisa possível")
1. ✔ margem em rounds
2. ✘ taxa por mapa pós-veto (real, +0,0007, abaixo da régua)
3. ✘ LAN × online; ✘ pausa/estreia
4. ✔ elenco: Elo por jogador (aceito) + calibração da série (aceita)
5. ✔ robô de odds da Pinnacle coletando de 3 em 3 h
6. ✘ calibração simétrica; seed/ordem = próximo candidato; comparar com a Pinnacle quando houver odds
