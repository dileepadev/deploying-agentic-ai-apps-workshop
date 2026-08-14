# app/http/ — poking the API by hand

Ready-made HTTP requests for the deployed and local API, so you can drive the
agent without writing a client or leaving the editor.

| File | What it covers |
| --- | --- |
| [api.http](api.http) | The REST API — health, the accept-and-poll flow, follow-up questions and threads, the naive endpoint, the guardrails |
| [mcp.http](mcp.http) | The MCP server at `/mcp` — handshake, `tools/list`, calling each tool |

These are **not** the test suite. `uv run --extra dev pytest` is the test suite,
it runs offline, and it's what has to pass before a change is done. These files
need a server that's actually running, and `mcp.http` reaches real Wikipedia.

## Running them

Install the [REST Client](https://marketplace.visualstudio.com/items?itemName=humao.REST-Client)
extension for VS Code, open either file, and click the **Send Request** link
that appears above each block. JetBrains IDEs read the same `.http` format with
their built-in HTTP client, though the `{{name.response...}}` chaining below is
REST Client syntax.

Start the API first, from `app/`:

```bash
uv run fastapi dev main.py
```

## Pointing at your deployed service

Every file opens with two lines. Comment out the first, uncomment the second,
and fill in your URL:

```http
@baseUrl = http://localhost:8000
# @baseUrl = https://your-service.onrender.com
```

Same requests, deployed target. This is the fastest way to prove a deploy
actually works — and to demonstrate the 504 that `POST /runs/naive` earns once
there's a proxy in front of it, which never reproduces on localhost.

## Two things that trip people up

**The polling request reuses the previous response.** In `api.http`, `POST /runs`
is named `createRun`, and the request under it reads
`{{createRun.response.body.$.run_id}}`. Send the POST once, then keep sending
the GET — no ids to copy. Send them out of order and the id is empty.

**MCP is stateful and streams.** `initialize` returns an `mcp-session-id`
header that every later call has to echo back, so `mcp.http` has to run top to
bottom. Responses arrive as Server-Sent Events (`event: message` / `data: {…}`),
not bare JSON — that's the protocol working, not a bug.
