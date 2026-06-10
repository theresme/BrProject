import { pct, dataBr } from "../format";

/** Cards da média atual do modelo — 1º turno. */
export default function ModelCards({ race }) {
  const cands = race.candidatos || [];
  if (!cands.length) return null;
  const [lider, ...resto] = cands;
  const principais = [lider, ...resto.slice(0, 1)];
  const demais = resto.slice(1);

  return (
    <div>
      <div className="text-xs uppercase tracking-widest text-gray-500 font-semibold">
        Média do modelo hoje · {race.nPesquisas} pesquisas no histórico
      </div>

      <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-4">
        {principais.map((c, i) => (
          <BigCard key={c.nome} c={c} destaque={i === 0} />
        ))}
      </div>

      {demais.length > 0 && (
        <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-3">
          {demais.map((c) => (
            <SmallCard key={c.nome} c={c} />
          ))}
        </div>
      )}
    </div>
  );
}

function fmtChance(p) {
  if (p >= 0.995) return ">99%";
  if (p <= 0.005) return "<1%";
  return `${Math.round(p * 100)}%`;
}

function Banda({ c }) {
  return (
    <span className="text-xs text-gray-500">
      banda {pct(c.banda[0])} – {pct(c.banda[1])}
    </span>
  );
}

function BigCard({ c, destaque }) {
  return (
    <div
      className={`rounded-xl border bg-panel/70 p-5 ${
        destaque ? "border-2" : "border-hair"
      }`}
      style={destaque ? { borderColor: c.cor } : {}}
    >
      <div className="flex items-center gap-2">
        <span className="h-3 w-3 rounded-full" style={{ background: c.cor }} />
        <span className="font-semibold text-gray-100">{c.nome}</span>
        {destaque && (
          <span className="ml-auto rounded-full bg-white/10 px-2 py-0.5 text-[11px] uppercase tracking-wide text-gray-300">
            lidera a média
          </span>
        )}
      </div>
      <div className="mt-2 num font-display text-5xl font-bold" style={{ color: c.cor }}>
        {pct(c.media)}
      </div>
      <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1">
        <Banda c={c} />
        {"pLiderHoje" in c && (
          <span className="text-xs text-gray-400">
            {fmtChance(c.pLiderHoje)} de chance de liderar hoje
          </span>
        )}
      </div>
      <div className="mt-3 text-xs text-gray-500">
        última pesquisa: {c.ultimaPesquisa.instituto} ({dataBr(c.ultimaPesquisa.data)}) —{" "}
        {pct(c.ultimaPesquisa.pct)}
      </div>
    </div>
  );
}

function SmallCard({ c }) {
  return (
    <div className="rounded-lg border border-hair bg-panel/50 p-3">
      <div className="flex items-center gap-1.5 text-sm text-gray-200">
        <span className="h-2 w-2 rounded-full" style={{ background: c.cor }} />
        {c.nome}
      </div>
      <div className="num mt-1 text-2xl font-bold text-gray-100">{pct(c.media)}</div>
      <Banda c={c} />
    </div>
  );
}
