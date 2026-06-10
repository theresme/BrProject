export default function Header({ lastFetch, fonte, onRefresh, error }) {
  return (
    <header>
      <div className="flex items-center gap-2 text-xs uppercase tracking-widest text-petrol font-semibold">
        <span className="inline-block h-2 w-2 rounded-full bg-ambar" />
        Eleições 2026 · Presidente
      </div>
      <div className="mt-2 flex flex-wrap items-end justify-between gap-3">
        <h1 className="font-display text-3xl sm:text-4xl font-bold text-petrol">
          A média das pesquisas
        </h1>
        <div className="flex items-center gap-3 text-xs text-gray-500">
          {error && <span className="text-ambar">⚠ {error}</span>}
          <span>
            fonte: <span className="text-texto font-medium">{fonte || "—"}</span>
            {" · "}atualizado{" "}
            {lastFetch ? lastFetch.toLocaleTimeString("pt-BR") : "—"}
          </span>
          <button
            onClick={onRefresh}
            className="rounded-md border border-hair bg-card px-2 py-1 text-petrol hover:bg-bg"
            title="Atualizar agora"
          >
            ↻
          </button>
        </div>
      </div>
      <p className="mt-2 max-w-3xl text-sm leading-relaxed text-texto">
        Agregador não-oficial das pesquisas de intenção de voto para presidente
        registradas no TSE, combinadas por um modelo estatístico que pondera
        recência, desempenho histórico de cada instituto e tamanho da amostra.
      </p>
    </header>
  );
}
