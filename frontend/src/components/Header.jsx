export default function Header({ lastFetch, fonte, onRefresh, error }) {
  return (
    <header>
      <div className="flex items-center gap-2 text-xs uppercase tracking-widest text-emerald-500/90 font-semibold">
        <span className="inline-block h-2 w-2 rounded-full bg-brasil" />
        Eleições 2026 · Presidente
      </div>
      <div className="mt-2 flex flex-wrap items-end justify-between gap-3">
        <h1 className="font-display text-3xl sm:text-4xl font-bold text-gray-100">
          A média das pesquisas
        </h1>
        <div className="flex items-center gap-3 text-xs text-gray-500">
          {error && <span className="text-amber-400">⚠ {error}</span>}
          <span>
            fonte: <span className="text-gray-300">{fonte || "—"}</span>
            {" · "}atualizado{" "}
            {lastFetch ? lastFetch.toLocaleTimeString("pt-BR") : "—"}
          </span>
          <button
            onClick={onRefresh}
            className="rounded-md border border-hair bg-panel px-2 py-1 text-gray-300 hover:bg-panel2"
            title="Atualizar agora"
          >
            ↻
          </button>
        </div>
      </div>
      <p className="mt-2 max-w-3xl text-sm leading-relaxed text-gray-400">
        Agregador não-oficial das pesquisas de intenção de voto para presidente
        registradas no TSE, combinadas por um modelo estatístico que pondera
        recência, desempenho histórico de cada instituto e tamanho da amostra.
      </p>
    </header>
  );
}
