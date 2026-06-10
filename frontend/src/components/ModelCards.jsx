import { pct, dataBr } from "../format";

/** Cards da média atual do modelo. `destaqueN` = quantos cartões grandes/em
 *  destaque (1 p/ presidente; 2 p/ senado, que elege 2). */
export default function ModelCards({ race, destaqueN = 1, pillLabel = "lidera a média" }) {
  const cands = race.candidatos || [];
  if (!cands.length) return null;
  const principais = cands.slice(0, Math.max(2, destaqueN));
  const demais = cands.slice(principais.length);

  return (
    <div>
      <div className="text-xs uppercase tracking-widest text-gray-400 font-semibold">
        Média do modelo hoje · {race.nPesquisas} pesquisas no histórico
      </div>

      <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-4">
        {principais.map((c, i) => (
          <BigCard key={c.nome} c={c} destaque={i < destaqueN}
                   pill={i < destaqueN ? pillLabel : null} />
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
    <span className="text-xs text-gray-400">
      banda {pct(c.banda[0])} – {pct(c.banda[1])}
    </span>
  );
}

function BigCard({ c, destaque, pill }) {
  return (
    <div
      className={`rounded-xl border bg-cardhi p-5 ${
        destaque ? "border-2 shadow-card" : "border-hair"
      }`}
      style={destaque ? { borderColor: c.cor } : {}}
    >
      <div className="flex items-center gap-2">
        <span className="h-3 w-3 rounded-full" style={{ background: c.cor }} />
        <span className="font-semibold text-petrol">{c.nome}</span>
        {pill && (
          <span className="ml-auto rounded-full bg-petrol/10 px-2 py-0.5 text-[11px] uppercase tracking-wide text-petrol">
            {pill}
          </span>
        )}
      </div>
      <div className="mt-2 num font-display text-5xl font-bold" style={{ color: c.cor }}>
        {pct(c.media)}
      </div>
      <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1">
        <Banda c={c} />
        {"pLiderHoje" in c && (
          <span className="text-xs text-texto font-medium">
            {fmtChance(c.pLiderHoje)} de chance de liderar hoje
          </span>
        )}
      </div>
      <div className="mt-3 text-xs text-gray-400">
        última pesquisa: {c.ultimaPesquisa.instituto} ({dataBr(c.ultimaPesquisa.data)}) —{" "}
        {pct(c.ultimaPesquisa.pct)}
      </div>
    </div>
  );
}

function SmallCard({ c }) {
  return (
    <div className="rounded-lg border border-hair bg-cardhi p-3">
      <div className="flex items-center gap-1.5 text-sm text-petrol font-medium">
        <span className="h-2 w-2 rounded-full" style={{ background: c.cor }} />
        {c.nome}
      </div>
      <div className="num mt-1 text-2xl font-bold text-petrol">{pct(c.media)}</div>
      <Banda c={c} />
    </div>
  );
}
