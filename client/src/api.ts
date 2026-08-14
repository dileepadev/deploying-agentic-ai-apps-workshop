/**
 * The entire backend contract, in one file.
 *
 * Five calls. That's the whole client:
 *
 *   1. GET  /health          -> which model is answering, and is the db up
 *   2. POST /runs            -> { run_id, thread_id }   back in ~200ms, always
 *   3. GET  /runs/{id}       -> { run, steps }          poll until it settles
 *   4. GET  /threads/{id}    -> { runs }                the conversation, after a reload
 *   5. POST /runs/naive      -> { run, steps }          the wrong way, kept to compare
 *
 * Note what is NOT here: any API key. The browser never holds one. It calls
 * your server, your server holds the Gemini, Supabase and Tavily keys. That is
 * the whole reason the backend exists as a separate thing.
 */

export type RunStatus = "queued" | "running" | "done" | "error";

/** A row from the `runs` table — one question and its answer. */
export type Run = {
  id: string;
  /** The conversation this run belongs to. Several runs share one. */
  thread_id: string;
  query: string;
  status: RunStatus;
  result: string | null;
  error: string | null;
  /** Who actually generated this answer — stamped by the server per run. */
  provider: string | null;
  model: string | null;
};

/** A row from the `steps` table — one line of the agent's thought process. */
export type Step = {
  seq: number;
  label: string;
  detail: string | null;
};

/** What both GET /runs/{id} and POST /runs/naive return. */
export type RunSnapshot = { run: Run; steps: Step[] };

/** What GET /health returns. Cheap, and it names the model on the other end. */
export type Health = {
  ok: boolean;
  database: boolean;
  provider: string;
  model: string;
  /** Whether a Tavily key is set — i.e. whether the agent can read the live web. */
  web_search: boolean;
};

/** Trailing slashes on a pasted URL produce `//runs`, which some hosts 404. */
export function normaliseBaseUrl(url: string): string {
  return url.trim().replace(/\/+$/, "");
}

/**
 * A failed response, with the status kept rather than flattened into a string.
 *
 * Worth the extra class: some 4xx replies are the server telling you exactly
 * what's wrong ("this conversation is too long"), and pasting a generic
 * troubleshooting list underneath one of those actively unhelps.
 */
export class HttpError extends Error {
  constructor(
    readonly status: number,
    readonly detail: string,
  ) {
    super(`HTTP ${status} — ${detail}`);
  }
}

/** Turn a failed response into a message worth showing a human. */
async function describe(response: Response): Promise<HttpError> {
  const body = await response.text().catch(() => "");
  // FastAPI puts its message in `detail`; anything else we show raw.
  let detail = body.slice(0, 300);
  try {
    detail = (JSON.parse(body) as { detail?: string }).detail ?? detail;
  } catch {
    // Not JSON — a proxy's HTML error page, most likely. Show it as-is.
  }
  return new HttpError(response.status, detail);
}

/**
 * Is the backend awake, and what is it running?
 *
 * Called as you type a backend URL. Doubles as the wake-up call for a free-tier
 * service that has gone to sleep, which is why it's the first thing the page does.
 */
export async function fetchHealth(
  baseUrl: string,
  signal: AbortSignal,
): Promise<Health> {
  const response = await fetch(`${baseUrl}/health`, { signal });
  if (!response.ok) throw await describe(response);
  return (await response.json()) as Health;
}

/**
 * The right way, part 1: hand over the job and get out of the way.
 *
 * Returns a run id immediately. The agent has not started working yet — that
 * happens in a background task, after this response has already been sent.
 *
 * `threadId` is what makes this a conversation instead of a series of unrelated
 * questions. Send back the one you were given and the agent picks up where it
 * left off; send nothing and the server starts a fresh thread.
 */
export async function createRun(
  baseUrl: string,
  query: string,
  threadId: string | null,
  signal: AbortSignal,
): Promise<{ run_id: string; thread_id: string }> {
  const response = await fetch(`${baseUrl}/runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, thread_id: threadId }),
    signal,
  });
  if (!response.ok) throw await describe(response);
  return (await response.json()) as { run_id: string; thread_id: string };
}

/**
 * The right way, part 2: ask "done yet?".
 *
 * Every call returns the steps written *so far*, which is what turns a blank
 * 45-second wait into "Agent is searching…".
 */
export async function readRun(
  baseUrl: string,
  runId: string,
  signal: AbortSignal,
): Promise<RunSnapshot> {
  const response = await fetch(`${baseUrl}/runs/${runId}`, { signal });
  if (!response.ok) throw await describe(response);
  return (await response.json()) as RunSnapshot;
}

/**
 * The conversation, read back from the database.
 *
 * This is what makes a reload not lose your chat. Nothing was ever really in
 * the browser: the thread lives in Postgres, and this page is only ever showing
 * you a copy of it.
 */
export async function readThread(
  baseUrl: string,
  threadId: string,
  signal: AbortSignal,
): Promise<Run[]> {
  const response = await fetch(`${baseUrl}/threads/${threadId}`, { signal });
  if (!response.ok) throw await describe(response);
  return ((await response.json()) as { runs: Run[] }).runs;
}

/**
 * The wrong way: one request, hold the line, hope for the best.
 *
 * Kept on purpose. This is the version everyone writes first, and it works
 * perfectly on localhost — which is exactly why it survives to production,
 * where a proxy times out at 30 seconds and the user gets a 504.
 */
export async function createRunNaive(
  baseUrl: string,
  query: string,
  threadId: string | null,
  signal: AbortSignal,
): Promise<RunSnapshot> {
  const response = await fetch(`${baseUrl}/runs/naive`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, thread_id: threadId }),
    signal,
  });
  if (!response.ok) throw await describe(response);
  return (await response.json()) as RunSnapshot;
}
