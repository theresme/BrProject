"""O modelo — média ponderada das pesquisas, em 2 passadas.

NÃO é uma pesquisa. É um agregado estatístico com pesos transparentes:

  peso = w_tempo × w_instituto × w_amostra × w_registro

  - w_tempo:     0.5^(idade_dias / half_life)  (pesquisa velha vale menos)
  - w_instituto: rating 0..1 por desempenho histórico (config.py, editorial)
  - w_amostra:   sqrt(n/1000), com teto (amostra grande ajuda até certo ponto)
  - w_registro:  penalização p/ pesquisa de 2026 sem registro localizado no TSE

Passada 1: curva diária por candidato (kernel exponencial bilateral).
House effect: desvio médio do instituto vs. a curva da passada 1 (mín. 3
pesquisas), encolhido por `house_effect_shrink`.
Passada 2: mesma curva sobre os valores corrigidos de house effect.

"Hoje" usa kernel unilateral (só o passado). A banda combina a dispersão
residual entre institutos com o erro amostral médio e um termo estrutural
(pesquisas erram além da margem declarada). P(liderança) sai de Monte Carlo
sobre a banda — é "quem estaria na frente HOJE segundo o modelo", não uma
previsão da eleição.
"""
from __future__ import annotations

import math
import random
from collections import defaultdict
from datetime import date, timedelta

import config
from sources.base import Poll

CFG = config.MODEL


def _w_tempo(age_days: float, half_life: float) -> float:
    return 0.5 ** (max(age_days, 0.0) / half_life)


def _w_amostra(n: int | None) -> float:
    if not n or n <= 0:
        return 1.0
    return min(math.sqrt(n / CFG.sample_ref), CFG.sample_weight_cap)


def _w_registro(p: Poll) -> float:
    if p.tse_registro:
        return 1.0
    # registro PesqEle só cobre o ciclo 2026: não penaliza pesquisa antiga
    if p.data_fim and p.data_fim >= date(2026, 1, 1):
        return config.UNREGISTERED_PENALTY
    return 1.0


def poll_weight(p: Poll, ref: date, one_sided: bool = True) -> float:
    age = (ref - p.data_fim).days
    if one_sided and age < 0:
        return 0.0
    return (
        _w_tempo(abs(age), CFG.half_life_days)
        * config.institute_rating(p.instituto, p.race_id)
        * _w_amostra(p.amostra)
        * _w_registro(p)
    )


def _curve(polls_by_cand: dict[str, list[tuple[Poll, float]]],
           days: list[date], one_sided_last: bool = True) -> dict[str, dict[date, float]]:
    """Curva diária por candidato. (Poll, pct) já corrigidos de house effect."""
    out: dict[str, dict[date, float]] = {}
    for cand, items in polls_by_cand.items():
        serie: dict[date, float] = {}
        for d in days:
            one_sided = one_sided_last and d == days[-1]
            num = den = 0.0
            for p, pct in items:
                w = poll_weight(p, d, one_sided=one_sided)
                if w > 0:
                    num += w * pct
                    den += w
            if den > 0:
                serie[d] = num / den
        out[cand] = serie
    return out


def aggregate_race(polls: list[Poll], today: date | None = None) -> dict:
    """Roda o modelo para UMA disputa (lista de polls do mesmo race_id)."""
    today = today or date.today()
    polls = [p for p in polls if p.data_fim and p.data_fim <= today]
    if not polls:
        return {"candidatos": [], "trend": [], "nPesquisas": 0}

    # ---- grade de dias do gráfico (semanal até o mês atual, diária depois)
    start = today - timedelta(days=CFG.trend_start_days_back)
    start = max(start, min(p.data_fim for p in polls))
    days: list[date] = []
    d = start
    while d < today - timedelta(days=30):
        days.append(d)
        d += timedelta(days=7)
    while d <= today:
        days.append(d)
        d += timedelta(days=1)
    if days[-1] != today:
        days.append(today)

    # ---- passada 1: curva crua
    by_cand: dict[str, list[tuple[Poll, float]]] = defaultdict(list)
    for p in polls:
        for r in p.resultados:
            if r.is_candidate:
                by_cand[r.candidato].append((p, r.pct))
    curve1 = _curve(by_cand, days)

    # ---- house effects: desvio médio (ponderado) do instituto vs. curva 1
    he_sum: dict[tuple[str, str], float] = defaultdict(float)
    he_w: dict[tuple[str, str], float] = defaultdict(float)
    he_n: dict[tuple[str, str], int] = defaultdict(int)
    for cand, items in by_cand.items():
        serie = curve1[cand]
        for p, pct in items:
            ref = serie.get(min(days, key=lambda x: abs((x - p.data_fim).days)))
            if ref is None:
                continue
            w = config.institute_rating(p.instituto, p.race_id) * _w_amostra(p.amostra)
            key = (p.instituto, cand)
            he_sum[key] += w * (pct - ref)
            he_w[key] += w
            he_n[key] += 1
    house: dict[tuple[str, str], float] = {}
    for key, s in he_sum.items():
        if he_n[key] >= CFG.house_effect_min_polls and he_w[key] > 0:
            house[key] = CFG.house_effect_shrink * (s / he_w[key])

    # ---- passada 2: curva sobre valores corrigidos
    by_cand_adj: dict[str, list[tuple[Poll, float]]] = defaultdict(list)
    for cand, items in by_cand.items():
        for p, pct in items:
            adj = pct - house.get((p.instituto, cand), 0.0)
            by_cand_adj[cand].append((p, adj))
    curve2 = _curve(by_cand_adj, days)

    # ---- média atual + banda por candidato
    candidatos = []
    sigmas: dict[str, float] = {}
    for cand, items in by_cand_adj.items():
        serie = curve2[cand]
        media = serie.get(today)
        if media is None:
            continue
        # candidato precisa estar sendo testado em pesquisas recentes
        ultima_data = max(p.data_fim for p, _ in items)
        recentes = sum(1 for p, _ in items
                       if (today - p.data_fim).days <= CFG.max_age_days)
        if ((today - ultima_data).days > CFG.candidate_max_silence_days
                or recentes < CFG.candidate_min_recent_polls):
            continue
        # dispersão residual ponderada das pesquisas recentes vs. a média
        num = den = 0.0
        n_rec = 0
        me_recent: list[float] = []
        for p, pct in items:
            w = poll_weight(p, today)
            if w <= 0 or (today - p.data_fim).days > CFG.max_age_days:
                continue
            num += w * (pct - media) ** 2
            den += w
            n_rec += 1
            if p.margem_erro:
                me_recent.append(p.margem_erro)
        disp = math.sqrt(num / den) if den > 0 else 2.0
        # erro-padrão da média encolhe com nº efetivo de pesquisas
        se = disp / math.sqrt(max(n_rec, 1))
        me_med = (sum(me_recent) / len(me_recent)) if me_recent else 2.0
        sigma = math.sqrt(se ** 2 + (me_med / 2) ** 2 + CFG.structural_pp ** 2)
        sigmas[cand] = sigma
        ultima = max(items, key=lambda it: it[0].data_fim)
        candidatos.append({
            "nome": cand,
            "media": round(media, 1),
            "banda": [round(max(0.0, media - CFG.band_z * sigma), 1),
                      round(media + CFG.band_z * sigma, 1)],
            "nRecentes": n_rec,
            "ultimaPesquisa": {
                "instituto": ultima[0].instituto,
                "data": ultima[0].data_fim.isoformat(),
                "pct": ultima[1] + house.get((ultima[0].instituto, cand), 0.0),
            },
        })
    candidatos.sort(key=lambda c: -c["media"])

    # ---- P(liderança hoje) por Monte Carlo
    if len(candidatos) >= 2:
        rng = random.Random(20261004)
        wins = defaultdict(int)
        nomes = [c["nome"] for c in candidatos]
        medias = [c["media"] for c in candidatos]
        for _ in range(CFG.n_sims):
            draw = [rng.gauss(m, sigmas[n]) for n, m in zip(nomes, medias)]
            wins[nomes[draw.index(max(draw))]] += 1
        for c in candidatos:
            c["pLiderHoje"] = round(wins[c["nome"]] / CFG.n_sims, 3)

    # ---- série do gráfico
    trend = []
    for d in days:
        vals = {c: round(curve2[c][d], 2) for c in curve2 if d in curve2[c]}
        if vals:
            trend.append({"date": d.isoformat(), "values": vals})

    return {
        "candidatos": candidatos,
        "trend": trend,
        "houseEffects": {
            f"{inst}|{cand}": round(v, 2) for (inst, cand), v in house.items()
        },
        "nPesquisas": len({p.key for p in polls}),
        "janelaDias": CFG.max_age_days,
        "meiaVidaDias": CFG.half_life_days,
    }


def aggregate_matchups(polls: list[Poll], today: date | None = None) -> list[dict]:
    """2º turno: agrega cada confronto (cenário) separadamente."""
    today = today or date.today()
    by_matchup: dict[str, list[Poll]] = defaultdict(list)
    for p in polls:
        cands = sorted(r.candidato for r in p.resultados if r.is_candidate)
        if len(cands) == 2:
            by_matchup[" × ".join(cands)].append(p)

    out = []
    for matchup, ps in by_matchup.items():
        agg = aggregate_race(ps, today)
        if len(agg["candidatos"]) != 2:
            continue
        recencia = max(p.data_fim for p in ps)
        out.append({
            "matchup": matchup,
            "candidatos": agg["candidatos"],
            "trend": agg["trend"],
            "nPesquisas": agg["nPesquisas"],
            "maisRecente": recencia.isoformat(),
        })
    # mais pesquisado e mais recente primeiro
    out.sort(key=lambda m: (-m["nPesquisas"], m["maisRecente"]), reverse=False)
    out.sort(key=lambda m: m["maisRecente"], reverse=True)
    out.sort(key=lambda m: -m["nPesquisas"])
    return out
