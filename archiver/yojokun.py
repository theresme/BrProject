"""Alvo 2 — Yōjōkun / 養生訓 (Kaibara Ekiken, 1713), 8 volumes.

Fonte A — Arquivo Nacional do Japão, item 1236669 (養生訓, Naikaku Bunko).
O padrão de URL não foi chutado: a página do item lista um viewer por volume
em /img/<id>, e cada viewer expõe um manifesto IIIF em
    https://www.digital.archives.go.jp/api/iiif/<id>/manifest.json
que é o endpoint efetivamente usado aqui. Cada canvas dá um service IIIF, de
onde as páginas saem em full/max (3000 px no lado maior).

Fonte B — Universidade Nakamura Gakuen: de lá vem a tabela de hentaigana, que
é o que torna a xilogravura legível.
"""

from __future__ import annotations

from pathlib import Path

import img2pdf

from . import core
from .core import ACERVO, log

DEST = ACERVO / "yojokun"
RAW = DEST / "raw"

ITEM_PAI = "1236669"
MANIFEST_API = "https://www.digital.archives.go.jp/api/iiif/{id}/manifest.json"

# Os 8 volumes, na ordem, extraídos da página do item 1236669.
VOLUMES = [
    ("4318676", 1),
    ("4318677", 2),
    ("4319506", 3),
    ("4319507", 4),
    ("4319508", 5),
    ("4299674", 6),
    ("4299675", 7),
    ("4319510", 8),
]

# Fonte B — tabela de variantes de kana (変体仮名), do arquivo Kaibara Ekiken.
HENTAIGANA_URL = (
    "https://www.nakamura-u.ac.jp/institute/media/library/kaibara/pdf/a_kana.pdf"
)

# 3000 px no lado maior: o que o servidor entrega em "max". Suficiente para ler
# a xilogravura; "full" nominal seria 6700 px, que o serviço não devolve.
TAMANHO_IIIF = "full/max/0/native.jpg"
TAMANHO_FALLBACK = "full/1500,/0/native.jpg"


def _paginas(manifest_iiif: dict) -> list[str]:
    """URLs de imagem, na ordem dos canvases."""
    canvases = manifest_iiif["sequences"][0]["canvases"]
    urls = []
    for canvas in canvases:
        recurso = canvas["images"][0]["resource"]
        servico = recurso.get("service", {}).get("@id")
        if servico:
            urls.append(f"{servico}/{TAMANHO_IIIF}")
        else:  # sem service: usa a imagem direta declarada no canvas
            urls.append(recurso["@id"])
    return urls


def _monta_pdf(imagens: list[Path], destino: Path) -> None:
    """img2pdf embute os JPEGs sem recomprimir — nada de perda extra."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    with open(destino, "wb") as fh:
        fh.write(img2pdf.convert([str(p) for p in imagens]))
    log().info("PDF montado %s (%d páginas, %d bytes)", destino.name, len(imagens), destino.stat().st_size)


def fetch(manifest: dict) -> list[Path]:
    saidas: list[Path] = []
    todas_imagens: list[Path] = []

    for vol_id, numero in VOLUMES:
        log().info("== Yōjōkun volume %d (item %s)", numero, vol_id)
        iiif = core.get_json(MANIFEST_API.format(id=vol_id))
        rotulo = iiif.get("label", f"養生訓{numero}")
        urls = _paginas(iiif)
        log().info("   %s: %d páginas", rotulo, len(urls))

        dir_vol = RAW / f"vol{numero:02d}"
        imagens: list[Path] = []
        for i, url in enumerate(urls, start=1):
            alvo = dir_vol / f"{i:04d}.jpg"
            try:
                core.download(url, alvo, min_bytes=5_000)
            except Exception as exc:
                log().warning("   página %d em max falhou (%s); tentando 1500px", i, exc)
                base = url.rsplit("/full/", 1)[0]
                core.download(f"{base}/{TAMANHO_FALLBACK}", alvo, min_bytes=5_000)
            imagens.append(alvo)

        pdf_vol = DEST / f"yojokun-vol{numero:02d}.pdf"
        if not pdf_vol.exists():
            _monta_pdf(imagens, pdf_vol)
        core.record(
            manifest,
            pdf_vol,
            fonte="Arquivo Nacional do Japão (Fonte A) — Naikaku Bunko, metadados CC0",
            origem=MANIFEST_API.format(id=vol_id),
            volume=numero,
            rotulo=rotulo,
            paginas=len(imagens),
        )
        saidas.append(pdf_vol)
        todas_imagens.extend(imagens)

    # Consolidado dos 8 volumes.
    consolidado = DEST / "yojokun-shotoku.pdf"
    if not consolidado.exists():
        _monta_pdf(todas_imagens, consolidado)
    core.record(
        manifest,
        consolidado,
        fonte="Arquivo Nacional do Japão (Fonte A) — 8 volumes consolidados",
        origem=f"https://www.digital.archives.go.jp/file/{ITEM_PAI}",
        paginas=len(todas_imagens),
        volumes=len(VOLUMES),
    )
    saidas.append(consolidado)

    # Fonte B — tabela de hentaigana.
    tabela = DEST / "hentaigana-tabela.pdf"
    bruto = RAW / "a_kana.pdf"
    try:
        core.download(HENTAIGANA_URL, bruto, min_bytes=10_000)
        if not tabela.exists():
            tabela.write_bytes(bruto.read_bytes())
        core.record(
            manifest,
            tabela,
            fonte="Universidade Nakamura Gakuen (Fonte B) — arquivo Kaibara Ekiken",
            origem=HENTAIGANA_URL,
            nota="tabela de variantes de kana; chave para ler o original xilogravado",
        )
        saidas.append(tabela)
    except Exception as exc:
        log().error("tabela de hentaigana falhou: %s", exc)

    return saidas
