## Memory (mimi)

Check this before grepping the repo. Everything mimi keeps is in `mimi/`, and the current state loads automatically:

@STATE.md

### Where to look
- Something broke, or a symptom looks familiar → `mimi/ISSUES.md` (search the exact error text)
- About to change an existing choice (library, schema, provider, architecture) → `mimi/decisions.md` — contains: DEC-AS-1 — mimi/ is committed, not git-ignored; DEC-AS-2 — AGENTS.md is the single rulebook; CLAUDE.md only imports it; DEC-AS-3 — Merges gated by CI + Claude review, 0 human approvals; DEC-AS-4 — Members run mimi close themselves; DEC-HG-1 — Data Engineering public interface and player-GW schema; DEC-JD-1 — PROPOSED — pending consumer sign-off: prediction API and uncertainty output; DEC-AS-5 — PRs auto-merge; nobody merges by hand; DEC-AS-6 — Session state is per person; mimi/STATE.md is team-level; DEC-AS-7 — Agents identify the user via `gh`, then follow teammates/<user>.md; DEC-AS-8 — Anyone may edit mimi/STATE.md; DEC-TA-1 — PROPOSED: backtest simulator interface
- Touching an external system (API, database, deploy, credentials) → `mimi/memory/external.md` — contains: Why can't I push to main or merge my PR (branch protection); PR stuck with no reminder (failed checks); Claude PR review: whose credentials, what it costs; gh pr checks: "no checks reported" after a push; Collaborators and GitHub usernames

Every file in `mimi/memory/` gets one line above saying when to read it. A file with no line is never read. `index` appends each file's `##` headings to its line, so a task can match a trap by name, and marks a file that holds nothing yet as `— empty`: skip those.

Memory holds only what someone wrote down. When it has nothing on the question, that is not an answer: search `git log --grep`, the issue tracker and the code before concluding.

### What to write, and where
- Bug fixed → append to `mimi/ISSUES.md`: exact symptom text, cause, fix commit, test.
- Choice someone could argue again → append to `mimi/decisions.md`: why, what was rejected, what would reverse it.
- Fact the code cannot tell you → `mimi/memory/<topic>.md`: external-system quirks, measured numbers with date and sample size, why something non-obvious exists, environment traps. Give each trap its own `##` heading, named the way a task would describe it (error text, library, table, command). Keep one `Last verified:` line per file, dated when its facts were last checked.
- End of a work session → overwrite your own `mimi/state/<github-username>.md` (or run the `mimi-close` skill, writing to that file instead of `mimi/STATE.md`). Finished work leaves it. `mimi/STATE.md` is team-level; anyone may edit it for team-level facts.
- Code change alone → nothing. Git has it.
- After any memory edit: run `python "<mimi skill folder>/memlayer.py" index .`, then `python "<mimi skill folder>/memlayer.py" check .` and fix what it prints until it says clean.

Before writing any line: could someone learn this in under a minute from the code or a command? If yes, do not write it. Ask it of each fact on its own, not of the message the fact came in: a number, date, measurement, deadline, decision or constraint that a person stated is never in the code, even when the code touches the same topic, and a fact about the user's own systems, team or downstream use of this code is kept even when this repository never touches it. Every fact needs something checkable behind it: a commit, an issue ID, a command, a date. A wrong line gets fixed or deleted, never a correct one added beside it. Split `mimi/memory/` by external boundary or subsystem, not by code folder, and only after a real miss.

`mimi/` is committed and shared by the whole team through git. Never add it to any `.gitignore`. Pull before reading it; commit memory edits together with the code they describe.

Find rot: `python "<mimi skill folder>/memlayer.py" check .` — the mimi skill folder is the first that exists of `~/.claude/skills/mimi`, `~/.agents/skills/mimi`, `~/.config/opencode/skills/mimi`, `~/.codex/skills/mimi`.
