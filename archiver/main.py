"""CLI do arquivador.

    python -m archiver.main            # baixa tudo e verifica
    python -m archiver.main menagier   # só o Ménagier
    python -m archiver.main yojokun    # só o Yōjōkun
    python -m archiver.main verify     # só a verificação
"""

from __future__ import annotations

import sys
import traceback

from . import core, menagier, verify, yojokun
from .core import ACERVO, log


def _pdfs_para_verificar() -> list[tuple[bool, ...]]:
    alvos = []
    for p in sorted((ACERVO / "menagier").glob("*.pdf")):
        alvos.append((p, True))
    for p in sorted((ACERVO / "yojokun").glob("*.pdf")):
        # a tabela de kana é um PDF de texto/vetor, não um fac-símile
        alvos.append((p, "hentaigana" not in p.name))
    return alvos


def main(argv: list[str]) -> int:
    alvo = argv[1] if len(argv) > 1 else "all"
    manifest = core.load_manifest()
    falhas: list[str] = []

    if alvo in ("all", "menagier"):
        try:
            menagier.fetch(manifest)
        except Exception as exc:
            falhas.append(f"menagier: {exc}")
            log().error("Ménagier falhou: %s\n%s", exc, traceback.format_exc())
        core.save_manifest(manifest)

    if alvo in ("all", "yojokun"):
        try:
            yojokun.fetch(manifest)
        except Exception as exc:
            falhas.append(f"yojokun: {exc}")
            log().error("Yōjōkun falhou: %s\n%s", exc, traceback.format_exc())
        core.save_manifest(manifest)

    if alvo in ("all", "verify"):
        resultados = verify.verifica_todos(_pdfs_para_verificar())
        manifest["verificacao"] = resultados
        core.save_manifest(manifest)
        falhas += [
            f"verificação {r['arquivo']}: {'; '.join(r['problemas'])}"
            for r in resultados
            if not r["ok"]
        ]

    log().info("=" * 60)
    if falhas:
        log().error("FALHAS (%d):", len(falhas))
        for f in falhas:
            log().error("  - %s", f)
    else:
        log().info("Sem falhas.")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
