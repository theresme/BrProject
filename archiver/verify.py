"""Verificação dos PDFs montados.

Para cada PDF: contagem de páginas > 0, primeira e última página renderizadas
como PNG e checadas contra "veio em branco", e coerência entre tamanho do
arquivo e número de páginas.
"""

from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF
from pypdf import PdfReader

from .core import ACERVO, log

AMOSTRAS = ACERVO / "_verificacao"

# Um fac-símile digitalizado não desce de ~20 KB/página. PDFs de texto puro
# (Gutenberg convertido, tabela de kana vetorial) são legitimamente menores,
# por isso o piso só é aplicado a fac-símiles.
MIN_BYTES_POR_PAGINA_FACSIMILE = 20_000


def _pagina_em_branco(pagina: fitz.Page, png: Path) -> tuple[bool, float]:
    """Renderiza a página e mede o desvio-padrão dos pixels.

    Página em branco tem variação praticamente nula; qualquer coisa com texto
    ou imagem passa longe disso.
    """
    pix = pagina.get_pixmap(dpi=72, colorspace=fitz.csGRAY)
    png.parent.mkdir(parents=True, exist_ok=True)
    pix.save(png)

    dados = pix.samples
    n = len(dados)
    if n == 0:
        return True, 0.0
    media = sum(dados) / n
    variancia = sum((b - media) ** 2 for b in dados) / n
    desvio = variancia**0.5
    return desvio < 1.0, desvio


def verifica(pdf: Path, *, facsimile: bool = True) -> dict:
    resultado: dict = {"arquivo": str(pdf.relative_to(ACERVO)), "ok": True, "problemas": []}

    if not pdf.exists():
        return {**resultado, "ok": False, "problemas": ["arquivo não existe"]}

    tamanho = pdf.stat().st_size
    resultado["bytes"] = tamanho

    try:
        paginas = len(PdfReader(str(pdf)).pages)
    except Exception as exc:
        return {**resultado, "ok": False, "problemas": [f"pypdf não abriu: {exc}"]}

    resultado["paginas"] = paginas
    if paginas <= 0:
        resultado["ok"] = False
        resultado["problemas"].append("zero páginas")
        return resultado

    if facsimile:
        por_pagina = tamanho / paginas
        resultado["bytes_por_pagina"] = round(por_pagina)
        if por_pagina < MIN_BYTES_POR_PAGINA_FACSIMILE:
            resultado["ok"] = False
            resultado["problemas"].append(
                f"tamanho incoerente: {por_pagina:.0f} B/página num fac-símile"
            )

    doc = fitz.open(str(pdf))
    try:
        for rotulo, indice in (("primeira", 0), ("ultima", paginas - 1)):
            png = AMOSTRAS / f"{pdf.stem}-{rotulo}.png"
            branco, desvio = _pagina_em_branco(doc[indice], png)
            resultado[f"{rotulo}_desvio"] = round(desvio, 2)
            resultado[f"{rotulo}_png"] = str(png.relative_to(ACERVO))
            if branco:
                resultado["ok"] = False
                resultado["problemas"].append(f"página {rotulo} veio em branco")
    finally:
        doc.close()

    return resultado


def verifica_todos(pdfs: list[tuple[Path, bool]]) -> list[dict]:
    saida = []
    for pdf, facsimile in pdfs:
        r = verifica(pdf, facsimile=facsimile)
        marca = "OK  " if r["ok"] else "FALHA"
        log().info(
            "%s %s — %s páginas, %s bytes%s",
            marca,
            r["arquivo"],
            r.get("paginas", "?"),
            r.get("bytes", "?"),
            "" if r["ok"] else f" :: {'; '.join(r['problemas'])}",
        )
        saida.append(r)
    return saida
