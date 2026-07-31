# Arquivador de domínio público

Baixa, monta, verifica e traduz duas obras de domínio público:

- **Le Ménagier de Paris** (c. 1393), ed. Jérôme Pichon, Paris 1846 — 2 tomos
- **Yōjōkun / 養生訓** (Kaibara Ekiken, 1713) — 8 volumes, exemplar do Naikaku Bunko

## Como rodar

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install requests img2pdf pypdf tqdm pymupdf reportlab

python -m archiver.main            # baixa tudo, traduz e verifica
python -m archiver.main menagier   # só o Ménagier
python -m archiver.main yojokun    # só o Yōjōkun
python -m archiver.main traduzir    # só a tradução
python -m archiver.main verify     # só a verificação
```

Rodar de novo não rebaixa nada: cada arquivo já presente em `raw/` com tamanho
maior que zero é pulado.

## Saída

```
acervo/
  menagier/
    raw/                        PDFs originais + transcrição do Gutenberg
    menagier-t1.pdf             351 páginas, fac-símile com camada de texto
    menagier-t2.pdf             397 páginas
    menagier-traducao-pt.pdf    antologia bilíngue francês médio / português
  yojokun/
    raw/vol01..vol08/           234 páginas em JPEG, direto do IIIF
    yojokun-vol01..08.pdf       um PDF por volume
    yojokun-shotoku.pdf         os 8 volumes consolidados
    hentaigana-tabela.pdf       tabela de variantes de kana
  _verificacao/                 PNGs da primeira e da última página de cada PDF
  MANIFEST.json                 sha256, tamanho e origem de cada artefato
  download.log                  URL, status, bytes e timestamp de cada requisição
```

Os binários (~555 MB) ficam fora do git; `MANIFEST.json` e `download.log` são
versionados e permitem reconstruir o acervo.

## De onde vem cada coisa

| Alvo | Fonte | Rota |
|---|---|---|
| Ménagier t1/t2 | Internet Archive (digitalização da Bayerische Staatsbibliothek) | `/metadata/<id>` → escolhe o PDF derivado, menor e com camada de texto |
| Ménagier (texto) | Project Gutenberg #44070 | transcrição, base da tradução |
| Yōjōkun vol. 1–8 | Arquivo Nacional do Japão, item 1236669 | página do item → viewer por volume → `api/iiif/<id>/manifest.json` → `full/max` |
| Tabela de hentaigana | Universidade Nakamura Gakuen, arquivo Kaibara Ekiken | PDF direto |

As fontes B (Gallica) e D (manuscrito do séc. XV) do Ménagier não foram usadas:
a Fonte A já entrega os dois tomos completos.

## Regras de rede

User-Agent identificável, um único worker, no máximo 1 requisição/segundo por
domínio, 5 tentativas com backoff exponencial limitado a 120 s. Os status 429,
503 e 403 esperam o dobro — o serviço de imagem do Arquivo Nacional devolve 403
intermitente sob carga sustentada, e a mesma URL responde 200 segundos depois.
Restrição de acesso de verdade persiste pelas cinco tentativas e o item termina
registrado como falha; nada é contornado.

## Tradução

O Ménagier tem transcrição, então dá para traduzir. Cada parágrafo em francês
médio impresso no PDF bilíngue é recortado por âncora textual do arquivo
baixado — nada é redigitado, e se a fonte mudar o recorte falha alto em vez de
divergir em silêncio.

Dois backends:

- `curada` (padrão) — traduções revisadas em `data/menagier-pt.json`, sem
  credencial nenhuma. Cobre o prólogo, o plano da obra e uma receita.
- `claude` — traduz o texto inteiro via API da Anthropic, em lotes, com
  conferência de alinhamento por marcador. Precisa de credencial
  (`ANTHROPIC_API_KEY` ou perfil do `ant auth login`):
  `python -m archiver.main traduzir claude`

Tradutor automático genérico não serve aqui: em francês médio `amer` é amar e
não amargo, `aucun` é algum e não nenhum — os erros invertem o sentido.

**O Yōjōkun não foi traduzido.** O fac-símile é xilogravura em kuzushiji/
hentaigana, sem camada de texto; não há transcrição em domínio público (o
catálogo do Aozora Bunko, 19.497 obras, não traz nem 養生訓 nem 貝原益軒), e a
leitura exigiria OCR de kuzushiji (KuroNet, miwo), indisponível offline. Sem
transcrição, traduzir seria inventar. Havendo uma, ela entra em `data/` e o
mesmo pipeline bilíngue a monta. O estado fica registrado em
`MANIFEST.json` sob `traducao_yojokun`.

## Verificação

Para cada PDF: contagem de páginas pelo `pypdf`, primeira e última página
renderizadas em PNG e testadas contra "veio em branco" (desvio-padrão dos
pixels), e coerência entre tamanho e número de páginas. O piso de bytes/página
só se aplica a fac-símiles — um PDF de texto é legitimamente menor.
