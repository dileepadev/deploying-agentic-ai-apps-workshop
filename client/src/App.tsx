import { useEffect, useState } from "react";

import { normaliseBaseUrl } from "./api";
import { Turn } from "./Turn";
import { useConversation } from "./useConversation";
import { useHealth } from "./useHealth";

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
const DEFAULT_API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export default function App() {
  const [backendUrl, setBackendUrl] = useState(
    () => localStorage.getItem("backendUrl") ?? DEFAULT_API_URL,
  );
  const [query, setQuery] = useState("How do solar panels actually work?");
  const [naive, setNaive] = useState(false);

  useEffect(() => {
    localStorage.setItem("backendUrl", backendUrl.trim());
  }, [backendUrl]);

  const baseUrl = normaliseBaseUrl(backendUrl);
  const { health, checking } = useHealth(baseUrl);
  const { turns, elapsed, busy, ask, reset } = useConversation(baseUrl);

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    if (query.trim().length < 3) return;
    void ask(query.trim(), naive);
    setQuery("");
  };

  return (
    <main>
      <h1>Research Agent</h1>
      <p className="sub">
        A deliberately slow AI agent — and a UI that tells you what it's doing
        while you wait. Ask a question, then ask a follow-up. Workshop demo.
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

        {/* Who is on the other end of that URL. One /health call answers it,
            and answers it again the moment you point somewhere else. */}
        <p className="conn">
          {checking && <span className="dot waiting" />}
          {checking && "checking…"}

          {!checking && !health && (
            <>
              <span className="dot down" />
              unreachable, retrying — cold start, or is this page's origin in
              ALLOWED_ORIGINS?
            </>
          )}

          {!checking && health && (
            <>
              <span className={`dot ${health.database ? "up" : "down"}`} />
              <strong>{health.provider}</strong> · {health.model}
              {" · "}
              {health.database ? "database ok" : "database unreachable"}
              {" · "}
              {health.web_search ? "web search on" : "wikipedia only"}
            </>
          )}
        </p>

        <p className="hint">
          Your own deployed API. Local: <code>http://localhost:8000</code>.
          Deployed: your Render URL. Saved in this browser.
        </p>
      </section>

      {turns.length > 0 && (
        <section className="panel conversation">
          {turns.map((turn, index) => (
            <Turn
              key={turn.runId ?? `pending-${index}`}
              turn={turn}
              elapsed={elapsed}
              naiveWait={naive && busy && index === turns.length - 1}
            />
          ))}
        </section>
      )}

      <form className="panel" onSubmit={submit}>
        <div className="row">
          <div>
            <label htmlFor="query">
              {turns.length === 0 ? "Your question" : "Follow-up"}
            </label>
            <input
              id="query"
              type="text"
              value={query}
              placeholder={
                turns.length === 0
                  ? "How do solar panels actually work?"
                  : "Why is that? · Which of those is cheapest? · Any news this week?"
              }
              onChange={(event) => setQuery(event.target.value)}
            />
          </div>
          <button type="submit" disabled={busy}>
            {turns.length === 0 ? "Ask the agent" : "Send"}
          </button>
          {turns.length > 0 && (
            <button
              type="button"
              className="secondary"
              onClick={reset}
              disabled={busy}
            >
              New conversation
            </button>
          )}
        </div>

        <label className="naive">
          <input
            type="checkbox"
            checked={naive}
            onChange={(event) => setNaive(event.target.checked)}
          />
          Naive mode — run the agent inside the request (this is the bug)
        </label>

        {turns.length > 0 && (
          <p className="hint">
            The agent remembers this conversation — the history lives in your
            database, not in this tab. Reload the page and it's still here.
          </p>
        )}
      </form>

      <footer>
        Source:{" "}
        <a href="https://github.com/dileepadev/deploying-agentic-ai-apps-workshop">
          github.com/dileepadev/deploying-agentic-ai-apps-workshop
        </a>
      </footer>
    </main>
  );
}
