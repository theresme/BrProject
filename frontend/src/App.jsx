import { useState } from "react";
import { usePoll } from "./hooks/usePoll";
import Header from "./components/Header";
import Disclaimer from "./components/Disclaimer";
import ModelCards from "./components/ModelCards";
import TrendChart from "./components/TrendChart";
import Matchups from "./components/Matchups";
import PollsTable from "./components/PollsTable";
import WeightsPanel from "./components/WeightsPanel";
import Methodology from "./components/Methodology";
import Footer from "./components/Footer";

export default function App() {
  const { state, error, loading, lastFetch, refresh } = usePoll();
  const [turno, setTurno] = useState(1);

  const race1 = state?.races?.["presidente-1t"];
  const race2 = state?.races?.["presidente-2t"];
  const race = turno === 1 ? race1 : race2;

  return (
    <div className="min-h-full">
      <div className="mx-auto max-w-5xl px-4 py-8 sm:py-12">
        <Header lastFetch={lastFetch} fonte={state?.fonte} onRefresh={refresh}
                error={error && state ? error : null} />

        <Disclaimer />

        {loading && !state && <LoadingState />}
        {!loading && !state && <ErrorState error={error} onRetry={refresh} />}

        {state && (
          <main className="mt-6 space-y-6">
            <TurnoTabs turno={turno} setTurno={setTurno} race2={race2} />

            {turno === 1 && race1 && (
              <>
                <section className="hero-glow relative overflow-hidden rounded-2xl bg-card border border-hair border-t-[3px] border-t-petrol shadow-card p-6 sm:p-8">
                  <ModelCards race={race1} />
                </section>
                <TrendChart race={race1} cores={state.cores} />
                <PollsTable race={race1} turno={1} />
              </>
            )}

            {turno === 2 && race2 && (
              <>
                <Matchups race={race2} />
                <PollsTable race={race2} turno={2} />
              </>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <WeightsPanel pesos={state.pesos} params={state.modeloParams} />
              <Methodology params={state.modeloParams} race={race} />
            </div>
          </main>
        )}

        <Footer />
      </div>
    </div>
  );
}

function TurnoTabs({ turno, setTurno, race2 }) {
  const tabs = [
    { id: 1, label: "1º turno" },
    { id: 2, label: "2º turno (cenários)", disabled: !race2?.matchups?.length },
  ];
  return (
    <div className="flex gap-2">
      {tabs.map((t) => (
        <button
          key={t.id}
          disabled={t.disabled}
          onClick={() => setTurno(t.id)}
          className={`rounded-lg px-4 py-2 text-sm font-semibold border transition-colors ${
            turno === t.id
              ? "bg-petrol border-petrol text-white shadow-sm"
              : "bg-card border-hair text-texto hover:bg-bg"
          } ${t.disabled ? "opacity-40 cursor-not-allowed" : ""}`}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}

function LoadingState() {
  return (
    <div className="mt-16 flex flex-col items-center text-gray-400">
      <div className="h-10 w-10 rounded-full border-2 border-hair border-t-petrol animate-spin" />
      <p className="mt-4 text-sm">Carregando pesquisas…</p>
    </div>
  );
}

function ErrorState({ error, onRetry }) {
  return (
    <div className="mt-16 flex flex-col items-center text-center">
      <div className="text-4xl mb-3">⚠️</div>
      <p className="text-petrol font-semibold">Não foi possível carregar os dados</p>
      <p className="text-sm text-gray-500 mt-1 max-w-md">{error || "tente novamente"}</p>
      <button
        onClick={onRetry}
        className="mt-4 rounded-lg border border-hair bg-card px-4 py-2 text-sm text-texto hover:bg-bg"
      >
        Tentar de novo
      </button>
    </div>
  );
}
