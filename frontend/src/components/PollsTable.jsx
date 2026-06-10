import { useState } from "react";
import { pct, int, periodo } from "../format";

const PAGE = 15;

/** As pesquisas como publicadas — com nº de registro no TSE quando casado. */
export default function PollsTable({ race, turno }) {
  const [shown, setShown] = useState(PAGE);
  const pesquisas = race.pesquisas || [];
  if (!pesquisas.length) return null;

  // candidatos a mostrar como colunas: os da média atual (1t) ou os 2 do confronto
  const nomes =
    turno === 1
      ? (race.candidatos || []).map((c) => c.nome)
      : topNames(pesquisas);
  const corDe = corMap(race);

  return (
    <section className="rounded-2xl border border-hair bg-card shadow-card p-4 sm:p-6">
      <h2 className="text-sm font-semibold uppercase tracking-widest text-gray-400">
        Últimas pesquisas publicadas {turno === 2 ? "(2º turno)" : ""}
      </h2>
      <p className="mt-1 text-xs text-gray-500">
        Números originais de cada instituto (sem ajuste do modelo).{" "}
        <span className="text-petrol font-medium">✓ TSE</span> = registro
        localizado no sistema PesqEle; passe o mouse para ver o protocolo.
      </p>

      <div className="mt-3 overflow-x-auto">
        <table className="w-full min-w-[640px] text-sm">
          <thead>
            <tr className="border-b-2 border-hair text-left text-xs uppercase tracking-wide text-gray-400">
              <th className="py-2 pr-3 font-semibold">Instituto</th>
              <th className="py-2 pr-3 font-semibold">Campo</th>
              {nomes.map((n) => (
                <th key={n} className="py-2 pr-3 text-right font-semibold whitespace-nowrap">
                  <span className="inline-block h-2 w-2 rounded-full mr-1"
                        style={{ background: corDe[n] || "#94a3b8" }} />
                  {n}
                </th>
              ))}
              <th className="py-2 pr-3 text-right font-semibold">Amostra</th>
              <th className="py-2 text-right font-semibold">TSE</th>
            </tr>
          </thead>
          <tbody>
            {pesquisas.slice(0, shown).map((p, i) => (
              <Row key={i} p={p} nomes={nomes} />
            ))}
          </tbody>
        </table>
      </div>

      {shown < pesquisas.length && (
        <button
          onClick={() => setShown((s) => s + PAGE)}
          className="mt-3 w-full rounded-lg border border-hair bg-bg px-4 py-2 text-sm text-texto hover:bg-hair/40"
        >
          mostrar mais ({pesquisas.length - shown} restantes)
        </button>
      )}
    </section>
  );
}

function Row({ p, nomes }) {
  const por = {};
  for (const r of p.resultados) por[r.candidato] = r.pct;
  const lider = nomes.reduce(
    (best, n) => (por[n] != null && (best == null || por[n] > por[best]) ? n : best),
    null
  );
  return (
    <tr className="border-b border-hair text-texto hover:bg-bg/70">
      <td className="py-2 pr-3 font-semibold text-petrol whitespace-nowrap">
        {p.instituto}
      </td>
      <td className="num py-2 pr-3 whitespace-nowrap text-gray-500">
        {periodo(p.dataInicio, p.dataFim)}
      </td>
      {nomes.map((n) => (
        <td key={n}
            className={`num py-2 pr-3 text-right ${n === lider ? "font-bold text-petrol" : ""}`}>
          {por[n] != null ? pct(por[n]) : "—"}
        </td>
      ))}
      <td className="num py-2 pr-3 text-right text-gray-500">
        {p.amostra ? int(p.amostra) : "—"}
        {p.margemErro ? <span className="text-gray-400"> ±{p.margemErro}</span> : null}
      </td>
      <td className="py-2 text-right">
        {p.tseRegistro ? (
          <span className="cursor-help font-semibold text-petrol"
                title={`Registro ${p.tseRegistro}\n${p.tseEmpresa || ""}`}>
            ✓
          </span>
        ) : (
          <span className="cursor-help text-gray-300"
                title="Registro não localizado no CSV de dados abertos do TSE (pesquisa antiga ou nome divergente)">
            —
          </span>
        )}
      </td>
    </tr>
  );
}

function topNames(pesquisas) {
  const freq = {};
  for (const p of pesquisas.slice(0, 30)) {
    for (const r of p.resultados) {
      if (r.isCandidate) freq[r.candidato] = (freq[r.candidato] || 0) + 1;
    }
  }
  return Object.entries(freq).sort((a, b) => b[1] - a[1]).slice(0, 6).map(([n]) => n);
}

function corMap(race) {
  const m = {};
  for (const c of race.candidatos || []) m[c.nome] = c.cor;
  for (const mu of race.matchups || []) {
    for (const c of mu.candidatos) m[c.nome] = c.cor;
  }
  return m;
}
