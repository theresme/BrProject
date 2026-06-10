"""
Configuração central do agregador — TUDO que o modelo usa é ajustável aqui.

IMPORTANTE (e o frontend repete isso o tempo todo): a saída do modelo NÃO é
uma pesquisa. É uma média ponderada das pesquisas registradas no TSE, com
pesos editoriais/estatísticos documentados abaixo.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Fonte de dados
# ---------------------------------------------------------------------------
# "mock"      -> pesquisas sintéticas (demo/offline, sempre funciona)
# "wikipedia" -> wikitables de "Opinion polling for the 2026 Brazilian
#                presidential election" (en.wikipedia.org), cruzadas com o
#                CSV oficial de registros do TSE (dados abertos)
SOURCE: str = os.getenv("SOURCE", "wikipedia")

WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
WIKIPEDIA_PAGE = os.getenv(
    "WIKIPEDIA_PAGE",
    "Opinion polling for the 2026 Brazilian presidential election",
)

# CSV oficial de pesquisas REGISTRADAS (metadados, sem resultados) — TSE.
# https://dadosabertos.tse.jus.br/dataset/pesquisas-eleitorais-2026
TSE_CSV_ZIP_URL = os.getenv(
    "TSE_CSV_ZIP_URL",
    "https://cdn.tse.jus.br/estatistica/sead/odsele/pesquisa_eleitoral/pesquisa_eleitoral_2026.zip",
)
TSE_ENABLED: bool = os.getenv("TSE_ENABLED", "1") == "1"

# Pesquisas mudam em ritmo de dias, não segundos. 6h é mais que suficiente.
POLL_INTERVAL_SECONDS: int = int(os.getenv("POLL_INTERVAL_SECONDS", str(6 * 3600)))

USER_AGENT: str = os.getenv(
    "USER_AGENT",
    "brasil-needle/1.0 (agregador editorial nao-oficial de pesquisas; contato: voce@exemplo.com)",
)

REQUEST_TIMEOUT: float = 30.0
RETRY_MAX: int = 4
RETRY_BACKOFF_BASE: float = 1.8  # segundos: base^tentativa


# ---------------------------------------------------------------------------
# Disputas acompanhadas
# ---------------------------------------------------------------------------
# A arquitetura é genérica (cargo + UF). Presidente/BR é a disputa default e
# a única com fonte de resultados configurada por enquanto; para Governador/
# Senador basta existir uma página com wikitables e registrá-la aqui.
@dataclass(frozen=True)
class Race:
    id: str            # "presidente-br"
    cargo: str         # "Presidente"
    uf: str            # "BR" ou sigla do estado
    turno: int         # 1 ou 2
    wikipedia_page: str
    # Títulos (lowercase) de seções da página que delimitam este turno.
    section_hints: tuple[str, ...] = ()


RACES: tuple[Race, ...] = (
    Race(
        id="presidente-1t",
        cargo="Presidente",
        uf="BR",
        turno=1,
        wikipedia_page=WIKIPEDIA_PAGE,
        section_hints=("first round",),
    ),
    Race(
        id="presidente-2t",
        cargo="Presidente",
        uf="BR",
        turno=2,
        wikipedia_page=WIKIPEDIA_PAGE,
        section_hints=("second round", "run-off", "runoff"),
    ),
)

DEFAULT_RACE_ID = "presidente-1t"


# ---------------------------------------------------------------------------
# Cores e normalização de candidatos
# ---------------------------------------------------------------------------
# Cores por candidato (fallback: paleta neutra em ordem de chegada).
CANDIDATE_COLORS: dict[str, str] = {
    "lula": "#e11d48",            # vermelho PT
    "tarcisio": "#2563eb",        # azul
    "tarcísio": "#2563eb",
    "bolsonaro": "#1d4ed8",
    "michelle": "#7c3aed",
    "ratinho": "#0891b2",
    "caiado": "#16a34a",
    "zema": "#ea580c",
    "gomes": "#b45309",           # Ciro
    "marçal": "#9333ea",
    "marcal": "#9333ea",
}

FALLBACK_PALETTE: tuple[str, ...] = (
    "#e11d48", "#2563eb", "#16a34a", "#9333ea", "#ea580c",
    "#0891b2", "#b45309", "#db2777", "#65a30d", "#64748b",
)

# Rótulos agregados que NÃO são candidatos (não entram no modelo como pessoa).
NON_CANDIDATE_LABELS: tuple[str, ...] = (
    "blank", "null", "undecided", "none", "abstention", "others", "other",
    "don't know", "dont know", "branco", "nulo", "indeciso", "nenhum",
    "não sabe", "nao sabe", "outros",
)


# ---------------------------------------------------------------------------
# Pesos por instituto (desempenho histórico)
# ---------------------------------------------------------------------------
# Rating editorial baseado no erro das pesquisas de véspera vs. resultado
# oficial em 2018/2020/2022 (presidente 1º e 2º turnos; ver README para a
# metodologia e as referências). Escala 0..1 — multiplicador do peso da
# pesquisa no modelo. Institutos fora da tabela recebem DEFAULT_RATING.
#
# Isso é EDITORIAL e transparente: o painel mostra a tabela ao leitor.
INSTITUTE_RATINGS: dict[str, float] = {
    # menor erro médio em 2022 (presidencial)
    "atlasintel": 1.00,
    "atlas": 1.00,
    "quaest": 0.90,
    "genial/quaest": 0.90,
    "datafolha": 0.85,
    "ipec": 0.75,
    "ipespe": 0.75,
    "fsb": 0.75,
    "marquii": 0.70,
    "real time big data": 0.70,
    "rtbd": 0.70,
    # histórico de lean sistemático em 2018-2022
    "paraná pesquisas": 0.65,
    "parana pesquisas": 0.65,
    "veritá": 0.55,
    "verita": 0.55,
    "brasmarket": 0.40,
    "gerp": 0.55,
    "futura": 0.60,
    "modalmais/futura": 0.60,
}
DEFAULT_RATING: float = 0.60

# Institutos sem registro no TSE encontrado ganham penalização extra.
UNREGISTERED_PENALTY: float = 0.50


# ---------------------------------------------------------------------------
# Parâmetros do modelo
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ModelConfig:
    # Peso temporal: 0.5^(idade_em_dias / half_life_days)
    half_life_days: float = 14.0
    # Pesquisas mais velhas que isso saem do cálculo da média atual
    max_age_days: int = 90
    # Peso amostral: sqrt(n/1000), com teto (amostra gigante ≠ verdade)
    sample_ref: int = 1000
    sample_weight_cap: float = 1.6

    # House effect: desvio médio do instituto vs. média móvel dos demais,
    # encolhido por este fator antes de subtrair (1.0 = correção total).
    house_effect_shrink: float = 0.5
    # Mínimo de pesquisas do instituto para estimar house effect
    house_effect_min_polls: int = 3

    # Banda de incerteza: desvio-padrão ponderado entre pesquisas recentes
    # combinado com erro amostral médio, escalado por este fator (z≈1.28
    # ⇒ ~80% de cobertura, banda honesta sem virar rodapé de jornal).
    band_z: float = 1.28
    # Incerteza extra estrutural (pp) — pesquisas erram além do erro amostral
    structural_pp: float = 1.5

    # Monte Carlo p/ P(liderança): sorteia a "verdade" de cada candidato
    n_sims: int = 20_000

    # Grade do gráfico de tendência (1 ponto por dia)
    trend_start_days_back: int = 365

    # Candidato só aparece na média ATUAL se foi testado em pesquisa recente
    # (evita fantasma: alguém que saiu dos cenários fica com média estagnada)
    candidate_max_silence_days: int = 45
    candidate_min_recent_polls: int = 2


MODEL = ModelConfig()


def institute_rating(name: str) -> float:
    """Rating 0..1 do instituto (case-insensitive, melhor esforço)."""
    k = (name or "").strip().lower()
    if k in INSTITUTE_RATINGS:
        return INSTITUTE_RATINGS[k]
    for known, r in INSTITUTE_RATINGS.items():
        if known in k or k in known:
            return r
    return DEFAULT_RATING
