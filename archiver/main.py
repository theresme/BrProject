"""CLI do arquivador.

    python -m archiver.main             # baixa tudo, verifica e traduz
    python -m archiver.main menagier    # só o Ménagier
    python -m archiver.main yojokun     # só o Yōjōkun
    python -m archiver.main verify      # só a verificação
    python -m archiver.main traduzir    # só a tradução (backend curado)
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

from . import core, menagier, translate, verify, yojokun
from .core import ACERVO, log


def _pdfs_para_verificar() -> list[tuple[Path, bool]]:
    """Cada PDF com a informação de ser ou não fac-símile.

    O piso de bytes/página só faz sentido para páginas digitalizadas: um PDF de
    texto puro (a tradução, a tabela de kana) é legitimamente muito menor.
    """
    alvos: list[tuple[Path, bool]] = []
    for p in sorted((ACERVO / "menagier").glob("*.pdf")):
        alvos.append((p, "traducao" not in p.name))
    for p in sorted((ACERVO / "yojokun").glob("*.pdf")):
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

    if alvo in ("all", "traduzir"):
        try:
            pdf = translate.monta_menagier(backend=argv[2] if len(argv) > 2 else "curada")
            core.record(
                manifest,
                pdf,
                fonte="tradução a partir da transcrição do Project Gutenberg",
                origem=str(translate.FONTE_MENAGIER.relative_to(ACERVO)),
                escopo="antologia bilíngue (prólogo, plano da obra, uma receita)",
            )
        except Exception as exc:
            falhas.append(f"tradução do Ménagier: {exc}")
            log().error("tradução do Ménagier falhou: %s\n%s", exc, traceback.format_exc())

        # O Yōjōkun não tem texto para traduzir. Fica registrado como bloqueado
        # — com o motivo — em vez de sumir do relatório.
        manifest["traducao_yojokun"] = {
            "estado": "bloqueado",
            "motivo": (
                "o fac-símile é xilogravura em kuzushiji/hentaigana (1713) e não há "
                "camada de texto; não existe transcrição em domínio público (o catálogo "
                "do Aozora Bunko, 19.497 obras, não traz 養生訓 nem 貝原益軒); a leitura "
                "exigiria OCR de kuzushiji (KuroNet/miwo), indisponível offline"
            ),
            "desbloqueio": (
                "havendo transcrição, ela entra em archiver/data/ e o mesmo pipeline "
                "bilíngue a monta"
            ),
        }
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
