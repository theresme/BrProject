"""Tradução das obras baixadas.

O que dá e o que não dá, por obra:

**Ménagier de Paris** — existe texto. A transcrição do Project Gutenberg
(Fonte C) é francês médio de 1393, ~225 mil palavras. Ela é a base: melhor que
OCR do fac-símile e melhor que qualquer coisa reconstruída de memória. Todo
trecho traduzido aqui é recortado do arquivo baixado, por âncora — nunca
redigitado — de modo que o original impresso no PDF é verificavelmente o da
fonte.

**Yōjōkun** — não existe texto. O fac-símile é xilogravura em kuzushiji/
hentaigana de 1713; não há transcrição em domínio público (o catálogo do Aozora
Bunko, 19.497 obras, não tem nem 養生訓 nem 貝原益軒), e ler kuzushiji exige OCR
especializado (KuroNet, miwo) que não roda offline. Sem transcrição, traduzir
seria inventar. O pipeline abaixo aceita uma transcrição assim que houver uma;
até lá, o alvo 2 fica registrado como bloqueado, não como feito.

Dois backends de tradução:

- ``curada`` (padrão) — traduções revisadas, versionadas em
  ``archiver/data/menagier-pt.json``. É o que roda sem credencial nenhuma.
- ``claude`` — traduz o texto inteiro via API da Anthropic, em blocos, com
  retomada. Precisa de credencial (``ANTHROPIC_API_KEY`` ou perfil do
  ``ant auth login``). Máquina de tradução genérica erra feio em francês médio
  (``amer`` = amar, não amargo; ``aucun`` = algum, não nenhum), por isso o
  backend é um LLM com instrução explícita sobre o estado de língua, e não um
  tradutor estatístico.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from . import bilingue
from .core import ACERVO, log

DADOS = Path(__file__).resolve().parent / "data"
FONTE_MENAGIER = ACERVO / "menagier" / "raw" / "gutenberg-44070.txt"
SAIDA_MENAGIER = ACERVO / "menagier" / "menagier-traducao-pt.pdf"

MODELO = "claude-opus-5"

INSTRUCAO = """Você traduz francês médio (séc. XIV) para português brasileiro.

O texto é o Ménagier de Paris (c. 1393), na edição de Jérôme Pichon (1846).

Regras:
- Traduza o sentido do francês MÉDIO, não do francês moderno. Falsos amigos
  frequentes: `amer` = amar (não amargo); `aucun` = algum (não nenhum);
  `mary` = marido; `chiere seur` = cara irmã; `ce` / `si` como partículas
  narrativas; `l'en` = impessoal ("a gente", "deve-se"); `jasoit-ce que` =
  ainda que; `pour ce que` = porque; `quanques` = tudo quanto.
- Preserve o registro: é um marido idoso instruindo a esposa de quinze anos.
  Cortês, prolixo, com períodos longos. Não modernize para prosa curta.
- Mantenha a divisão em parágrafos exatamente como recebida.
- Não acrescente comentário, nota, título ou preâmbulo. Devolva só a tradução.
- Se um trecho for genuinamente ambíguo, escolha a leitura mais provável e siga.

Formato: você recebe parágrafos numerados como `[[n]]`. Devolva os mesmos
marcadores `[[n]]`, na mesma ordem, cada um seguido da tradução."""


# ---------------------------------------------------------------- extração


def corpo_gutenberg(caminho: Path = FONTE_MENAGIER) -> str:
    """Texto do e-book, normalizado, sem cabeçalho nem licença do Gutenberg.

    A transcrição quebra as linhas em ~70 colunas, o que não tem relação com a
    divisão em parágrafos. Aqui as quebras rígidas somem e só a linha em branco
    — o parágrafo de verdade — sobrevive, como ``\\n\\n``. Sem isso as âncoras
    de recorte teriam de adivinhar onde cai cada quebra de linha.

    Também some o aparato de edição: chamadas de nota (``[797]``) e a marcação
    de itálico do Gutenberg (``_assim_``).
    """
    bruto = caminho.read_text(encoding="utf-8")
    inicio = bruto.find("*** START")
    fim = bruto.find("*** END")
    if inicio == -1 or fim == -1:
        raise ValueError("marcadores do Project Gutenberg não encontrados")
    corpo = bruto[bruto.find("\n", inicio) + 1 : fim]

    corpo = re.sub(r"\[\d+\]", "", corpo)
    corpo = re.sub(r"_([^_]+)_", r"\1", corpo)

    paragrafos = [" ".join(b.split()) for b in re.split(r"\n\s*\n", corpo)]
    return "\n\n".join(p for p in paragrafos if p)


def _limpa(trecho: str) -> list[str]:
    """Parágrafos de um trecho já normalizado por `corpo_gutenberg`."""
    return [p.strip() for p in trecho.split("\n\n") if p.strip()]


def recorta(corpo: str, inicio: str, fim: str) -> list[str]:
    """Recorta um trecho entre duas âncoras literais e devolve seus parágrafos.

    Âncoras em vez de deslocamentos numéricos: o recorte continua válido — ou
    falha alto — se o arquivo de origem mudar, em vez de silenciosamente
    passar a apontar para outro trecho. Um trecho longo do original é um único
    parágrafo; para partir em unidades menores, use vários trechos na seção.
    """
    a = corpo.find(inicio)
    if a == -1:
        raise LookupError(f"âncora inicial não encontrada: {inicio[:60]!r}")
    b = corpo.find(fim, a + len(inicio))
    if b == -1:
        raise LookupError(f"âncora final não encontrada: {fim[:60]!r}")
    return _limpa(corpo[a : b + len(fim)])


def originais_da_secao(corpo: str, secao: dict) -> list[str]:
    """Todos os parágrafos de uma seção, na ordem dos trechos declarados."""
    paragrafos: list[str] = []
    for trecho in secao["trechos"]:
        paragrafos.extend(recorta(corpo, trecho["inicio"], trecho["fim"]))
    return paragrafos


# ---------------------------------------------------------------- backends


def traduz_claude(paragrafos: list[str], *, lote: int = 8) -> list[str]:
    """Traduz via API da Anthropic, em lotes, preservando o alinhamento.

    Os parágrafos vão numerados e voltam numerados; o alinhamento é conferido
    por marcador, e não pela ordem de chegada, de modo que uma resposta com
    blocos faltando é detectada em vez de desalinhar a edição bilíngue.
    """
    import anthropic

    cliente = anthropic.Anthropic()
    saida: list[str] = []

    for i in range(0, len(paragrafos), lote):
        bloco = paragrafos[i : i + lote]
        entrada = "\n\n".join(f"[[{n}]] {p}" for n, p in enumerate(bloco, start=i))
        log().info("traduzindo parágrafos %d-%d de %d", i, i + len(bloco) - 1, len(paragrafos))

        with cliente.messages.stream(
            model=MODELO,
            max_tokens=32000,
            system=[{
                "type": "text",
                "text": INSTRUCAO,
                # a instrução é idêntica em todos os lotes: vale cachear
                "cache_control": {"type": "ephemeral"},
            }],
            output_config={"effort": "high"},
            messages=[{"role": "user", "content": entrada}],
        ) as fluxo:
            resposta = fluxo.get_final_message()

        if resposta.stop_reason == "refusal":
            raise RuntimeError(f"tradução recusada no lote {i}")

        texto = "".join(b.text for b in resposta.content if b.type == "text")
        partes = dict(
            (int(n), t.strip())
            for n, t in re.findall(r"\[\[(\d+)\]\]\s*(.*?)(?=\n*\[\[\d+\]\]|\Z)", texto, re.S)
        )
        faltando = [n for n in range(i, i + len(bloco)) if n not in partes]
        if faltando:
            raise RuntimeError(f"resposta sem os parágrafos {faltando}")
        saida.extend(partes[n] for n in range(i, i + len(bloco)))

    return saida


def traducao_curada() -> dict:
    return json.loads((DADOS / "menagier-pt.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------- montagem


def monta_menagier(backend: str = "curada") -> Path:
    """Monta a edição bilíngue do Ménagier."""
    corpo = corpo_gutenberg()
    dados = traducao_curada()
    secoes = []

    for secao in dados["secoes"]:
        originais = originais_da_secao(corpo, secao)

        if backend == "claude":
            traduzidos = traduz_claude(originais)
        else:
            traduzidos = secao["paragrafos"]
            if len(traduzidos) != len(originais):
                raise ValueError(
                    f"seção {secao['id']}: {len(originais)} parágrafos na fonte, "
                    f"{len(traduzidos)} na tradução curada"
                )

        secoes.append({"titulo": secao["titulo"], "pares": list(zip(originais, traduzidos))})
        log().info("seção %s: %d parágrafos", secao["id"], len(originais))

    destino = bilingue.render(
        destino=SAIDA_MENAGIER,
        titulo="Le Ménagier de Paris",
        subtitulo="Tratado de moral e economia doméstica composto por volta de 1393 "
        "por um burguês parisiense — antologia bilíngue",
        nota=dados["nota"],
        secoes=secoes,
        rotulo_esq="Francês médio (ed. Pichon, 1846)",
        rotulo_dir="Português (tradução)",
    )
    log().info("tradução montada: %s (%d bytes)", destino.name, destino.stat().st_size)
    return destino
