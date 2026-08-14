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

/**
 * A sleeping free-tier service takes ~50s to answer, and the browser gives up
 * long before that. So the first check failing means "cold" far more often than
 * it means "down" — and asking once would leave a backend that woke up ten
 * seconds later labelled unreachable until you reload the page.
 *
 * Widening gaps, then one steady 20s beat: long enough not to hammer a free
 * tier, short enough that the badge fixes itself while you read the question.
 */
const RETRY_MS = [2_000, 5_000, 10_000, 20_000];

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

    let timer: ReturnType<typeof setTimeout>;

    const check = (failures: number) => {
      setChecking(true);
      fetchHealth(baseUrl, controller.signal)
        .then((result) => {
          setHealth(result);
          setChecking(false);
        })
        // Unreachable, CORS-blocked, still cold, or not our API at all. The
        // badge just says "unreachable" — the real diagnosis belongs to the
        // error box you get when you actually try to ask something.
        .catch(() => {
          // We cancelled it ourselves: the URL changed, or the page is gone.
          // Retrying here would race the check that replaced this one.
          if (controller.signal.aborted) return;
          setHealth(null);
          setChecking(false);
          timer = setTimeout(
            () => check(failures + 1),
            RETRY_MS[Math.min(failures, RETRY_MS.length - 1)],
          );
        });
    };

    timer = setTimeout(() => check(0), DEBOUNCE_MS);

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [baseUrl]);

  return { health, checking };
}
