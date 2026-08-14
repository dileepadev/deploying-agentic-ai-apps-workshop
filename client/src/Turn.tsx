import { Steps } from "./Steps";
import type { Turn as TurnData } from "./useConversation";

/**
 * One exchange: the question you asked, and everything that came back.
 *
 * The footer line under a finished answer names the provider and model that
 * produced it. It's stamped per run rather than read from /health, so an answer
 * still tells the truth about itself after you've switched keys — which, on a
 * free tier, you will.
 */
export function Turn({
  turn,
  elapsed,
  naiveWait,
}: {
  turn: TurnData;
  /** The live clock, for the run that's still going. */
  elapsed: number;
  /** Naive mode, mid-request: there is nothing to poll and nothing to show. */
  naiveWait: boolean;
}) {
  const running = turn.status === "queued" || turn.status === "running";
  const seconds = turn.seconds ?? (running ? elapsed : null);

  return (
    <article className="turn">
      <p className="question">{turn.question}</p>

      <div className="answer">
        <div className="statusbar">
          <span className={`pill ${turn.status}`}>{turn.status}</span>
          {seconds !== null && <span>{seconds.toFixed(1)}s</span>}
        </div>

        {naiveWait ? (
          <ol className="steps">
            <li className="active">
              <div className="step-label">Waiting for the server…</div>
              <div className="step-detail">
                No progress updates are possible — the request hasn't come back
                yet. This is exactly what your users see.
              </div>
            </li>
          </ol>
        ) : (
          <Steps steps={turn.steps} status={turn.status} />
        )}

        {turn.result && <div className="result">{turn.result}</div>}
        {turn.error && <div className="error-box">{turn.error}</div>}

        {turn.provider && (
          <p className="meta">
            {turn.provider} · {turn.model}
            {turn.steps.length > 0 && ` · ${turn.steps.length} steps`}
          </p>
        )}
      </div>
    </article>
  );
}
