"""Fonte Wikipédia (EN): wikitables de "Opinion polling for the 2026
Brazilian presidential election".

Por que a Wikipédia? O TSE registra as pesquisas (PesqEle) mas NÃO publica
os percentuais — só metadados. A Wikipédia mantém as tabelas de resultados
mais completas e auditáveis (cada linha tem citação para a fonte primária),
e nós cruzamos cada pesquisa com o CSV oficial de registros do TSE
(sources/tse.py) para exibir o nº de registro.

O parser é genérico: expande rowspan/colspan numa grade, classifica colunas
pelo texto do cabeçalho e trata o resto como candidatos. Cada wikitable é
atribuída a (ano, turno) pelo heading h3/h4 que a precede.
"""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import date

import httpx
from bs4 import BeautifulSoup, Tag

import config
from .base import Poll, PollResult, Source

log = logging.getLogger("fonte.wikipedia")

MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    "abr": 4, "mai": 5, "ago": 8, "set": 9, "out": 10, "dez": 12,
}

# Colunas de metadados (não-candidato), por palavra-chave no cabeçalho.
META_COLS = {
    "pollster": "instituto",
    "firm": "instituto",        # "Polling firm" — checar ANTES de "period"
    "contratante": "instituto",
    "period": "periodo",
    "fieldwork": "periodo",
    "date": "periodo",
    "data": "periodo",
    "margin": "margem",
    "margem": "margem",
    "sample": "amostra",
    "amostra": "amostra",
    "amostragem": "amostra",
    "lead": "lead",
    "vantagem": "lead",
    "source": "fonte",
    "ref": "fonte",
    "link": "fonte",
    "cen.": "ignore",
    "cenário": "ignore",
    "cenario": "ignore",
    "número de identificação": "ignore",
    "numero de identificacao": "ignore",
}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def _cell_text(cell: Tag) -> str:
    """Texto visível da célula, sem citações [1]/[a]."""
    for sup in cell.find_all("sup"):
        sup.decompose()
    return _norm(cell.get_text(" "))


def expand_table(table: Tag) -> list[list[Tag]]:
    """Expande a <table> numa grade retangular respeitando rowspan/colspan.
    Cada posição aponta para a Tag da célula original."""
    grid: list[list[Tag | None]] = []
    row_idx = -1
    for tr in table.find_all("tr"):
        cells = tr.find_all(["th", "td"], recursive=False)
        if not cells:
            continue
        row_idx += 1
        while len(grid) <= row_idx:
            grid.append([])
        col = 0
        for cell in cells:
            # pula posições já ocupadas por rowspan de linhas anteriores
            while col < len(grid[row_idx]) and grid[row_idx][col] is not None:
                col += 1
            rs = int(cell.get("rowspan", 1) or 1)
            cs = int(cell.get("colspan", 1) or 1)
            for r in range(rs):
                while len(grid) <= row_idx + r:
                    grid.append([])
                row = grid[row_idx + r]
                while len(row) < col + cs:
                    row.append(None)
                for c in range(cs):
                    if row[col + c] is None:
                        row[col + c] = cell
            col += cs
    width = max((len(r) for r in grid), default=0)
    for r in grid:
        while len(r) < width:
            r.append(None)
    return grid  # type: ignore[return-value]


def _is_header_row(row: list[Tag]) -> bool:
    real = [c for c in row if c is not None]
    return bool(real) and all(c.name == "th" for c in real)


def _candidate_name(cell: Tag) -> str:
    """Nome do candidato a partir da célula de cabeçalho (1º link COM texto
    = pessoa; links de foto não têm texto)."""
    for a in cell.find_all("a"):
        if _norm(a.get_text()):
            return _norm(a.get_text())
    return _cell_text(cell)


def _candidate_color(cells: list[Tag]) -> str | None:
    for c in cells:
        style = c.get("style", "") if c is not None else ""
        m = re.search(r"background(?:-color)?:\s*(#[0-9a-fA-F]{3,6})", style)
        if m:
            return m.group(1)
    return None


def parse_period(text: str, fallback_year: int) -> tuple[date | None, date | None]:
    """'5–8 Jun 2026' | '28 Apr – 2 May 2026' | '17 Oct 2025' | 'Nov 2025'."""
    t = _norm(text).replace("–", "-").replace("—", "-").replace("−", "-")
    if not t:
        return None, None
    year_m = re.findall(r"(20\d\d)", t)
    year = int(year_m[-1]) if year_m else fallback_year

    pt = re.sub(r"(\d{1,2})\s*[ºª]\.?", r"\1", t.lower())
    mon_pt = r"([A-Za-zÀ-ÿ]+)"

    def pt_month(name: str) -> int | None:
        return MONTHS.get(name[:3].lower())

    # "7 e 9 de junho de 2026" / "1 a 4 de março de 2026"
    m = re.match(rf"^(\d{{1,2}})\s+(?:e|a|-)\s+(\d{{1,2}})\s+de\s+{mon_pt}\s+de\s+(20\d\d)$", pt)
    if m:
        mon = pt_month(m.group(3))
        if mon:
            y = int(m.group(4))
            return date(y, mon, int(m.group(1))), date(y, mon, int(m.group(2)))

    # "29 de abril - 03 de maio de 2026"
    m = re.match(
        rf"^(\d{{1,2}})\s+de\s+{mon_pt}\s*(?:-|a|e)\s*(\d{{1,2}})\s+de\s+{mon_pt}\s+de\s+(20\d\d)$",
        pt,
    )
    if m:
        mon1, mon2 = pt_month(m.group(2)), pt_month(m.group(4))
        if mon1 and mon2:
            y = int(m.group(5))
            return date(y, mon1, int(m.group(1))), date(y, mon2, int(m.group(3)))

    # "9 de junho de 2026"
    m = re.match(rf"^(\d{{1,2}})\s+de\s+{mon_pt}\s+de\s+(20\d\d)$", pt)
    if m:
        mon = pt_month(m.group(2))
        if mon:
            d = date(int(m.group(3)), mon, int(m.group(1)))
            return d, d

    def one(part: str, default_month: int | None = None) -> date | None:
        part = part.strip()
        m = re.match(r"(?:(\d{1,2})\s+)?([A-Za-z]{3,9})\.?(?:\s+(20\d\d))?$", part)
        if not m:
            m2 = re.match(r"^(\d{1,2})$", part)  # só o dia ("5" em "5-8 Jun")
            if m2 and default_month:
                return date(year, default_month, int(m2.group(1)))
            return None
        day = int(m.group(1)) if m.group(1) else 15
        mon = MONTHS.get(m.group(2)[:3].lower())
        if not mon:
            return None
        y = int(m.group(3)) if m.group(3) else year
        return date(y, mon, day)

    parts = [p for p in t.split("-") if p.strip()]
    if len(parts) == 1:
        d = one(parts[0])
        return d, d
    fim = one(parts[-1])
    inicio = one(parts[0], default_month=fim.month if fim else None)
    return inicio, fim


def _parse_pct(text: str) -> float | None:
    t = _norm(text).replace(",", ".").rstrip("%")
    m = re.match(r"^(\d+(?:\.\d+)?)$", t)
    return float(m.group(1)) if m else None


def _parse_int(text: str) -> int | None:
    t = re.sub(r"[^\d]", "", _norm(text))
    return int(t) if t else None


def _parse_margin(text: str) -> float | None:
    m = re.search(r"(\d+(?:[.,]\d+)?)", _norm(text))
    return float(m.group(1).replace(",", ".")) if m else None


def _classify_header(texts: list[str]) -> str | None:
    """Classifica a coluna como meta ('instituto', 'periodo'...), 'nc'
    (branco/nulo/indeciso/outros) ou None (candidato)."""
    joined = " ".join(texts).lower()
    for kw, kind in META_COLS.items():
        if kw in joined:
            return kind
    for lbl in config.NON_CANDIDATE_LABELS:
        if lbl in joined:
            return "nc"
    return None


def parse_polls_table(table: Tag, race_id: str, year: int) -> list[Poll]:
    grid = expand_table(table)
    header_rows = []
    body_start = 0
    for i, row in enumerate(grid):
        if _is_header_row(row):
            header_rows.append(row)
            body_start = i + 1
        else:
            break
    if not header_rows or body_start >= len(grid):
        return []

    ncols = len(grid[0])
    columns: list[dict] = []
    for c in range(ncols):
        seen: list[Tag] = []
        for hr in header_rows:
            cell = hr[c]
            if cell is not None and cell not in seen:
                seen.append(cell)
        texts = [_cell_text(x) for x in seen]
        kind = _classify_header([t for t in texts if t])
        col = {"kind": kind, "texts": texts}
        if kind is None:  # candidato
            name_cell = next((x for x in seen if _norm(x.get_text())), None)
            col["nome"] = _candidate_name(name_cell) if name_cell else ""
            col["cor"] = _candidate_color(seen)
            if not col["nome"]:
                col["kind"] = "ignore"
        columns.append(col)

    polls: list[Poll] = []
    seen_cells: set[int] = set()
    for row in grid[body_start:]:
        if all(x is None for x in row) or _is_header_row(row):
            continue
        vals: dict[str, str] = {}
        results: list[PollResult] = []
        for c, col in enumerate(columns):
            cell = row[c]
            text = _cell_text(cell) if cell is not None else ""
            kind = col["kind"]
            if kind in ("instituto", "periodo", "margem", "amostra"):
                vals[kind] = text
            elif kind is None:
                pct = _parse_pct(text)
                if pct is not None:
                    results.append(PollResult(col["nome"], pct, True))
            elif kind == "nc":
                pct = _parse_pct(text)
                if pct is not None:
                    label = next((t for t in col["texts"] if t), "B/N/I")
                    results.append(PollResult(label, pct, False))

        instituto = vals.get("instituto", "").strip(" *")
        if not instituto or not results:
            continue
        # linhas-evento ("Lula announces candidacy") não têm números
        if not any(r.is_candidate for r in results):
            continue
        inicio, fim = parse_period(vals.get("periodo", ""), year)
        if fim is None:
            continue
        # cenário = quem de fato está NESTA linha (no 2º turno cada linha é
        # um confronto distinto; no 1º, um conjunto testado de candidatos)
        nomes_linha = [r.candidato for r in results if r.is_candidate]
        sep = " × " if race_id.endswith("2t") else ", "
        cenario = sep.join(nomes_linha)
        # célula com rowspan (mesma pesquisa, vários cenários) repete o
        # instituto: dedup por identidade da célula não é necessário porque
        # cada linha É um cenário distinto — mantemos todas.
        polls.append(Poll(
            race_id=race_id,
            instituto=instituto,
            data_inicio=inicio,
            data_fim=fim,
            amostra=_parse_int(vals.get("amostra", "")),
            margem_erro=_parse_margin(vals.get("margem", "")),
            cenario=cenario,
            resultados=results,
        ))
    _ = seen_cells
    return polls


# Cores por candidato extraídas dos cabeçalhos (partido) — preenchido no parse.
PARSED_COLORS: dict[str, str] = {}


def _collect_colors(table: Tag) -> None:
    grid = expand_table(table)
    header_rows = [r for r in grid if _is_header_row(r)]
    if not header_rows:
        return
    ncols = len(grid[0])
    for c in range(ncols):
        seen: list[Tag] = []
        for hr in header_rows:
            cell = hr[c]
            if cell is not None and cell not in seen:
                seen.append(cell)
        texts = [_cell_text(x) for x in seen]
        if _classify_header([t for t in texts if t]) is not None:
            continue
        name_cell = next((x for x in seen if _norm(x.get_text())), None)
        if not name_cell:
            continue
        nome = _candidate_name(name_cell)
        cor = _candidate_color(seen)
        if nome and cor and nome not in PARSED_COLORS:
            PARSED_COLORS[nome] = cor


class WikipediaSource(Source):
    name = "wikipedia"

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            headers={"User-Agent": config.USER_AGENT},
            timeout=config.REQUEST_TIMEOUT,
        )

    async def _fetch_html(self, page: str) -> str:
        last_exc: Exception | None = None
        for attempt in range(config.RETRY_MAX):
            try:
                r = await self._client.get(config.WIKIPEDIA_API, params={
                    "action": "parse", "page": page,
                    "prop": "text", "format": "json", "formatversion": "2",
                })
                r.raise_for_status()
                return r.json()["parse"]["text"]
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                await asyncio.sleep(config.RETRY_BACKOFF_BASE ** attempt)
        raise RuntimeError(f"Wikipédia indisponível: {last_exc}")

    async def fetch(self) -> list[Poll]:
        html = await self._fetch_html(config.WIKIPEDIA_PAGE)
        soup = BeautifulSoup(html, "lxml")

        polls: list[Poll] = []
        year = date.today().year
        round_no = 1
        # caminha o DOM na ordem: headings definem (ano, turno) das tabelas
        for el in soup.find_all(["h2", "h3", "h4", "h5", "table"]):
            if el.name in ("h2", "h3", "h4", "h5"):
                t = _norm(el.get_text()).lower()
                ym = re.search(r"\b(20\d\d)\b", t)
                if ym:
                    year = int(ym.group(1))
                if "second round" in t or "run-off" in t or "runoff" in t:
                    round_no = 2
                elif "first round" in t:
                    round_no = 1
                continue
            if "wikitable" not in (el.get("class") or []):
                continue
            race_id = "presidente-1t" if round_no == 1 else "presidente-2t"
            _collect_colors(el)
            parsed = parse_polls_table(el, race_id, year)
            polls.extend(parsed)

        log.info("Wikipédia: %d linhas de pesquisa extraídas", len(polls))
        if not polls:
            raise RuntimeError(
                "0 pesquisas extraídas — a estrutura da página mudou? "
                f"Verifique {config.WIKIPEDIA_PAGE!r}."
            )
        return polls
