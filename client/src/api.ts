/**
 * The entire backend contract, in one file.
 *
 * Three calls. That's the whole client:
 *
 *   1. POST /runs        -> { run_id }        comes back in ~200ms, always
 *   2. GET  /runs/{id}   -> { run, steps }    poll this until status settles
 *   3. POST /runs/naive  -> { run, steps }    the wrong way, kept to compare
 *
 * Note what is NOT here: any API key. The browser never holds one. It calls
 * your server, your server holds the Gemini and Supabase keys. That is the
 * whole reason the backend exists as a separate thing.
 */

export type RunStatus = "queued" | "running" | "done" | "error";

/** A row from the `runs` table — the job. */
export type Run = {
  id: string;
  query: string;
  status: RunStatus;
  result: string | null;
  error: string | null;
};

/** A row from the `steps` table — one line of the agent's thought process. */
export type Step = {
  seq: number;
  label: string;
  detail: string | null;
};

/** What both GET /runs/{id} and POST /runs/naive return. */
export type RunSnapshot = { run: Run; steps: Step[] };

/** Trailing slashes on a pasted URL produce `//runs`, which some hosts 404. */
export function normaliseBaseUrl(url: string): string {
  return url.trim().replace(/\/+$/, "");
}

/** Turn a failed response into a message worth showing a human. */
async function describe(response: Response): Promise<Error> {
  const body = await response.text().catch(() => "");
  return new Error(`HTTP ${response.status} — ${body.slice(0, 300)}`);
}

/**
 * The right way, part 1: hand over the job and get out of the way.
 *
 * Returns a run id immediately. The agent has not started working yet — that
 * happens in a background task, after this response has already been sent.
 */
export async function createRun(
  baseUrl: string,
  query: string,
  signal: AbortSignal,
): Promise<string> {
  const response = await fetch(`${baseUrl}/runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
    signal,
  });
  if (!response.ok) throw await describe(response);
  const { run_id } = (await response.json()) as { run_id: string };
  return run_id;
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
 * The wrong way: one request, hold the line, hope for the best.
 *
 * Kept on purpose. This is the version everyone writes first, and it works
 * perfectly on localhost — which is exactly why it survives to production,
 * where a proxy times out at 30 seconds and the user gets a 504.
 */
export async function createRunNaive(
  baseUrl: string,
  query: string,
  signal: AbortSignal,
): Promise<RunSnapshot> {
  const response = await fetch(`${baseUrl}/runs/naive`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
    signal,
  });
  if (!response.ok) throw await describe(response);
  return (await response.json()) as RunSnapshot;
}
