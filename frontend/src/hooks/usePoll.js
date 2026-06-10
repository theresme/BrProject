import { useCallback, useEffect, useRef, useState } from "react";
import { fetchState } from "../api";

// pesquisas mudam em ritmo de horas — recheca a cada 5 min
const POLL_MS = 5 * 60_000;
const BOOT_RETRY_DELAYS_MS = [
  1_200, 1_800, 2_500, 3_500, 5_000, 7_000, 10_000, 15_000, 20_000, 30_000,
];

export function usePoll() {
  const [state, setState] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastFetch, setLastFetch] = useState(null);
  const timer = useRef(null);
  const retryTimer = useRef(null);
  const bootAttempt = useRef(0);
  const stateRef = useRef(null);
  const inFlight = useRef(false);

  const clearRetry = useCallback(() => {
    if (retryTimer.current) {
      clearTimeout(retryTimer.current);
      retryTimer.current = null;
    }
  }, []);

  const scheduleBootRetry = useCallback(() => {
    const attempt = bootAttempt.current;
    if (attempt >= BOOT_RETRY_DELAYS_MS.length) {
      return false;
    }
    clearRetry();
    retryTimer.current = setTimeout(() => {
      retryTimer.current = null;
      load();
    }, BOOT_RETRY_DELAYS_MS[attempt]);
    bootAttempt.current = attempt + 1;
    return true;
  }, [clearRetry]);

  const load = useCallback(async ({ manual = false } = {}) => {
    if (inFlight.current) return;
    if (manual) {
      bootAttempt.current = 0;
      clearRetry();
      setError(null);
      if (!stateRef.current) setLoading(true);
    }
    inFlight.current = true;
    try {
      const data = await fetchState();
      if (data.ready === false) {
        if (!stateRef.current && scheduleBootRetry()) {
          setLoading(true);
          setError(null);
        } else if (!stateRef.current) {
          setLoading(false);
          setError(data.error || "Ainda estamos preparando as pesquisas. Tente novamente em instantes.");
        }
      } else {
        stateRef.current = data;
        setState(data);
        setError(data.error || null);
        setLastFetch(new Date());
        setLoading(false);
        bootAttempt.current = 0;
        clearRetry();
      }
    } catch (e) {
      if (!stateRef.current && scheduleBootRetry()) {
        setLoading(true);
        setError(null);
      } else {
        setError(e.message || "falha de rede");
        setLoading(false);
      }
    } finally {
      inFlight.current = false;
    }
  }, [clearRetry, scheduleBootRetry]);

  const refresh = useCallback(() => load({ manual: true }), [load]);

  useEffect(() => {
    load();
    timer.current = setInterval(load, POLL_MS);
    return () => {
      clearInterval(timer.current);
      clearRetry();
    };
  }, [clearRetry, load]);

  return { state, error, loading, lastFetch, refresh };
}
