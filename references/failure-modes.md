# QE Failure Modes and Restarts

Load this file when a Quantum ESPRESSO run failed, stalled, or produced suspicious output.

## Recovery sequence

1. confirm whether the issue is physical, numerical, or scheduler-related
2. preserve the original inputs and outputs before editing anything
3. change the fewest variables that plausibly address the failure
4. say explicitly whether the restart reuses scratch data, density, wavefunctions, or only geometry

## Common patterns

### SCF convergence not achieved

- inspect whether occupations, smearing, cutoffs, or the structure are the real problem
- lower `mixing_beta` only after checking the modeling assumptions

### Diagonalization or overlap-matrix failures

- inspect the structure for pathologies
- verify pseudo and cutoff consistency before changing unrelated knobs

### Ionic optimization stalls

- check whether the task should really be `relax` instead of `vc-relax`
- inspect the starting geometry rather than tuning solver parameters blindly

### Scratch or restart data missing

- if `outdir` contents are gone, say directly that dependent post-processing may need the parent stage to rerun

## When to recommend a clean rerun

Recommend a fresh parent run when:

- the structure is obviously corrupted or unphysical
- the scratch data required by downstream stages is missing
- the pseudo family or core physics model changed materially
