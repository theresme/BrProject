"""Fonte de pesquisas de SENADO, por estado.

Em 2026 cada estado elege 2 senadores (voto em dois nomes), então não há
"média nacional": a disputa é por UF. Não existe página única consolidada na
Wikipédia — os dados ficam nas páginas estaduais "2026 {Estado} general
election", na seção *Opinion polling → Senate*, no MESMO formato de wikitable
da página presidencial.

Estratégia: descoberta automática. Para cada UF configurada, resolvemos a
página, procuramos a subseção "Senate" sob "Opinion polling" e parseamos suas
tabelas com o parser genérico já existente. UF sem página/seção é ignorada —
conforme a Wikipédia for preenchendo, novos estados aparecem sozinhos.
"""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import date

import httpx
from bs4 import BeautifulSoup

import config
from .base import Poll, Source
from .wikipedia import _collect_colors, _norm, parse_polls_table

log = logging.getLogger("fonte.senado")

PT_WIKIPEDIA_API = "https://pt.wikipedia.org/w/api.php"

# Nome da UF na Wikipédia (para montar "2026 {Nome} general election").
UF_NOMES: dict[str, str] = {
    "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas",
    "BA": "Bahia", "CE": "Ceará", "DF": "Federal District", "ES": "Espírito Santo",
    "GO": "Goiás", "MA": "Maranhão", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul",
    "MG": "Minas Gerais", "PA": "Pará", "PB": "Paraíba", "PR": "Paraná",
    "PE": "Pernambuco", "PI": "Piauí", "RJ": "Rio de Janeiro",
    "RN": "Rio Grande do Norte", "RS": "Rio Grande do Sul", "RO": "Rondônia",
    "RR": "Roraima", "SC": "Santa Catarina", "SP": "São Paulo",
    "SE": "Sergipe", "TO": "Tocantins",
}

PT_POLLING_PAGES: dict[str, str] = {
    "PR": "Pesquisas eleitorais para a eleição estadual de 2026 no Paraná",
}


class SenateSource(Source):
    name = "senate"

    def __init__(self, ufs: list[str] | None = None) -> None:
        self.ufs = ufs or list(UF_NOMES.keys())
        self._client = httpx.AsyncClient(
            headers={"User-Agent": config.USER_AGENT},
            timeout=config.REQUEST_TIMEOUT,
        )

    async def _api(self, api_url: str | None = None, **params) -> dict:
        params.setdefault("format", "json")
        params.setdefault("formatversion", "2")
        params.setdefault("redirects", "1")
        last_exc: Exception | None = None
        for attempt in range(config.RETRY_MAX):
            try:
                r = await self._client.get(api_url or config.WIKIPEDIA_API, params=params)
                r.raise_for_status()
                return r.json()
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                await asyncio.sleep(config.RETRY_BACKOFF_BASE ** attempt)
        raise RuntimeError(f"Wikipédia indisponível: {last_exc}")

    async def _senate_section_index(self, page: str) -> tuple[str, int] | None:
        """Resolve a página e acha o índice da seção 'Senate' que fica SOB
        'Opinion polling'. Retorna (título_resolvido, índice) ou None."""
        data = await self._api(action="parse", page=page, prop="sections")
        parse = data.get("parse")
        if not parse:
            return None
        title = parse["title"]
        secs = parse["sections"]
        # acha a posição da seção "Opinion polling" e da próxima seção de
        # mesmo nível (toclevel<=1) que a encerra
        op_pos = next((i for i, s in enumerate(secs)
                       if "opinion polling" in s["line"].lower()), None)
        if op_pos is None:
            return None
        op_level = int(secs[op_pos].get("toclevel", 1))
        for s in secs[op_pos + 1:]:
            lvl = int(s.get("toclevel", 1))
            if lvl <= op_level:
                break  # saiu da região de Opinion polling
            if re.fullmatch(r"senate|senado", s["line"].strip(), re.IGNORECASE):
                return title, int(s["index"])
        return None

    async def _pt_senator_section_index(self, page: str) -> tuple[str, int] | None:
        """Fallback ptwiki: acha a seção 'Senador' na página de pesquisas."""
        data = await self._api(
            PT_WIKIPEDIA_API, action="parse", page=page, prop="sections"
        )
        parse = data.get("parse")
        if not parse:
            return None
        for s in parse["sections"]:
            if re.fullmatch(r"senador", s["line"].strip(), re.IGNORECASE):
                return parse["title"], int(s["index"])
        return None

    async def _fetch_ptwiki_uf(self, uf: str) -> list[Poll]:
        page = PT_POLLING_PAGES.get(uf)
        if not page:
            return []
        found = await self._pt_senator_section_index(page)
        if not found:
            return []
        title, idx = found
        data = await self._api(
            PT_WIKIPEDIA_API, action="parse", page=title, prop="text", section=idx
        )
        html = data.get("parse", {}).get("text", "")
        if not html:
            return []
        soup = BeautifulSoup(html, "lxml")
        race_id = f"senador-{uf.lower()}"
        polls: list[Poll] = []
        for tbl in soup.find_all("table"):
            if "wikitable" not in (tbl.get("class") or []):
                continue
            _collect_colors(tbl)
            polls.extend(parse_polls_table(tbl, race_id, 2026))
        if polls:
            log.info("Senado %s (ptwiki): %d linhas de pesquisa", uf, len(polls))
        return polls

    async def _fetch_uf(self, uf: str) -> list[Poll]:
        nome = UF_NOMES.get(uf, uf)
        page = f"2026 {nome} general election"
        try:
            found = await self._senate_section_index(page)
        except Exception as exc:  # noqa: BLE001
            log.debug("Senado %s: erro resolvendo seção (%s)", uf, exc)
            return []
        if not found:
            try:
                return await self._fetch_ptwiki_uf(uf)
            except Exception as exc:  # noqa: BLE001
                log.debug("Senado %s: erro no fallback ptwiki (%s)", uf, exc)
                return []
        title, idx = found
        data = await self._api(action="parse", page=title, prop="text", section=idx)
        html = data.get("parse", {}).get("text", "")
        if not html:
            return []
        soup = BeautifulSoup(html, "lxml")
        race_id = f"senador-{uf.lower()}"
        polls: list[Poll] = []
        for tbl in soup.find_all("table"):
            if "wikitable" not in (tbl.get("class") or []):
                continue
            _collect_colors(tbl)
            polls.extend(parse_polls_table(tbl, race_id, 2026))
        if polls:
            log.info("Senado %s: %d linhas de pesquisa", uf, len(polls))
        return polls

    async def fetch(self) -> list[Poll]:
        results = await asyncio.gather(
            *(self._fetch_uf(uf) for uf in self.ufs), return_exceptions=True
        )
        polls: list[Poll] = []
        for r in results:
            if isinstance(r, list):
                polls.extend(r)
        log.info("Senado: %d linhas em %d estados",
                 len(polls), len({p.race_id for p in polls}))
        return polls


# usado por _norm/date imports indiretos
_ = (_norm, date)
