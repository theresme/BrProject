"""Alvo 1 — Le Ménagier de Paris (ed. Pichon, 1846, 2 tomos).

Fonte A (Internet Archive) é a que resolve: os dois tomos existem como itens
digitalizados pela Bayerische Staatsbibliothek, cada um com um "Text PDF"
derivado — menor e já com camada de texto de OCR. Como a Fonte A entrega os
dois tomos completos, as fontes B (Gallica) e D (manuscrito) não são
necessárias para o objetivo principal.

A Fonte C (Project Gutenberg) é baixada mesmo assim: é a transcrição do mesmo
texto, sem OCR no meio, e é dela que sai a tradução com qualidade.
"""

from __future__ import annotations

from pathlib import Path

from . import core
from .core import ACERVO, log

DEST = ACERVO / "menagier"
RAW = DEST / "raw"

IA_ITEMS = {
    "menagier-t1.pdf": "le-menagier-de-paris-tome-01-bsb",
    "menagier-t2.pdf": "le-menagier-de-paris-tome-02-bsb",
}

GUTENBERG_TXT = "https://www.gutenberg.org/files/44070/44070-0.txt"


def _pick_pdf(files: list[dict]) -> dict:
    """Escolhe o PDF a baixar entre os arquivos do item.

    Itens do IA costumam ter dois PDFs: o original da biblioteca (enorme) e o
    derivado do IA (menor, com camada de texto). Preferimos o menor — mesmo
    conteúdo, com texto pesquisável e sem 100 MB de scan redundante.
    """
    pdfs = [f for f in files if f["name"].lower().endswith(".pdf")]
    if not pdfs:
        raise LookupError("nenhum PDF no item")
    return min(pdfs, key=lambda f: int(f.get("size", 0) or 0))


def fetch(manifest: dict) -> list[Path]:
    """Baixa os dois tomos do Internet Archive + a transcrição do Gutenberg."""
    saidas: list[Path] = []

    for nome_final, identifier in IA_ITEMS.items():
        log().info("== Ménagier: %s (%s)", nome_final, identifier)
        meta = core.get_json(f"https://archive.org/metadata/{identifier}")
        if not meta or "files" not in meta:
            log().error("metadata vazio para %s — item inexistente?", identifier)
            continue

        escolhido = _pick_pdf(meta["files"])
        # O nome tem acentos e espaços; requests cuida do encoding da URL.
        url = f"https://archive.org/download/{identifier}/{escolhido['name']}"

        bruto = RAW / f"{identifier}.pdf"
        core.download(url, bruto, min_bytes=100_000)

        # raw/ é intocável: o PDF montado vai para o nível acima, por cópia.
        final = DEST / nome_final
        if not final.exists() or final.stat().st_size != bruto.stat().st_size:
            final.write_bytes(bruto.read_bytes())

        core.record(
            manifest,
            final,
            fonte="Internet Archive (Fonte A) / digitalização Bayerische Staatsbibliothek",
            origem=url,
            edicao="Pichon, 1846",
            item=identifier,
            arquivo_original=escolhido["name"],
        )
        saidas.append(final)

    # Fonte C — transcrição, base da tradução.
    txt = RAW / "gutenberg-44070.txt"
    try:
        core.download(GUTENBERG_TXT, txt, min_bytes=100_000)
        core.record(
            manifest,
            txt,
            fonte="Project Gutenberg (Fonte C) — transcrição, não fac-símile",
            origem=GUTENBERG_TXT,
            nota="texto dos dois volumes; usado como base da tradução",
        )
    except Exception as exc:
        log().error("Gutenberg falhou: %s", exc)

    return saidas
