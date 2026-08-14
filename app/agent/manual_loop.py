"""The same agent, written by hand. No framework.

This file is here to be READ, not to be used in production. `research.py` is
what actually runs.

Why keep it? Because a framework hides the loop, and the loop is the thing you
need to see once. Everything Pydantic AI does for us in `research.py` is done
explicitly here, in about eighty lines, with nothing you can't step through in a
debugger.

    plan  ->  search  ->  read  ->  write  ->  save

THE HONEST DIFFERENCE

This version is a *pipeline*. We wrote the order down; the model only fills in
the blanks. Ask it something that needs a follow-up search and it can't do one,
because we never gave it the chance — the shape of the work was decided by us,
in advance.

`research.py` hands the model the same two tools and lets it decide. That is the
line between "a script that calls an LLM" and "an agent": who owns the control
flow. Everything else — the deployment problem this whole workshop is about — is
identical either way, which is exactly why the deployment lesson outlives your
choice of framework.

Run it on its own (from app/):

    uv run python -m agent.manual_loop "how do solar panels work?"
"""

import asyncio
import sys

import llm
from tools import wikipedia

PLANNER_SYSTEM = """You are a research planner.
Given a user's question, break it into 2-3 short search queries that together
would answer it. Prefer specific, factual queries over broad ones.

Reply with JSON only, in exactly this shape:
{"searches": ["query one", "query two"]}"""

WRITER_SYSTEM = """You are a careful research assistant.
Answer the user's question using ONLY the sources provided. Write 3-5 short
paragraphs in plain language a first-year university student would understand.

If the sources don't actually answer the question, say so plainly instead of
guessing. End with a "Sources:" list of the titles you used."""


async def run(query: str, log=print) -> str:
    """Research a question and return the answer. Every phase is explicit."""

    # --- 1. Plan -------------------------------------------------------------
    # We ask the model what to search for, but WE decide that searching is the
    # next thing that happens. That's the pipeline showing through.
    log("Planning the research")
    plan = await llm.generate_json(f"Question: {query}", system=PLANNER_SYSTEM)
    searches = [str(s) for s in plan.get("searches", [])][:3]
    if not searches:
        searches = [query]  # planner gave us nothing useful — fall back

    # --- 2. Search -----------------------------------------------------------
    titles: list[str] = []
    for search_query in searches:
        log(f'Searching for: "{search_query}"')
        for title in await wikipedia.search(search_query, limit=2):
            if title not in titles:
                titles.append(title)

    if not titles:
        raise RuntimeError("No sources found for that question. Try rephrasing it.")

    # --- 3. Read -------------------------------------------------------------
    log(f"Reading {len(titles)} sources")
    sources = []
    for title in titles[:5]:
        page = await wikipedia.read_page(title)
        if page:
            sources.append(page)

    if not sources:
        raise RuntimeError("Found sources but couldn't read any of them.")

    # --- 4. Write ------------------------------------------------------------
    log(f"Writing the answer from {len(sources)} sources")
    context = "\n\n".join(
        f"### {s['title']}\n{s['extract']}\n({s['url']})" for s in sources
    )
    return await llm.generate(
        f"Question: {query}\n\nSources:\n{context}",
        system=WRITER_SYSTEM,
    )


async def _main() -> None:
    question = " ".join(sys.argv[1:]) or "How do solar panels actually work?"
    print(f"\n  Question: {question}\n")
    answer = await run(question, log=lambda m: print(f"  · {m}"))
    print(f"\n{answer}\n")
    await llm.close()
    await wikipedia.close()


if __name__ == "__main__":
    asyncio.run(_main())
