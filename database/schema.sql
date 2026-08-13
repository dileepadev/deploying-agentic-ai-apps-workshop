-- =============================================================================
--  Research Agent — database schema
--  Paste this whole file into the Supabase SQL Editor and hit Run.
--  Supabase dashboard -> your project -> SQL Editor -> New query
-- =============================================================================


-- -----------------------------------------------------------------------------
--  1. runs — one row per question a user asks
-- -----------------------------------------------------------------------------
-- This is the "job". The API creates it instantly and returns its id, then the
-- agent fills it in from a background task. The client polls this row until
-- status is 'done' or 'error'.

create table if not exists runs (
  id          uuid primary key default gen_random_uuid(),
  query       text not null,
  status      text not null default 'queued',   -- queued | running | done | error
  result      text,                             -- the final answer
  error       text,                             -- why it failed, if it failed
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);


-- -----------------------------------------------------------------------------
--  2. steps — the agent's thought process, one row per step
-- -----------------------------------------------------------------------------
-- This is what makes an agent *feel* alive. Every row here becomes a line in the
-- UI: "Agent is searching...", "Agent is reading 3 sources...".
--
-- It is also your debugger. When a run goes wrong in production you cannot
-- attach a breakpoint, but you can read exactly how far it got.

create table if not exists steps (
  id          bigserial primary key,
  run_id      uuid not null references runs(id) on delete cascade,
  seq         int  not null,                    -- 1, 2, 3... display order
  label       text not null,                    -- shown in the UI
  detail      text,                             -- extra info, shown when expanded
  created_at  timestamptz not null default now()
);

-- The client polls "give me the steps for this run, in order" a lot.
-- This index is what keeps that query fast.
create index if not exists steps_run_seq_idx on steps (run_id, seq);


-- -----------------------------------------------------------------------------
--  3. Row Level Security
-- -----------------------------------------------------------------------------
-- Supabase gives you two keys:
--
--   anon key          -- safe to ship in a browser. Restricted by RLS policies.
--   service_role key  -- BYPASSES RLS COMPLETELY. Server-side only. Never, ever
--                        put this in frontend code.
--
-- Our backend uses the service_role key, so it can do everything. Turning RLS on
-- means that if anyone gets hold of the public anon key, they still get nothing.
--
-- Default-deny: enable RLS and write no policies at all.

alter table runs  enable row level security;
alter table steps enable row level security;

-- Want the browser to read runs directly with the anon key instead of going
-- through your API? Then add a policy. Uncomment ONLY if you need it, and note
-- that this makes every run readable by anyone who knows its id:
--
-- create policy "anyone can read runs"  on runs  for select using (true);
-- create policy "anyone can read steps" on steps for select using (true);


-- -----------------------------------------------------------------------------
--  4. BONUS: long-term memory with pgvector
-- -----------------------------------------------------------------------------
-- Everything above is *working memory* — it belongs to one run and dies with it.
-- This table is *long-term memory*: it outlives the run.
--
-- Vector search means "find me things that MEAN something similar", instead of
-- "find me things that contain this exact word".

create extension if not exists vector;

create table if not exists memories (
  id          bigserial primary key,
  content     text not null,
  embedding   vector(768),                      -- <-- SEE THE WARNING BELOW
  created_at  timestamptz not null default now()
);

-- ⚠️  THE DIMENSION GOTCHA — the #1 thing that breaks pgvector projects.
--
-- That 768 must EXACTLY match the number of dimensions your embedding model
-- outputs. Different models output different sizes, and some let you configure
-- it. If they don't match you get an error at insert time, or worse, you build
-- your whole table on the wrong number and have to migrate it later.
--
-- Check your model's output dimensions FIRST, then write this line.

alter table memories enable row level security;

-- Similarity search looks like this (<=> is cosine distance, smaller = closer):
--
--   select content, 1 - (embedding <=> '[0.1, 0.2, ...]'::vector) as similarity
--   from memories
--   order by embedding <=> '[0.1, 0.2, ...]'::vector
--   limit 5;


-- -----------------------------------------------------------------------------
--  Done. Check the Table Editor — you should see: runs, steps, memories
-- -----------------------------------------------------------------------------
