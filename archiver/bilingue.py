"""Renderização de uma edição bilíngue em PDF.

Original à esquerda, tradução à direita, parágrafo a parágrafo. O objetivo é
que dê para conferir a tradução contra a fonte sem sair da página — é o formato
honesto para um texto em francês médio, onde a escolha de cada palavra é
discutível.
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

RAIZ_FONTES = "/usr/share/fonts/truetype/dejavu"

_fontes_ok = False


def _registra_fontes() -> None:
    """DejaVu cobre todos os acentos do francês médio e do português.

    O pacote não traz a face oblíqua da DejaVu Sans, então o papel de itálico
    fica com a serifada. Não é um itálico de verdade, mas o contraste entre as
    duas famílias é justamente o que se quer aqui: a coluna do original em
    serifada e a da tradução em sem-serifa se distinguem de relance.
    """
    global _fontes_ok
    if _fontes_ok:
        return
    pdfmetrics.registerFont(TTFont("DejaVu", f"{RAIZ_FONTES}/DejaVuSans.ttf"))
    pdfmetrics.registerFont(TTFont("DejaVu-Bold", f"{RAIZ_FONTES}/DejaVuSans-Bold.ttf"))
    pdfmetrics.registerFont(TTFont("DejaVu-Italic", f"{RAIZ_FONTES}/DejaVuSerif.ttf"))
    pdfmetrics.registerFont(
        TTFont("DejaVu-BoldItalic", f"{RAIZ_FONTES}/DejaVuSerif-Bold.ttf")
    )
    # sem o registro da família, a marcação <i>/<b> dos parágrafos não resolve
    pdfmetrics.registerFontFamily(
        "DejaVu",
        normal="DejaVu",
        bold="DejaVu-Bold",
        italic="DejaVu-Italic",
        boldItalic="DejaVu-BoldItalic",
    )
    _fontes_ok = True


def _estilos() -> dict[str, ParagraphStyle]:
    base = ParagraphStyle(
        "base",
        fontName="DejaVu",
        fontSize=8.5,
        leading=12,
        alignment=TA_JUSTIFY,
    )
    return {
        "titulo": ParagraphStyle(
            "titulo", parent=base, fontName="DejaVu-Bold", fontSize=20, leading=26,
            alignment=0, spaceAfter=6,
        ),
        "subtitulo": ParagraphStyle(
            "subtitulo", parent=base, fontName="DejaVu-Italic", fontSize=11,
            leading=15, alignment=0, spaceAfter=14, textColor=colors.HexColor("#444444"),
        ),
        "secao": ParagraphStyle(
            "secao", parent=base, fontName="DejaVu-Bold", fontSize=13, leading=17,
            alignment=0, spaceBefore=14, spaceAfter=8,
        ),
        "nota": ParagraphStyle(
            "nota", parent=base, fontSize=8.5, leading=12.5, alignment=TA_JUSTIFY,
            textColor=colors.HexColor("#333333"),
        ),
        "cabecalho_col": ParagraphStyle(
            "cabecalho_col", parent=base, fontName="DejaVu-Bold", fontSize=8,
            leading=11, alignment=0, textColor=colors.HexColor("#666666"),
        ),
        "original": ParagraphStyle(
            "original", parent=base, fontName="DejaVu-Italic", fontSize=8,
            leading=12, textColor=colors.HexColor("#555555"),
        ),
        "traducao": ParagraphStyle("traducao", parent=base),
    }


def _escapa(texto: str) -> str:
    return texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render(
    *,
    destino: Path,
    titulo: str,
    subtitulo: str,
    nota: str,
    secoes: list[dict],
    rotulo_esq: str = "Original",
    rotulo_dir: str = "Tradução (pt-BR)",
) -> Path:
    """Monta o PDF bilíngue.

    Cada seção é ``{"titulo": str, "pares": [(original, traducao), ...]}``.
    """
    _registra_fontes()
    est = _estilos()
    destino.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(destino),
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=titulo,
        author="PublicDomainArchiver",
    )

    largura = doc.width / 2.0
    fluxo: list = [
        Paragraph(_escapa(titulo), est["titulo"]),
        Paragraph(_escapa(subtitulo), est["subtitulo"]),
        Paragraph(nota, est["nota"]),  # nota já vem com marcação
        PageBreak(),
    ]

    estilo_tabela = TableStyle(
        [
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (0, -1), 8),
            ("LEFTPADDING", (1, 0), (1, -1), 8),
            ("RIGHTPADDING", (1, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            # filete separando as colunas
            ("LINEBEFORE", (1, 0), (1, -1), 0.4, colors.HexColor("#cccccc")),
        ]
    )

    for secao in secoes:
        fluxo.append(Paragraph(_escapa(secao["titulo"]), est["secao"]))
        fluxo.append(
            Table(
                [[
                    Paragraph(rotulo_esq, est["cabecalho_col"]),
                    Paragraph(rotulo_dir, est["cabecalho_col"]),
                ]],
                colWidths=[largura, largura],
                style=estilo_tabela,
            )
        )
        for original, traducao in secao["pares"]:
            linha = Table(
                [[
                    Paragraph(_escapa(original), est["original"]),
                    Paragraph(_escapa(traducao), est["traducao"]),
                ]],
                colWidths=[largura, largura],
                style=estilo_tabela,
            )
            # KeepTogether evita que um par curto seja partido entre páginas.
            fluxo.append(KeepTogether(linha) if len(original) < 900 else linha)
        fluxo.append(Spacer(1, 6))

    doc.build(fluxo)
    return destino
