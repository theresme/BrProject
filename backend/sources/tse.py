"""Cruzamento com o registro oficial de pesquisas do TSE (dados abertos).

O TSE NÃO publica resultados — publica o REGISTRO (PesqEle): instituto,
contratante, período de campo, nº de entrevistados e o nº de protocolo.
Baixamos o CSV oficial e tentamos casar cada pesquisa (vinda da fonte de
resultados) com seu registro, por nome do instituto + proximidade da data
de fim de campo. Pesquisa casada ganha o badge "registrada no TSE".
"""
from __future__ import annotations

import csv
import io
import logging
import re
import unicodedata
import zipfile
from datetime import date, datetime, timedelta

import httpx

import config
from .base import Poll

log = logging.getLogger("fonte.tse")

# Janela de tolerância entre o fim de campo informado na publicação e o
# registrado no TSE (institutos às vezes estendem o campo).
MATCH_WINDOW_DAYS = 4

# Apelido público (como aparece na imprensa/Wikipédia) -> termo que aparece
# na razão social ou nome fantasia do registro.
ALIASES: dict[str, tuple[str, ...]] = {
    "atlasintel": ("atlas",),
    "poderdata": ("poderdata", "poder data"),
    "real time big data": ("real time",),
    "rtbd": ("real time",),
    "datafolha": ("datafolha",),
    "ipec": ("ipec", "inteligencia em pesquisa"),
    "quaest": ("quaest",),
    "genial/quaest": ("quaest",),
    "parana pesquisas": ("parana",),
    "vox brasil": ("vox",),
    "ideia": ("ideia",),
    "mda": ("mda",),
    "gerp": ("gerp",),
    "futura": ("futura",),
    "nexus": ("nexus",),
}


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def _norm_name(s: str) -> str:
    s = _strip_accents((s or "").lower())
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


class TseRegistry:
    """Índice das pesquisas registradas no TSE para um conjunto de UFs."""

    def __init__(self) -> None:
        # registros: lista de dicts com chaves normalizadas
        self._rows: list[dict] = []
        self._loaded_at: datetime | None = None

    @property
    def loaded(self) -> bool:
        return self._loaded_at is not None

    @property
    def stale(self) -> bool:
        return (self._loaded_at is None
                or datetime.now() - self._loaded_at > timedelta(hours=24))

    async def load(self) -> None:
        async with httpx.AsyncClient(
            headers={"User-Agent": config.USER_AGENT}, timeout=120.0,
        ) as client:
            r = await client.get(config.TSE_CSV_ZIP_URL, follow_redirects=True)
            r.raise_for_status()
        rows: list[dict] = []
        with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
            for name in zf.namelist():
                if not name.lower().endswith(".csv"):
                    continue
                with zf.open(name) as fh:
                    text = io.TextIOWrapper(fh, encoding="latin-1")
                    for rec in csv.DictReader(text, delimiter=";"):
                        rows.append({
                            "uf": rec.get("SG_UF", ""),
                            "registro": rec.get("NR_PROTOCOLO_REGISTRO", ""),
                            "empresa": rec.get("NM_EMPRESA", ""),
                            "fantasia": rec.get("NM_EMPRESA_FANTASIA", ""),
                            "cargos": _norm_name(rec.get("DS_CARGO", "")),
                            "fim": _parse_dt(rec.get("DT_FIM_PESQUISA", "")),
                            "inicio": _parse_dt(rec.get("DT_INICIO_PESQUISA", "")),
                            "entrevistados": rec.get("QT_ENTREVISTADO", ""),
                            "_busca": _norm_name(
                                rec.get("NM_EMPRESA", "") + " "
                                + rec.get("NM_EMPRESA_FANTASIA", "")),
                        })
        self._rows = rows
        self._loaded_at = datetime.now()
        log.info("TSE: %d registros carregados", len(rows))

    def _terms_for(self, instituto: str) -> tuple[str, ...]:
        k = _norm_name(instituto)
        if k in ALIASES:
            return ALIASES[k]
        return (k,) if k else ()

    def match(self, poll: Poll) -> tuple[str, str] | None:
        """Retorna (nº de registro, razão social) ou None."""
        if poll.data_fim is None:
            return None
        terms = self._terms_for(poll.instituto)
        if not terms:
            return None
        uf = "BR" if poll.race_id.startswith("presidente") else poll.race_id[-2:]
        cargo = "presidente" if uf == "BR" else None
        best: tuple[int, dict] | None = None
        for row in self._rows:
            if cargo and cargo not in row["cargos"]:
                continue
            if uf == "BR" and row["uf"] not in ("BR", "BRASIL"):
                continue
            if uf != "BR" and row["uf"] != uf:
                continue
            if not any(t in row["_busca"] for t in terms):
                continue
            if row["fim"] is None:
                continue
            diff = abs((row["fim"] - poll.data_fim).days)
            if diff > MATCH_WINDOW_DAYS:
                continue
            if best is None or diff < best[0]:
                best = (diff, row)
        if best is None:
            return None
        return best[1]["registro"], best[1]["empresa"]

    def annotate(self, polls: list[Poll]) -> int:
        """Preenche tse_registro/tse_empresa in-place; retorna nº de casadas."""
        hits = 0
        cache: dict[str, tuple[str, str] | None] = {}
        for p in polls:
            ck = f"{p.instituto}|{p.data_fim}|{p.race_id}"
            if ck not in cache:
                cache[ck] = self.match(p)
            m = cache[ck]
            if m:
                p.tse_registro, p.tse_empresa = m
                hits += 1
        return hits


def _parse_dt(s: str) -> date | None:
    s = (s or "").strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None
