import { useEffect } from "react";
import ModelCards from "./ModelCards";
import TrendChart from "./TrendChart";
import PollsTable from "./PollsTable";

const UF_NOMES = {
  AC: "Acre", AL: "Alagoas", AP: "Amapá", AM: "Amazonas", BA: "Bahia",
  CE: "Ceará", DF: "Distrito Federal", ES: "Espírito Santo", GO: "Goiás",
  MA: "Maranhão", MT: "Mato Grosso", MS: "Mato Grosso do Sul", MG: "Minas Gerais",
  PA: "Pará", PB: "Paraíba", PR: "Paraná", PE: "Pernambuco", PI: "Piauí",
  RJ: "Rio de Janeiro", RN: "Rio Grande do Norte", RS: "Rio Grande do Sul",
  RO: "Rondônia", RR: "Roraima", SC: "Santa Catarina", SP: "São Paulo",
  SE: "Sergipe", TO: "Tocantins",
};

export default function SenateView({ senado, cores, uf, setUf }) {
  const ufs = Object.keys(senado || {}).sort();

  useEffect(() => {
    if (ufs.length && !ufs.includes(uf)) setUf(ufs[0]);
  }, [setUf, ufs, uf]);

  if (!ufs.length) {
    return (
      <div className="rounded-2xl border border-hair bg-card shadow-card p-8 text-center">
        <div className="text-3xl mb-2">🏛️</div>
        <p className="text-petrol font-semibold">Ainda sem pesquisas de Senado</p>
        <p className="mt-1 text-sm text-gray-500 max-w-md mx-auto">
          Nenhum estado com tabela de pesquisas de Senado disponível no momento.
          Conforme as fontes forem publicadas, os estados aparecem aqui
          automaticamente.
        </p>
      </div>
    );
  }

  const race = senado[uf];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <label className="text-sm text-texto font-medium">Estado:</label>
        <select
          value={uf || ""}
          onChange={(e) => setUf(e.target.value)}
          className="rounded-lg border border-hair bg-card px-3 py-2 text-sm font-semibold text-petrol shadow-sm focus:outline-none focus:ring-2 focus:ring-petrol/30"
        >
          {ufs.map((u) => (
            <option key={u} value={u}>
              {UF_NOMES[u] || u} ({u})
            </option>
          ))}
        </select>
        <span className="text-xs text-gray-400">
          {ufs.length} estado{ufs.length > 1 ? "s" : ""} com pesquisas
        </span>
      </div>

      <div className="rounded-xl border-l-4 border-petrol bg-petrol/5 px-4 py-3 text-sm leading-relaxed text-texto">
        Em 2026, cada estado elege <strong>2 senadores</strong> (o eleitor vota
        em dois nomes). Os <strong>dois primeiros</strong> da média tendem a se
        eleger. Ainda não há candidaturas oficiais — entram os nomes que
        aparecem nas pesquisas.
      </div>

      <section className="hero-glow relative overflow-hidden rounded-2xl bg-card border border-hair border-t-[3px] border-t-petrol shadow-card p-6 sm:p-8">
        <ModelCards race={race} destaqueN={2} pillLabel="tende a eleger-se" />
      </section>

      <TrendChart race={race} cores={cores} />
      <PollsTable race={race} turno={1} />
    </div>
  );
}
