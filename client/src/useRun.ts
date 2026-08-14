/**
 * The accept-and-poll pattern, as a React hook.
 *
 * This file is the reason the client is a real app and not a single HTML file.
 * The three fetch calls in api.ts are the easy part — copy them anywhere. The
 * hard part is everything around them, and it is all here:
 *
 *   - cancelling the in-flight run when the component unmounts, so a poll loop
 *     doesn't outlive the screen that started it and quietly hammer your
 *     free-tier server until the tab closes
 *   - cancelling the previous run when the user asks a second question, so two
 *     loops don't fight over the same state
 *   - waiting for each poll before sending the next, instead of firing them on
 *     a fixed timer and stacking requests when the server is slow
 *
 * Get these wrong and it still looks fine on localhost. That's the trap.
 */

import { useCallback, useEffect, useRef, useState } from "react";

import {
  createRun,
  createRunNaive,
  readRun,
  type Run,
  type RunStatus,
  type Step,
} from "./api";

/** Fast enough to feel live, slow enough not to hammer a free-tier server. */
const POLL_MS = 1500;

export type ClientStatus = "idle" | RunStatus;

/** Resolves after `ms` — or bails out the instant the run is cancelled. */
function sleep(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(resolve, ms);
    signal.addEventListener(
      "abort",
      () => {
        clearTimeout(timer);
        reject(signal.reason);
      },
      { once: true },
    );
  });
}

/** Every one of these has eaten someone's afternoon at least once. */
function explain(err: unknown): string {
  const message = err instanceof Error ? err.message : String(err);
  return (
    message +
    "\n\nCommon causes:\n" +
    "• Backend URL is wrong or the server isn't running\n" +
    "• Backend is cold-starting on a free tier — wait a minute and retry\n" +
    "• CORS: this page's origin isn't in ALLOWED_ORIGINS on the server\n" +
    "• Mixed content: an https page can't call an http backend"
  );
}

export function useRun(baseUrl: string) {
  const [status, setStatus] = useState<ClientStatus>("idle");
  const [steps, setSteps] = useState<Step[]>([]);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);

  const abortRef = useRef<AbortController | null>(null);
  const busy = status === "queued" || status === "running";

  // Unmount: stop polling. The browser will not do this for you — a forgotten
  // loop keeps calling your API for as long as the tab is open.
  useEffect(() => () => abortRef.current?.abort(), []);

  // The elapsed clock, kept separate so the run logic never touches a timer.
  // `busy` stays true across queued -> running, so the clock doesn't restart.
  useEffect(() => {
    if (!busy) return;
    const startedAt = Date.now();
    const timer = setInterval(
      () => setElapsed((Date.now() - startedAt) / 1000),
      100,
    );
    return () => clearInterval(timer);
  }, [busy]);

  const ask = useCallback(
    async (query: string, naive: boolean) => {
      // A second question cancels the first, in flight, mid-poll.
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      const { signal } = controller;

      setSteps([]);
      setResult(null);
      setError(null);
      setElapsed(0);
      setStatus("queued");

      // Both paths end here, with whatever the run finally settled on.
      const finish = (run: Run) => {
        setStatus(run.status);
        if (run.status === "error") setError(run.error ?? "The run failed.");
        else setResult(run.result);
      };

      try {
        if (naive) {
          // One request. No progress is possible — there's nothing to poll,
          // because the answer and the work arrive together or not at all.
          setStatus("running");
          const snapshot = await createRunNaive(baseUrl, query, signal);
          setSteps(snapshot.steps);
          finish(snapshot.run);
          return;
        }

        // 1. Hand over the job. Back in ~200ms with an id.
        const runId = await createRun(baseUrl, query, signal);

        // 2. Ask "done yet?" until it settles. Awaiting inside the loop means
        //    a slow poll delays the next one rather than overlapping with it.
        for (;;) {
          await sleep(POLL_MS, signal);
          const snapshot = await readRun(baseUrl, runId, signal);

          setStatus(snapshot.run.status);
          setSteps(snapshot.steps);

          if (snapshot.run.status === "done" || snapshot.run.status === "error") {
            finish(snapshot.run);
            return;
          }
        }
      } catch (err) {
        // We cancelled it ourselves — not a failure, and not worth a red box.
        if (signal.aborted) return;
        setStatus("error");
        setError(explain(err));
      }
    },
    [baseUrl],
  );

  return { status, steps, result, error, elapsed, busy, ask };
}
