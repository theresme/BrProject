# Ratings contextuais de institutos

O rating nacional continua sendo o fallback do modelo. Quando ha evidencia
local auditavel, uma disputa especifica pode substituir esse fallback por um
rating de UF/cargo.

Quando uma disputa tem matriz local, institutos sem historico local naquela
UF/cargo nao recebem automaticamente um rating nacional alto. Eles entram com
fallback neutro/conservador (`min(rating nacional, 0,60)`) ate haver evidencia
local comparavel.

## Senador PR

Base usada para `senador-pr`:

- Resultado oficial: TSE/Dados Abertos, `votacao_candidato_munzona_2022.zip`,
  arquivo `votacao_candidato_munzona_2022_PR.csv`, cargo `Senador`, 1o turno.
- Pesquisas comparadas: ultima rodada disponivel antes do 1o turno de 2022 na
  pagina "Eleicoes estaduais no Parana em 2022", secao `Pesquisas de opiniao >
  Senador`.
- Verita: relatorio publico do proprio instituto, "Previsoes 1o turno x
  resultados das urnas", pagina 61.

Resultado oficial em votos validos:

| Candidato | Oficial |
| --- | ---: |
| Sergio Moro | 33,50 |
| Paulo Martins | 29,12 |
| Alvaro Dias | 23,94 |

Metodologia:

1. Pesquisas com indecisos/outros foram normalizadas para votos validos entre
   candidatos.
2. O erro-base e o MAE dos tres primeiros da urna: Moro, Paulo Martins e Alvaro
   Dias.
3. Formula: `rating = 1 - MAE_top3 / 15`, com piso `0,40`.
4. Se a pesquisa errou o vencedor, o rating fica limitado a `0,50`.

Resultado aplicado:

| Instituto | MAE top-3 | Vencedor correto | Rating |
| --- | ---: | :---: | ---: |
| Verita | 1,83 | sim | 0,88 |
| IRG | 4,01 | sim | 0,73 |
| Parana Pesquisas | 6,11 | sim | 0,59 |
| Ipec | 10,01 | nao | 0,40 |
| Radar | 9,54 | nao | 0,40 |

Fontes:

- TSE/Dados Abertos: https://dadosabertos.tse.jus.br/dataset/resultados-2022
- Pagina historica de pesquisas: https://pt.wikipedia.org/wiki/Elei%C3%A7%C3%B5es_estaduais_no_Paran%C3%A1_em_2022
- Relatorio Verita: https://eleicoes.institutoverita.com.br/wp-content/uploads/2022/10/Previsoes-1o-turno-x-resultados-das-urnas.pdf

## Alteracoes registradas

2026-06-10, Codex:

- Criou ratings contextuais para `senador-pr` com base no desempenho das
  ultimas pesquisas de 2022 contra o resultado oficial.
- Fez o modelo usar rating contextual por `race_id` quando existir matriz local.
- Em disputas com matriz local, institutos sem evidencia naquela UF/cargo usam
  fallback neutro em vez de herdar automaticamente rating nacional alto.
- Adicionou `pesosPorDisputa` na API para a interface exibir pesos da corrida
  selecionada.
- Atualizou a aba Senado para propagar a UF selecionada ao painel de pesos.
- Atualizou o painel de pesos com selos `local` e `neutro`.
- Corrigiu o carregamento inicial da aba Senado para evitar renderizacao sem UF
  selecionada.

Coautor: Codex.
