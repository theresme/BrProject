import asyncio

import main


async def run():
    await main.poll_once()
    s = main.cache.state
    if s is None:
        print("ERRO:", main.cache.last_error)
        return
    r1 = s["races"]["presidente-1t"]
    print("1T  nPesquisas:", r1["nPesquisas"])
    for c in r1["candidatos"][:6]:
        print("  ", c["nome"], c["media"], c["banda"], "pLider=", c.get("pLiderHoje"), c["cor"])
    print("trend pts:", len(r1["trend"]), r1["trend"][0]["date"], "->", r1["trend"][-1]["date"])
    print("houseEffects:", dict(list(r1["houseEffects"].items())[:6]))
    for m in s["races"]["presidente-2t"]["matchups"][:4]:
        a, b = m["candidatos"]
        print("2T", m["matchup"], "->", a["media"], "x", b["media"],
              "(n=%d, recente=%s)" % (m["nPesquisas"], m["maisRecente"]))
    print("pesos:", [(p["instituto"], p["rating"], p["registradaTse"]) for p in s["pesos"]][:8])
    print("pesquisas na tabela:", len(r1["pesquisas"]), "| 1a:",
          r1["pesquisas"][0]["instituto"], r1["pesquisas"][0]["dataFim"],
          r1["pesquisas"][0]["tseRegistro"])


asyncio.run(run())
