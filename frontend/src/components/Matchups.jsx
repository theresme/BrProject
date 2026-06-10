import { pct, dataBr } from "../format";

/** 2º turno: um card por confronto simulado. */
export default function Matchups({ race }) {
  const ms = race.matchups || [];
  if (!ms.length) return null;
  return (
    <section className="space-y-4">
      <h2 className="text-sm font-semibold uppercase tracking-widest text-gray-400">
        Cenários de 2º turno — média do modelo por confronto
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {ms.map((m) => (
          <MatchupCard key={m.matchup} m={m} />
        ))}
      </div>
    </section>
  );
}

function MatchupCard({ m }) {
  const [a, b] = m.candidatos; // já vem ordenado por média desc
  const total = a.media + b.media;
  const wA = (a.media / total) * 100;

  return (
    <div className="rounded-xl border border-hair bg-card shadow-card p-4">
      <div className="flex items-center justify-between text-sm">
        <Nome c={a} bold />
        <span className="text-[11px] text-gray-400">
          {m.nPesquisas} pesquisas · até {dataBr(m.maisRecente)}
        </span>
        <Nome c={b} right />
      </div>

      <div className="mt-3 flex h-7 overflow-hidden rounded-md">
        <div className="flex items-center pl-2 text-xs font-bold text-white/95"
             style={{ width: `${wA}%`, background: a.cor }}>
          {pct(a.media)}
        </div>
        <div className="flex items-center justify-end pr-2 text-xs font-bold text-white/95"
             style={{ width: `${100 - wA}%`, background: b.cor }}>
          {pct(b.media)}
        </div>
      </div>

      <div className="mt-2 flex justify-between text-[11px] text-gray-400">
        <span>banda {pct(a.banda[0])}–{pct(a.banda[1])}</span>
        <span className="font-medium text-texto">vantagem {pct(a.media - b.media)}</span>
        <span>banda {pct(b.banda[0])}–{pct(b.banda[1])}</span>
      </div>
    </div>
  );
}

function Nome({ c, bold, right }) {
  return (
    <span className={`flex items-center gap-1.5 ${right ? "flex-row-reverse" : ""}`}>
      <span className="h-2.5 w-2.5 rounded-full" style={{ background: c.cor }} />
      <span className={`${bold ? "font-bold" : "font-semibold"} text-petrol`}>
        {c.nome}
      </span>
    </span>
  );
}
