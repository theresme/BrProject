import { useCallback, useEffect, useRef, useState } from "react";
import { fetchState } from "../api";

// pesquisas mudam em ritmo de horas — recheca a cada 5 min
const POLL_MS = 5 * 60_000;

export function usePoll() {
  const [state, setState] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastFetch, setLastFetch] = useState(null);
  const timer = useRef(null);

  const load = useCallback(async () => {
    try {
      const data = await fetchState();
      if (data.ready === false) {
        setError(data.error || "carregando…");
      } else {
        setState(data);
        setError(data.error || null);
        setLastFetch(new Date());
      }
    } catch (e) {
      setError(e.message || "falha de rede");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    timer.current = setInterval(load, POLL_MS);
    return () => clearInterval(timer.current);
  }, [load]);

  return { state, error, loading, lastFetch, refresh: load };
}
