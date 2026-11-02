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

## ISS-HS-1 — Variable shadowing and quantile clamping in uncertainty module
Symptom: PR #22 review blocked with: (1) `confidence_interval` shadows `level` and ignores it in quantile branch causing wrong CI width, (2) `np.interp` clamps samples to [p10, p90] losing 20% tail mass understating variance for CVaR.
Cause: (1) Loop variable named `level` shadowing parameter, (2) `np.interp` clamps to range instead of extrapolating.
Fix: 6814a7e (rename to `q_level`, implement linear extrapolation for tails)
Test: TestExtrapolation::test_samples_beyond_p10_p90 verifies samples exist outside quantile range
Status: fixed
