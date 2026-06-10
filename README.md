# Média 2026 · agregador de pesquisas — Brasil

Painel editorial (estilo agregador do FiveThirtyEight/Poder360) para a corrida
presidencial brasileira de **2026**. Junta as pesquisas de intenção de voto
**registradas no TSE**, mostra as últimas publicadas e, em cima, um **modelo
matemático próprio** que faz a média ponderando o desempenho histórico de cada
instituto — deixando sempre claro que **a média NÃO é uma pesquisa, é um
modelo**.

```
brasil-needle/
├── backend/        FastAPI: fontes + cruzamento TSE + modelo + /api/state
│   ├── config.py   << TODA a configuração (ratings, parâmetros do modelo)
│   ├── model.py    << a média ponderada em 2 passadas (o "coração")
│   ├── sources/    << fontes plugáveis: wikipedia.py, tse.py, mock.py
│   └── main.py     << API + loop de atualização + cache
└── frontend/       React + Vite + Tailwind (gráfico SVG custom)
```

## De onde vêm os dados (importante)

- **Resultados (percentuais)**: o TSE registra as pesquisas no PesqEle mas
  **não publica os números**. A fonte de resultados é a página
  [Opinion polling for the 2026 Brazilian presidential election](https://en.wikipedia.org/wiki/Opinion_polling_for_the_2026_Brazilian_presidential_election)
  (cada linha cita a fonte primária). O parser (`sources/wikipedia.py`) é
  genérico para wikitables (rowspan/colspan, cenários de 1º e 2º turno).
- **Registro oficial**: CSV de
  [dados abertos do TSE](https://dadosabertos.tse.jus.br/dataset/pesquisas-eleitorais-2026)
  (`sources/tse.py`). Cada pesquisa é casada por instituto + data de fim de
  campo e ganha o nº de protocolo (badge "✓ TSE" na tabela).
- A API antiga do Poder360 foi descontinuada/paga (Poder Monitor) — por isso
  a Wikipédia como fonte de resultados.

## Como rodar (dev)

**1) Backend** (Python 3.11+):

```powershell
cd backend
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m uvicorn main:app --port 8000
```

`GET http://localhost:8000/api/state` responde com o estado completo.
Sem internet? `$env:SOURCE = "mock"` antes de subir.

**2) Frontend:**

```powershell
cd frontend
npm install
npm run dev        # http://localhost:5173  (proxy /api -> :8000)
```

**Produção:** `npm run build` gera direto em `backend/static/`, que o FastAPI
serve sozinho (um processo só).

## O modelo (resumo)

Tudo em `backend/config.py` (`ModelConfig` + `INSTITUTE_RATINGS`):

- Peso de cada pesquisa = **recência** (meia-vida de 14 dias) ×
  **rating do instituto** (0–1, editorial, baseado no erro de véspera em
  2018–2022) × **amostra** (√(n/1000), com teto) × **registro no TSE**
  (pesquisa do ciclo 2026 sem registro localizado vale 0,5×).
- **House effect**: desvio sistemático de cada instituto vs. a média dos
  demais, estimado na 1ª passada e corrigido em 50% na 2ª.
- **Banda de incerteza**: dispersão entre institutos + erro amostral médio +
  termo estrutural de 1,5 pp (pesquisa erra mais que a margem declarada).
- **P(liderar hoje)**: 20 mil simulações Monte Carlo sobre as bandas. É
  "quem estaria na frente hoje segundo o modelo", não previsão da eleição.
- 2º turno: cada confronto (Lula × F. Bolsonaro etc.) é agregado em separado.
- Candidato que saiu dos cenários recentes (45 dias) sai da média atual.

Os ratings dos institutos são **editoriais e transparentes** — o painel exibe
a tabela de pesos ao leitor. Discorde? Ajuste `INSTITUTE_RATINGS` e rode de
novo.

## Governador e Senador (estrutura pronta, fonte pendente)

A arquitetura é genérica: `config.RACES` aceita qualquer (cargo, UF, página).
O bloqueio é fonte de dados — não há páginas consolidadas e estáveis com os
resultados por estado em 2026 (a Wikipédia cobre mal as disputas estaduais, e
o CSV do TSE não traz percentuais). Quando houver página utilizável para um
estado, basta registrar uma `Race` nova apontando para ela; o cruzamento com
o TSE já filtra por UF e cargo automaticamente.

## Boas práticas embutidas

- Atualização no máximo a cada **6h** (`POLL_INTERVAL_SECONDS`) — pesquisa
  muda em dias, não em segundos. User-Agent honesto, retry com backoff,
  cache do último estado válido.
- Se a estrutura da página da Wikipédia mudar e o parse zerar, o backend
  mantém o último cache e loga o erro (não quebra o painel).

## Aviso

Painel **não-oficial**, sem vínculo com TSE, institutos ou campanhas. A média
do modelo **não é uma pesquisa** e não deve ser citada como tal. Os números
de cada pesquisa pertencem aos respectivos institutos; o registro pode ser
conferido em [pesqele-divulgacao.tse.jus.br](https://pesqele-divulgacao.tse.jus.br/).
