"""API do agregador.

- Busca as pesquisas na fonte (wikipedia/mock) a cada POLL_INTERVAL_SECONDS
  (pesquisa eleitoral muda em dias; default 6h).
- Cruza com o registro do TSE, roda o modelo, guarda em cache em memória.
- Expõe GET /api/state com o JSON consumido pelo frontend.
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import config
from model import aggregate_matchups, aggregate_race
from sources import get_source
from sources.base import Poll
from sources.tse import TseRegistry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("agregador")


class StateCache:
    def __init__(self) -> None:
        self.state: dict | None = None
        self.last_ok_ts: str | None = None
        self.last_error: str | None = None


cache = StateCache()
tse = TseRegistry()


def _color_for(nome: str, taken: dict[str, str]) -> str:
    if nome in taken:
        return taken[nome]
    # paleta curada vence a cor crua da Wikipédia (tons refinados p/ fundo claro)
    k = nome.lower()
    for frag, cor in config.CANDIDATE_COLORS.items():
        if frag in k:
            return cor
    try:
        from sources.wikipedia import PARSED_COLORS
        if nome in PARSED_COLORS:
            return PARSED_COLORS[nome]
    except ImportError:
        pass
    return config.FALLBACK_PALETTE[len(taken) % len(config.FALLBACK_PALETTE)]


def _poll_row(p: Poll) -> dict:
    return {
        "instituto": p.instituto,
        "dataInicio": p.data_inicio.isoformat() if p.data_inicio else None,
        "dataFim": p.data_fim.isoformat(),
        "amostra": p.amostra,
        "margemErro": p.margem_erro,
        "cenario": p.cenario,
        "resultados": [
            {"candidato": r.candidato, "pct": r.pct, "isCandidate": r.is_candidate}
            for r in p.resultados
        ],
        "tseRegistro": p.tse_registro,
        "tseEmpresa": p.tse_empresa,
        "rating": config.institute_rating(p.instituto),
    }


def build_state(polls: list[Poll]) -> dict:
    colors: dict[str, str] = {}
    races: dict[str, dict] = {}

    for race in config.RACES:
        rp = [p for p in polls if p.race_id == race.id]
        if not rp:
            continue
        if race.turno == 2:
            block: dict = {"matchups": aggregate_matchups(rp)}
            for m in block["matchups"]:
                for c in m["candidatos"]:
                    colors[c["nome"]] = _color_for(c["nome"], colors)
                    c["cor"] = colors[c["nome"]]
        else:
            block = aggregate_race(rp)
            for c in block["candidatos"]:
                colors[c["nome"]] = _color_for(c["nome"], colors)
                c["cor"] = colors[c["nome"]]
        rp_sorted = sorted(rp, key=lambda p: p.data_fim, reverse=True)
        block["pesquisas"] = [_poll_row(p) for p in rp_sorted[:80]]
        block["cargo"] = race.cargo
        block["uf"] = race.uf
        block["turno"] = race.turno
        races[race.id] = block

    institutos = sorted(
        {p.instituto for p in polls},
        key=lambda i: -config.institute_rating(i),
    )
    pesos = [
        {
            "instituto": i,
            "rating": config.institute_rating(i),
            "registradaTse": any(p.tse_registro for p in polls if p.instituto == i),
        }
        for i in institutos
    ]

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "fonte": config.SOURCE,
        "cores": colors,
        "races": races,
        "defaultRace": config.DEFAULT_RACE_ID,
        "pesos": pesos,
        "tseCarregado": tse.loaded,
        "modeloParams": {
            "meiaVidaDias": config.MODEL.half_life_days,
            "janelaDias": config.MODEL.max_age_days,
            "houseEffectShrink": config.MODEL.house_effect_shrink,
            "bandZ": config.MODEL.band_z,
            "penalSemRegistro": config.UNREGISTERED_PENALTY,
        },
    }


async def poll_once() -> None:
    source = get_source(config.SOURCE)
    try:
        polls = await source.fetch()
        if config.TSE_ENABLED and config.SOURCE != "mock" and tse.stale:
            try:
                await tse.load()
            except Exception as exc:  # noqa: BLE001
                log.warning("TSE indisponível (seguindo sem registro): %s", exc)
        if tse.loaded:
            hits = tse.annotate(polls)
            log.info("TSE: %d/%d linhas casadas com registro", hits, len(polls))
        cache.state = build_state(polls)
        cache.last_ok_ts = cache.state["timestamp"]
        cache.last_error = None
        n1 = cache.state["races"].get("presidente-1t", {}).get("nPesquisas", 0)
        log.info("OK [%s] %d pesquisas no 1º turno", config.SOURCE, n1)
    except Exception as exc:  # noqa: BLE001
        cache.last_error = str(exc)
        log.error("Falha na atualização (mantendo último cache): %s", exc)


async def poll_loop() -> None:
    while True:
        await poll_once()
        await asyncio.sleep(config.POLL_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Não bloqueia o boot: o servidor sobe na hora (health check do Render
    # passa imediato) e a primeira coleta roda em background. /api/state
    # responde ready:false até os dados chegarem (~poucos segundos).
    task = asyncio.create_task(poll_loop())
    yield
    task.cancel()


app = FastAPI(title="Agregador de pesquisas — Brasil 2026", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # frontend local; restrinja em produção
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/api/state")
async def get_state():
    if cache.state is None:
        return {
            "ready": False,
            "error": cache.last_error or "carregando pesquisas…",
        }
    return {
        "ready": True,
        "lastOk": cache.last_ok_ts,
        "error": cache.last_error,
        "pollSeconds": config.POLL_INTERVAL_SECONDS,
        **cache.state,
    }


@app.get("/api/health")
async def health():
    return {"ok": True, "fonte": config.SOURCE, "lastOk": cache.last_ok_ts}


# ---------------------------------------------------------------------------
# Servir o frontend buildado (produção). Em DEV o Vite serve o front.
# IMPORTANTE: montar DEPOIS das rotas /api para não as sombrear.
# ---------------------------------------------------------------------------
import os  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402


class SmartStatic(StaticFiles):
    """assets com hash → cache 1 ano; resto (index.html) → no-cache."""
    async def get_response(self, path, scope):
        resp = await super().get_response(path, scope)
        try:
            norm = path.replace("\\", "/")
            if norm.startswith("assets/"):
                resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
            else:
                resp.headers["Cache-Control"] = "no-cache, must-revalidate"
        except Exception:  # noqa: BLE001
            pass
        return resp


_STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_STATIC_DIR):
    app.mount("/", SmartStatic(directory=_STATIC_DIR, html=True), name="frontend")
    log.info("Servindo frontend estático de %s", _STATIC_DIR)
