import type { Step } from "./api";
import type { ClientStatus } from "./useConversation";

/**
 * The agent's thought process, one line per row in the `steps` table.
 *
 * The last step spins while the run is still going — that is the entire trick
 * behind the "Agent is searching…" feel. There is no streaming and no
 * websocket here; it's just the newest row we've seen, marked as in-progress.
 *
 * Note there's no HTML-escaping code anywhere: React escapes `{step.label}`
 * for us. The hand-written version of this client needed its own escapeHtml()
 * helper, because it built rows with innerHTML.
 */
export function Steps({
  steps,
  status,
}: {
  steps: Step[];
  status: ClientStatus;
}) {
  return (
    <ol className="steps">
      {steps.map((step, index) => {
        const isLast = index === steps.length - 1;
        let className = "";
        if (isLast && status === "running") className = "active";
        if (isLast && status === "error") className = "failed";

        return (
          <li key={step.seq} className={className}>
            <div className="step-label">{step.label}</div>
            {step.detail && <div className="step-detail">{step.detail}</div>}
          </li>
        );
      })}
    </ol>
  );
}
