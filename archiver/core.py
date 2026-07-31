"""Camada comum de rede e bookkeeping do arquivador de domínio público.

Regras que valem para todos os alvos:
  - User-Agent identificável (nada de UA padrão do requests)
  - no máximo 1 requisição/segundo por domínio
  - idempotência: arquivo já presente em raw/ com tamanho > 0 não é rebaixado
  - 3 tentativas com backoff exponencial (2s, 4s, 8s); 429/503 esperam o dobro
  - tudo logado em download.log; sha256 de cada artefato final no MANIFEST.json
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import requests

USER_AGENT = "PublicDomainArchiver/1.0 (uso pessoal de pesquisa)"

ACERVO = Path(__file__).resolve().parent.parent / "acervo"
LOG_PATH = ACERVO / "download.log"
MANIFEST_PATH = ACERVO / "MANIFEST.json"

MIN_INTERVAL = 1.0  # segundos entre requisições ao mesmo domínio
MAX_ATTEMPTS = 5
BACKOFF_BASE = 2  # 2s, 4s, 8s, 16s, 32s
MAX_BACKOFF = 120

# 429 e 503 são o pedido explícito de calma. O 403 entra aqui porque o serviço
# de imagem do Arquivo Nacional do Japão devolve 403 de forma intermitente sob
# carga sustentada — a mesma URL responde 200 alguns segundos depois. Tratamos
# como throttling, esperando mais, e não como restrição de acesso: se fosse
# restrição, o 403 persistiria e o item acaba registrado como falha.
SLOW_DOWN_STATUS = {403, 429, 503}

_log_ready = False


def log() -> logging.Logger:
    """Logger que escreve em acervo/download.log e no stdout."""
    global _log_ready
    logger = logging.getLogger("archiver")
    if not _log_ready:
        ACERVO.mkdir(parents=True, exist_ok=True)
        logger.setLevel(logging.INFO)
        fmt = logging.Formatter("%(asctime)sZ %(levelname)s %(message)s")
        fmt.converter = time.gmtime
        fh = logging.FileHandler(LOG_PATH, encoding="utf-8")
        fh.setFormatter(fmt)
        sh = logging.StreamHandler()
        sh.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(fh)
        logger.addHandler(sh)
        logger.propagate = False
        _log_ready = True
    return logger


class RateLimiter:
    """Um worker, 1 req/s por domínio. Servidores de biblioteca pública."""

    def __init__(self, min_interval: float = MIN_INTERVAL) -> None:
        self.min_interval = min_interval
        self._last: dict[str, float] = {}
        self._lock = threading.Lock()

    def wait(self, url: str) -> None:
        host = urlsplit(url).netloc
        with self._lock:
            last = self._last.get(host)
            if last is not None:
                gap = self.min_interval - (time.monotonic() - last)
                if gap > 0:
                    time.sleep(gap)
            self._last[host] = time.monotonic()


_limiter = RateLimiter()
_session: requests.Session | None = None


def session() -> requests.Session:
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update({"User-Agent": USER_AGENT})
    return _session


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get(url: str, *, timeout: int = 120, stream: bool = False) -> requests.Response:
    """GET com rate limit, retry e backoff. Levanta a última exceção se falhar."""
    last_exc: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        _limiter.wait(url)
        try:
            resp = session().get(url, timeout=timeout, stream=stream)
        except requests.RequestException as exc:  # rede caiu, DNS, timeout
            last_exc = exc
            wait = BACKOFF_BASE**attempt
            log().warning("GET %s tentativa %d falhou (%s); espera %ds", url, attempt, exc, wait)
            if attempt < MAX_ATTEMPTS:
                time.sleep(wait)
            continue

        if resp.status_code == 200:
            return resp

        wait = min(BACKOFF_BASE**attempt, MAX_BACKOFF)
        if resp.status_code in SLOW_DOWN_STATUS:
            wait = min(wait * 2, MAX_BACKOFF)  # servidor pedindo calma
        log().warning(
            "GET %s status=%d tentativa %d; espera %ds", url, resp.status_code, attempt, wait
        )
        last_exc = requests.HTTPError(f"HTTP {resp.status_code} em {url}", response=resp)
        if attempt < MAX_ATTEMPTS:
            time.sleep(wait)

    assert last_exc is not None
    raise last_exc


def get_json(url: str) -> dict:
    resp = get(url)
    log().info("GET %s status=%d bytes=%d (json)", url, resp.status_code, len(resp.content))
    return resp.json()


def download(url: str, dest: Path, *, min_bytes: int = 1) -> tuple[Path, bool]:
    """Baixa `url` para `dest` se ainda não existir.

    Retorna (caminho, baixou_agora). Escreve primeiro num .part e só então
    renomeia, de modo que uma interrupção nunca deixa um arquivo truncado
    parecendo completo para a próxima execução.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists() and dest.stat().st_size >= min_bytes:
        log().info("SKIP %s (já existe, %d bytes)", dest.name, dest.stat().st_size)
        return dest, False

    part = dest.with_suffix(dest.suffix + ".part")
    resp = get(url, stream=True)
    total = 0
    with open(part, "wb") as fh:
        for chunk in resp.iter_content(chunk_size=1 << 16):
            if chunk:
                fh.write(chunk)
                total += len(chunk)

    if total < min_bytes:
        part.unlink(missing_ok=True)
        raise IOError(f"{url} devolveu apenas {total} bytes (mínimo {min_bytes})")

    os.replace(part, dest)
    log().info(
        "GET %s status=%d bytes=%d -> %s [%s]",
        url,
        resp.status_code,
        total,
        dest.relative_to(ACERVO.parent),
        _utc(),
    )
    return dest, True


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        try:
            return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            log().warning("MANIFEST.json ilegível; recomeçando do zero")
    return {"gerado_em": _utc(), "artefatos": {}}


def save_manifest(manifest: dict) -> None:
    manifest["gerado_em"] = _utc()
    ACERVO.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )


def record(manifest: dict, path: Path, *, fonte: str, origem: str, **extra) -> None:
    """Registra um artefato final (tamanho + sha256 + de onde veio)."""
    key = str(path.relative_to(ACERVO))
    manifest["artefatos"][key] = {
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "fonte": fonte,
        "origem": origem,
        "registrado_em": _utc(),
        **extra,
    }
    log().info("MANIFEST %s (%d bytes)", key, path.stat().st_size)
