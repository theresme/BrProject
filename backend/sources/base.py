"""Tipos comuns e interface das fontes plugáveis."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class PollResult:
    """Número de UM candidato/rótulo em UMA pesquisa/cenário."""
    candidato: str           # nome normalizado ("Lula", "Tarcísio")
    pct: float               # pontos percentuais
    is_candidate: bool = True  # False p/ branco/nulo/indeciso/outros


@dataclass
class Poll:
    """Uma pesquisa publicada (um cenário estimulado de uma rodada)."""
    race_id: str             # "presidente-1t" | "presidente-2t"
    instituto: str
    data_fim: date           # último dia de campo (usado p/ idade)
    data_inicio: date | None = None
    amostra: int | None = None
    margem_erro: float | None = None      # pp (±)
    cenario: str = ""        # descrição curta do cenário/matchup
    resultados: list[PollResult] = field(default_factory=list)
    fonte_url: str = ""      # link da fonte primária (ref da Wikipédia)
    # Cruzamento com o TSE (preenchido por sources/tse.py)
    tse_registro: str | None = None       # nº de registro (ex.: BR-01234/2026)
    tse_empresa: str | None = None        # razão social no registro

    @property
    def key(self) -> str:
        return f"{self.instituto}|{self.data_fim.isoformat()}|{self.cenario}"


class Source:
    """Interface de fonte. Implementações: wikipedia, mock."""

    name: str = "base"

    async def fetch(self) -> list[Poll]:  # pragma: no cover - interface
        raise NotImplementedError
