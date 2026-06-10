"""Fonte mock: gera um histórico sintético de pesquisas (demo/offline)."""
from __future__ import annotations

import random
from datetime import date, timedelta

from .base import Poll, PollResult, Source

INSTITUTOS = [
    ("Datafolha", 2000), ("Quaest", 2004), ("AtlasIntel", 4500),
    ("Ipec", 2512), ("Paraná Pesquisas", 2020), ("Ipespe", 1500),
]

# (nome, média base, tendência pp/mês)
CANDIDATOS = [
    ("Lula", 38.0, +0.3),
    ("F. Bolsonaro", 28.0, +0.5),
    ("Caiado", 5.0, -0.1),
    ("Zema", 4.0, 0.0),
    ("Santos", 3.0, +0.2),
]


class MockSource(Source):
    name = "mock"

    async def fetch(self) -> list[Poll]:
        rng = random.Random(2026)
        hoje = date.today()
        polls: list[Poll] = []
        for semanas_atras in range(40, -1, -1):
            fim = hoje - timedelta(weeks=semanas_atras, days=rng.randint(0, 3))
            for instituto, amostra in INSTITUTOS:
                if rng.random() < 0.45:  # nem todo instituto publica toda semana
                    continue
                vies = rng.uniform(-1.5, 1.5)  # house effect sintético
                resultados = []
                total = 0.0
                for nome, base, tend in CANDIDATOS:
                    meses = -semanas_atras / 4.33
                    pct = base + tend * meses + vies * (1 if nome == "Lula" else -0.4)
                    pct += rng.gauss(0, 1.2)
                    pct = max(0.5, pct)
                    resultados.append(PollResult(nome, round(pct, 1), True))
                    total += pct
                resultados.append(PollResult("Branco/Nulo/Indeciso",
                                             round(max(2.0, 100 - total), 1), False))
                polls.append(Poll(
                    race_id="presidente-1t",
                    instituto=instituto,
                    data_inicio=fim - timedelta(days=3),
                    data_fim=fim,
                    amostra=amostra,
                    margem_erro=2.0,
                    cenario=", ".join(n for n, _, _ in CANDIDATOS),
                    resultados=resultados,
                    tse_registro=f"BR-{rng.randint(1000, 9999):05d}/2026",
                ))
        return polls
