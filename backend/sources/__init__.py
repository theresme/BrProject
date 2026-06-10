from .base import Poll, PollResult, Source


def get_source(name: str) -> Source:
    if name == "mock":
        from .mock import MockSource
        return MockSource()
    if name == "wikipedia":
        from .wikipedia import WikipediaSource
        return WikipediaSource()
    raise ValueError(f"fonte desconhecida: {name!r} (use 'wikipedia' ou 'mock')")


__all__ = ["Poll", "PollResult", "Source", "get_source"]
