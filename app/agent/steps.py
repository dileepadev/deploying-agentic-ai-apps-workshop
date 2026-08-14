"""Writing the agent's thought process to the database.

This one small class is what turns a mysterious 45-second wait into a UI that
says "Agent is searching…". Every row it writes becomes a line in the client.

It is also your production debugger. When a run goes wrong on a server you
cannot attach a breakpoint to, you can still read exactly how far it got.
"""

import config
import db


class StepLogger:
    """Writes the agent's steps to the database, in order.

    It also enforces a hard ceiling on steps. Without a ceiling, one confused
    agent can loop forever and burn your entire daily API quota before lunch.
    That ceiling is a guardrail, and it is the cheapest one you will ever write.
    """

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self.seq = 0

    async def log(self, label: str, detail: str | None = None) -> None:
        self.seq += 1
        if self.seq > config.MAX_AGENT_STEPS:
            raise RuntimeError(f"Agent exceeded {config.MAX_AGENT_STEPS} steps")
        await db.add_step(self.run_id, self.seq, label, detail)
