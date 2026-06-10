/** Transparência: o peso que o modelo dá a cada instituto. */
export default function WeightsPanel({ pesos, params }) {
  if (!pesos?.length) return null;
  return (
    <section className="rounded-2xl border border-hair bg-card shadow-card p-4 sm:p-6">
      <h2 className="text-sm font-semibold uppercase tracking-widest text-gray-400">
        Peso de cada instituto
      </h2>
      <p className="mt-1 text-xs leading-relaxed text-gray-500">
        Rating editorial (0–1) baseado no erro das pesquisas de véspera vs. o
        resultado oficial em 2018–2022. Multiplica o peso de cada pesquisa.
        Pesquisa de 2026 sem registro localizado no TSE leva fator{" "}
        {params?.penalSemRegistro ?? 0.5}×.
      </p>
      <ul className="mt-3 space-y-2">
        {pesos.map((p) => (
          <li key={p.instituto} className="flex items-center gap-3 text-sm">
            <span className="w-40 truncate text-texto" title={p.instituto}>
              {p.instituto}
              {!p.registradaTse && (
                <span className="ml-1 text-gray-400" title="sem registro TSE localizado">*</span>
              )}
            </span>
            <div className="h-2 flex-1 overflow-hidden rounded bg-hair">
              <div className="h-full rounded bg-gradient-to-r from-petrol to-azul"
                   style={{ width: `${p.rating * 100}%` }} />
            </div>
            <span className="num w-10 text-right text-gray-500">
              {p.rating.toFixed(2)}
            </span>
          </li>
        ))}
      </ul>
      <p className="mt-3 text-[11px] text-gray-400">
        * nenhum registro localizado no CSV de dados abertos do TSE para as
        pesquisas nacionais deste instituto.
      </p>
    </section>
  );
}
