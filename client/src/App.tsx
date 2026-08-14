import { useEffect, useState } from "react";

import { normaliseBaseUrl } from "./api";
import { Steps } from "./Steps";
import { useRun } from "./useRun";

/**
 * Where the backend lives.
 *
 * The build-time default comes from VITE_API_URL (see .env.example). The
 * on-screen field overrides it and is remembered in this browser — that field
 * exists because in the workshop everyone deploys their own backend and needs
 * to point this at their own Render URL without rebuilding.
 *
 * A backend URL is public by nature. Keys are not, and none are read here.
 */
const DEFAULT_API_URL =
  import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export default function App() {
  const [backendUrl, setBackendUrl] = useState(
    () => localStorage.getItem("backendUrl") ?? DEFAULT_API_URL,
  );
  const [query, setQuery] = useState("How do solar panels actually work?");
  const [naive, setNaive] = useState(false);

  useEffect(() => {
    localStorage.setItem("backendUrl", backendUrl.trim());
  }, [backendUrl]);

  const { status, steps, result, error, elapsed, busy, ask } = useRun(
    normaliseBaseUrl(backendUrl),
  );

  const started = status !== "idle";

  return (
    <main>
      <h1>Research Agent</h1>
      <p className="sub">
        A deliberately slow AI agent — and a UI that tells you what it's doing
        while you wait. Workshop demo.
      </p>

      <section className="panel">
        <label htmlFor="backend">Backend URL</label>
        <input
          id="backend"
          type="url"
          placeholder="http://localhost:8000"
          value={backendUrl}
          onChange={(event) => setBackendUrl(event.target.value)}
        />
        <p className="hint">
          Your own deployed API. Local: <code>http://localhost:8000</code>.
          Deployed: your Render URL. Saved in this browser.
        </p>
      </section>

      <form
        className="panel"
        onSubmit={(event) => {
          event.preventDefault();
          if (query.trim().length < 3) return;
          void ask(query.trim(), naive);
        }}
      >
        <div className="row">
          <div>
            <label htmlFor="query">Your question</label>
            <input
              id="query"
              type="text"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </div>
          <button type="submit" disabled={busy}>
            Ask the agent
          </button>
        </div>

        <label className="naive">
          <input
            type="checkbox"
            checked={naive}
            onChange={(event) => setNaive(event.target.checked)}
          />
          Naive mode — run the agent inside the request (this is the bug)
        </label>
      </form>

      {started && (
        <section className="panel">
          <div className="statusbar">
            <span>
              <span className={`pill ${status}`}>{status}</span>
            </span>
            <span>{elapsed.toFixed(1)}s</span>
          </div>

          {naive && busy ? (
            <ol className="steps">
              <li className="active">
                <div className="step-label">Waiting for the server…</div>
                <div className="step-detail">
                  No progress updates are possible — the request hasn't come
                  back yet. This is exactly what your users see.
                </div>
              </li>
            </ol>
          ) : (
            <Steps steps={steps} status={status} />
          )}
        </section>
      )}

      {result && (
        <section className="panel">
          <label>Answer</label>
          <div className="result">{result}</div>
        </section>
      )}

      {error && (
        <section>
          <div className="error-box">{error}</div>
        </section>
      )}

      <footer>
        Source:{" "}
        <a href="https://github.com/dileepadev/deploying-agentic-ai-apps-workshop">
          github.com/dileepadev/deploying-agentic-ai-apps-workshop
        </a>
      </footer>
    </main>
  );
}
