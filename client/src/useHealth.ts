/**
 * "Which model am I actually talking to?"
 *
 * A question that should never require opening a dashboard. `GET /health` is
 * cheap and answers it, along with whether the database is reachable and
 * whether this deployment can search the live web.
 *
 * It doubles as the wake-up call for a sleeping free-tier service: by the time
 * you've typed your question, the cold start has already happened.
 */

import { useEffect, useState } from "react";

import { fetchHealth, type Health } from "./api";

/** The URL field fires on every keystroke; don't call the API on every one. */
const DEBOUNCE_MS = 400;

export function useHealth(baseUrl: string) {
  const [health, setHealth] = useState<Health | null>(null);
  const [checking, setChecking] = useState(false);

  useEffect(() => {
    if (!baseUrl) {
      setHealth(null);
      return;
    }

    const controller = new AbortController();
    setHealth(null);
    setChecking(true);

    const timer = setTimeout(() => {
      fetchHealth(baseUrl, controller.signal)
        .then(setHealth)
        // Unreachable, CORS-blocked, or not our API at all. The badge just says
        // "unreachable" — the real diagnosis belongs to the error box you get
        // when you actually try to ask something.
        .catch(() => setHealth(null))
        .finally(() => setChecking(false));
    }, DEBOUNCE_MS);

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [baseUrl]);

  return { health, checking };
}
