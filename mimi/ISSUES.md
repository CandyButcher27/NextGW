# Issues
<!-- Append-only, one entry per bug:
"## ISS-<n> — <title>" heading, then
Symptom: exact error text or observed behavior
Cause: root cause
Fix: commit hash
Test: the test that fails without the fix
Status: open | fixed -->

## ISS-AS-1 — CI fails: Unable to resolve action `astral-sh/setup-uv@v10`
Symptom: `##[error]Unable to resolve action `astral-sh/setup-uv@v10`, unable to find version `v10`` in the ci job "Set up job" step (run 36642364155).
Cause: astral-sh/setup-uv publishes only exact release tags (e.g. v10.2.0), no floating major tag. actions/checkout does publish `v7`.
Fix: cf39ddf (pin `astral-sh/setup-uv@v10.2.0`)
Test: none; verified by green ci run 36642429779 on throwaway PR #1.
Status: fixed
