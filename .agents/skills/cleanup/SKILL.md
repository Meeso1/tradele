---
name: cleanup
description: Cleans up recently-written Tradele backend code (the last commit(s) plus any uncommitted changes) - resolving TODO(cleanup) markers and small missing-implementation TODOs, syncing repositories/SQL/migrations with model changes, updating tests, and fixing obvious bugs. Use when the user asks to "clean up", "review", or "polish" recent changes.
---

# Cleaning up recent Tradele changes

Use this after a prototyping/pairing session where code was written quickly (stubs,
half-wired features, renamed fields left unpropagated, etc.) and the user wants it brought up
to the codebase's normal standard before moving on. Scope the cleanup to what actually
changed recently - don't go rewrite unrelated parts of the codebase.

## 1. Figure out the scope

- Look at the last commit(s) the user points to (`git show`/`git log --stat`) plus any
  uncommitted changes (`git status`, `git diff`). If unclear how many commits are in scope, ask.
- Read every file touched, not just the diff hunks - half-finished work often leaves neighboring
  code (callers, tests, DTOs, schemas) out of sync even though it wasn't touched in the diff.

## 2. Resolve TODOs

TODOs in this codebase come in two flavors:

- **`TODO(cleanup): ...`** - a marker deliberately left for this pass. Always resolve these as
  part of cleanup. If a `TODO(cleanup)` describes something too large/ambiguous to safely
  implement, say so explicitly instead of silently skipping it.
- **Plain `TODO: ...`** - backlog/future work, not necessarily in scope. Only resolve a plain
  TODO during cleanup if it's small and mechanical (a missing method, an unimplemented stub like
  `...`/`pass`, a comparison/helper that's clearly required for the surrounding code to work).
  Leave larger-scoped or intentionally-deferred TODOs alone (e.g. "replace mock data with a real
  API", "support a configurable X") unless the user explicitly asks for them, and don't remove
  the TODO just to silence it.
- If you introduce a new piece of deliberately-deferred work while cleaning up, mark it
  `TODO(cleanup)` if you want a future cleanup pass to pick it up automatically, or a plain
  `TODO` if it's genuine backlog.
- Never touch TODOs about moving domain objects into a shared `models` location unless asked -
  this is a known, deliberately-deferred restructuring in this codebase.

## 3. Sync repositories, SQL, and migrations with model changes

Quick prototyping often changes a Pydantic model's fields without updating the repository that
persists it. For every repository touched (or touching a model that changed):

- Compare each model's fields against the SQL the repository sends/reads (column names, and
  whether every field is actually covered). Watch for silent mismatches like a rename that only
  updated one side (e.g. model field renamed `side` -> `kind` but the `INSERT`/`SELECT` still say
  `side`), or a nested/non-scalar field (e.g. a compound value like an hour+day pair) that a raw
  `Model(**dict(row))` can't reconstruct - these need explicit row-to-model mapping instead.
- If the schema itself needs to change (new/renamed/removed columns, tables), follow the
  `database-migrations` skill to add a new migration. Don't hand-edit a migration that's already
  been pushed/shared; if it was only added earlier in the same not-yet-pushed change, it's fine
  to edit in place instead of stacking another migration on top of it.
- Re-check query correctness, not just shape: filters that should account for edge cases (e.g.
  day/hour boundaries), missing indexes/ordering implied by a docstring, etc.

## 4. Update tests

- The user will very likely say they haven't updated tests themselves except for mechanical
  renames - meaning any semantic drift between tests and the cleaned-up code needs to be fixed
  by you, not merely field-renamed.
- Update tests to use the current model/repository/service shape (constructor fields, method
  signatures, valid enum/literal values, newly-required fields, etc.).
- Add tests for any behavior you implemented while resolving TODOs (new methods, new services,
  bug fixes) rather than only patching existing ones.
- Run the project's test command and lint (see the repo's `AGENTS.md`) after every meaningful
  batch of changes, not just once at the end - fix regressions before moving on.

## 5. Look for obvious bugs

While reading through the touched files and their neighbors, watch specifically for:

- Fields/params referenced that don't exist on the type being used (common after a rename that
  wasn't fully propagated).
- Return-type mismatches between a service/repository and its caller (e.g. a method that used to
  return a flat `dict` now returns a richer object, but a router/DTO downstream still assumes the
  old shape).
- Off-by-one/boundary bugs in date or hour arithmetic (this codebase deals with hourly windows
  and daily submissions a lot - midnight/day-rollover edge cases are a recurring source of bugs).
- Missing comparison/ordering support on small value types (e.g. a dataclass compared with `<`/
  `>=` that never opted into ordering).
- Dead code that only existed to serve something now-removed (e.g. a helper only used by a
  method you just deleted).

## 6. Keep changes minimal and consistent

- Follow the conventions already documented in the repo's `AGENTS.md` and other skills (e.g.
  `database-migrations`) rather than introducing new patterns.
- Don't refactor unrelated code "while you're in there" - stay scoped to what the recent
  commit(s)/uncommitted changes touched, plus what's needed to make that work correctly and
  consistently with the rest of the codebase.
- Summarize, at the end, what was cleaned up, which TODOs were resolved vs. intentionally left,
  and what validation (tests/lint) was run.
