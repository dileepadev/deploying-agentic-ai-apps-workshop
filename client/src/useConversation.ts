/**
 * The accept-and-poll pattern, as a React hook — now with a conversation.
 *
 * This file is the reason the client is a real app and not a single HTML file.
 * The fetch calls in api.ts are the easy part; copy them anywhere. The hard
 * part is everything around them, and it is all here:
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
 *
 * THE CONVERSATION PART IS SMALLER THAN YOU'D EXPECT
 *
 * Keep the `thread_id` the server hands back, send it with the next question.
 * That's it. The history itself never comes near the browser — it's loaded from
 * Postgres and replayed to the model on the server, which is why a reload, or a
 * different device, can pick up the same thread.
 */

import { useCallback, useEffect, useRef, useState } from "react";

import {
  createRun,
  createRunNaive,
  HttpError,
  readRun,
  readThread,
  type Run,
  type RunStatus,
  type Step,
} from "./api";

/** Fast enough to feel live, slow enough not to hammer a free-tier server. */
const POLL_MS = 1500;

/** Survives a reload, which is the only reason the thread endpoint exists. */
const THREAD_KEY = "threadId";

export type ClientStatus = "idle" | RunStatus;

/** One exchange: what you asked, and everything that came back. */
export type Turn = {
  runId: string | null;
  question: string;
  status: ClientStatus;
  steps: Step[];
  result: string | null;
  error: string | null;
  provider: string | null;
  model: string | null;
  /** Frozen when the run settles, so it stops counting once it's done. */
  seconds: number | null;
};

function blankTurn(question: string): Turn {
  return {
    runId: null,
    question,
    status: "queued",
    steps: [],
    result: null,
    error: null,
    provider: null,
    model: null,
    seconds: null,
  };
}

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

  // A 4xx that isn't 404 means the server understood us and said no, in words.
  // Appending a list of guesses to a clear answer only muddies it.
  if (err instanceof HttpError && err.status >= 400 && err.status < 500) {
    if (err.status !== 404) return err.detail;
  }

  return (
    message +
    "\n\nCommon causes:\n" +
    "• Backend URL is wrong or the server isn't running\n" +
    "• Backend is cold-starting on a free tier — wait a minute and retry\n" +
    "• CORS: this page's origin isn't in ALLOWED_ORIGINS on the server\n" +
    "• Mixed content: an https page can't call an http backend"
  );
}

export function useConversation(baseUrl: string) {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [threadId, setThreadId] = useState<string | null>(() =>
    localStorage.getItem(THREAD_KEY),
  );
  const [elapsed, setElapsed] = useState(0);

  const abortRef = useRef<AbortController | null>(null);
  const last = turns[turns.length - 1];
  const busy = last?.status === "queued" || last?.status === "running";

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

  /**
   * Put the conversation back after a reload.
   *
   * Only when there's nothing on screen — never stomp on a live conversation,
   * and never fight the poll loop for the same state.
   */
  useEffect(() => {
    if (!threadId || !baseUrl || turns.length > 0) return;

    const controller = new AbortController();
    readThread(baseUrl, threadId, controller.signal)
      .then((runs) =>
        setTurns(
          runs.map((run) => ({
            runId: run.id,
            question: run.query,
            status: run.status,
            // The thread endpoint returns runs, not their steps. Old turns
            // therefore show their answer without the thinking that produced
            // it — the steps are still in the database, they're just not worth
            // one request each to redraw a conversation you've already read.
            steps: [],
            result: run.result,
            error: run.error,
            provider: run.provider,
            model: run.model,
            seconds: null,
          })),
        ),
      )
      // A thread id from a different backend, or one you've since deleted.
      // Nothing to recover and nothing worth alarming anyone about: drop it.
      .catch(() => {
        if (!controller.signal.aborted) {
          localStorage.removeItem(THREAD_KEY);
          setThreadId(null);
        }
      });

    return () => controller.abort();
    // Deliberately not depending on `turns`: this runs when the page loads or
    // the backend changes, not every time a step arrives.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [baseUrl, threadId]);

  const rememberThread = useCallback((id: string) => {
    localStorage.setItem(THREAD_KEY, id);
    setThreadId(id);
  }, []);

  /** Start over: new thread, empty screen. The old one stays in the database. */
  const reset = useCallback(() => {
    abortRef.current?.abort();
    localStorage.removeItem(THREAD_KEY);
    setThreadId(null);
    setTurns([]);
    setElapsed(0);
  }, []);

  const ask = useCallback(
    async (question: string, naive: boolean) => {
      // A second question cancels the first, in flight, mid-poll.
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      const { signal } = controller;

      const startedAt = Date.now();
      setElapsed(0);
      setTurns((current) => [...current, blankTurn(question)]);

      // Everything below writes to the turn we just added, and only that one.
      const patch = (fields: Partial<Turn>) =>
        setTurns((current) =>
          current.map((turn, index) =>
            index === current.length - 1 ? { ...turn, ...fields } : turn,
          ),
        );

      // Both paths end here, with whatever the run finally settled on.
      const finish = (run: Run) =>
        patch({
          status: run.status,
          result: run.status === "error" ? null : run.result,
          error: run.status === "error" ? (run.error ?? "The run failed.") : null,
          provider: run.provider,
          model: run.model,
          seconds: (Date.now() - startedAt) / 1000,
        });

      try {
        if (naive) {
          // One request. No progress is possible — there's nothing to poll,
          // because the answer and the work arrive together or not at all.
          patch({ status: "running" });
          const snapshot = await createRunNaive(
            baseUrl,
            question,
            threadId,
            signal,
          );
          rememberThread(snapshot.run.thread_id);
          patch({ runId: snapshot.run.id, steps: snapshot.steps });
          finish(snapshot.run);
          return;
        }

        // 1. Hand over the job. Back in ~200ms with an id.
        const created = await createRun(baseUrl, question, threadId, signal);
        rememberThread(created.thread_id);
        patch({ runId: created.run_id });

        // 2. Ask "done yet?" until it settles. Awaiting inside the loop means
        //    a slow poll delays the next one rather than overlapping with it.
        for (;;) {
          await sleep(POLL_MS, signal);
          const snapshot = await readRun(baseUrl, created.run_id, signal);

          patch({ status: snapshot.run.status, steps: snapshot.steps });

          if (snapshot.run.status === "done" || snapshot.run.status === "error") {
            finish(snapshot.run);
            return;
          }
        }
      } catch (err) {
        // We cancelled it ourselves — not a failure, and not worth a red box.
        if (signal.aborted) return;
        patch({
          status: "error",
          error: explain(err),
          seconds: (Date.now() - startedAt) / 1000,
        });
      }
    },
    [baseUrl, threadId, rememberThread],
  );

  return { turns, threadId, elapsed, busy, ask, reset };
}
