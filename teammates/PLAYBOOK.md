# Teammate playbook — exact steps for every session

Shared procedure for every teammate. Your own file (`teammates/<github-username>.md`) adds what you own and what to watch for. `AGENTS.md` stays the binding rulebook; this file is the step-by-step version of it. Run the commands in order. Do not improvise around a step.

## The three rules that stop almost every conflict
1. **One topic = one branch = one PR. Never close a PR to "start fresh".** A blocked, red, or conflicting PR is fixed by pushing more commits to the same branch. Closing it and opening a new one throws away the review history and brings the same conflicts back.
2. **After your PR merges, that branch is dead.** PRs are squash-merged, so the old branch no longer matches `main`. Delete it and start the next topic from a fresh `main` (step E). Never keep committing on a merged branch.
3. **Merge `main` into your branch often** (at session start, before opening the PR, and whenever GitHub says the branch is out of date). Small, frequent merges are easy. One big merge at the end is where conflicts come from.

## A. Session start
```bash
gh api user --jq .login           # who you are; must match your teammates/<name>.md
git status --short                # uncommitted changes you did not make → stop, ask the user
git fetch origin
gh pr list --author @me --state open
```
- **You already have an open PR** → continue on that PR's branch. Do not create a new branch or a new PR:
  ```bash
  git checkout <that-branch>
  git pull --ff-only
  git merge origin/main             # conflicts → section D
  ```
- **No open PR** → start a new topic from fresh `main`:
  ```bash
  git checkout main
  git pull --ff-only
  git checkout -b <github-username>/<topic>
  ```
- Then: `uv sync`, and read `mimi/MIMI.md` and `mimi/STATE.md`.

## B. While working
- Touch only the paths listed in your own teammates file plus the shared files (`mimi/`, `pyproject.toml`, `uv.lock`, your own notebooks). Before every commit, run `git status --short` and check every path against that list. A path you do not own → unstage it (`git restore --staged <path>`), revert it (`git restore <path>`), and tell the user who owns it.
- Name new tests `tests/test_<your-module>_<topic>.py`. Any other name is owned by `CandyButcher27`, and CI fails your PR.
- Commit small: `uv run pytest`, then `git add <file> <file>` by name, then `git commit -m "feat: ..."`.
- Push early: `git push -u origin HEAD` the first time, `git push` after that.
- `mimi/STATE.md`: edit only your own lines. Never rewrite, reformat, or delete another person's line. Copy text exactly; do not retype it (PR #9 corrupted a teammate's line this way).

## C. Opening the PR — only if `gh pr list --author @me --state open` shows none for this branch
```bash
git fetch origin && git merge origin/main      # conflicts → section D
uv run pytest                                  # must pass locally first
git push
gh pr create --base main --title "feat: <what>" --body "<what changed, why, how it was tested>"
gh pr merge --auto --squash
gh pr checks --watch
```
If `gh pr create` says a PR already exists for this branch, that is fine: `git push` already updated it. Do not create another one.

## D. "This branch has conflicts" / "out of date with main"
Fix it on the same branch. Never close the PR.
```bash
git fetch origin
git merge origin/main
git status --short                 # lines starting with UU are conflicted files
```
Resolve each conflicted file:
- **Your own file** → open it, keep both sides' intent, remove every `<<<<<<<`, `=======`, `>>>>>>>` marker.
- **`uv.lock`** → `git checkout --theirs uv.lock && uv lock`
- **`mimi/STATE.md`** → keep both sides. Keep every other person's lines from `main` exactly as they are, keep your own lines, and write your own `Last session` block.
- **`mimi/ISSUES.md`, `mimi/decisions.md`** → keep both sides' entries.
- **A file someone else owns** → stop. Do not pick a side. Tell the user who owns it.

Then:
```bash
grep -rn '^<<<<<<<\|^>>>>>>>' --include='*.py' --include='*.md' --include='*.toml' .   # must print nothing
uv run pytest
git add <each resolved file>
git commit --no-edit
git push
```
If GitHub only says "out of date" (no conflicts), `gh pr update-branch` also works. Pull afterwards: `git pull --ff-only`.

## E. After your PR merges
```bash
git checkout main
git pull --ff-only
git branch -D <old-branch>
git checkout -b <github-username>/<next-topic>
```
The remote branch is deleted automatically on merge. Pushing the old local branch again recreates it with stale history; do not do that.

## F. `ci` check failed
```bash
gh pr checks
gh run view --log-failed
```
Find the failing step in the log and fix it on the same branch:
- **`uv sync --locked` failed** → `pyproject.toml` and `uv.lock` disagree. Run `uv lock`, commit `uv.lock`, push. Never add packages with `pip`.
- **`uv run pytest` failed** → run `uv run pytest` locally, fix the code until it passes, push. Never delete, skip, or weaken a test. If the failing test belongs to someone else and fails because of your change, your change is wrong or needs an interface agreement (`AGENTS.md` section 4). If it fails on `main` too, tell the user to tell its owner.
- **"PR only touches paths its author owns" failed** → the log prints `<path>: owned by <owner>, not <you>`. Undo that path on your branch: `git checkout origin/main -- <path>` (or `git rm <path>` if the file is new), commit, push. Then tell the user what change to ask `<owner>` for.
- **"mimi memory is not git-ignored" failed** → `git rm mimi/.gitignore`, also delete `mimi/.ignore` if present, commit, push.

## G. `review` check failed (`**Review: BLOCK**`)
```bash
gh pr view --comments
```
Read the newest comment starting `**Review: BLOCK**` and the inline comments. Fix every blocking item on the same branch, add the tests it asks for, `uv run pytest`, push. The review re-runs on every push. Suggestions (not blocking) are optional. If you think a block is wrong, tell the user; do not close and reopen the PR to get a new review.

## H. Waiting for merge
`gh pr checks --watch`. When both checks are green and auto-merge is armed, GitHub merges the PR. Nobody approves by hand. If it still does not merge, run `gh pr view --json mergeStateStatus,autoMergeRequest`:
- `BEHIND` → section D.
- `autoMergeRequest` is null → `gh pr merge --auto --squash`.

## I. Session end
Follow `AGENTS.md` section 8. Tell the user the PR link, whether it merged, and anything another owner must change.

## Never
- Close a PR and open a new one for the same work.
- Commit on a branch whose PR already merged.
- Push to `main`, force-push, rebase a pushed branch, or use `--no-verify`.
- `git add -A` / `git add .` without reading what it stages.
- Edit another person's files or their lines in `mimi/STATE.md`.
