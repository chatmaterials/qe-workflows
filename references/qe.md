# Quantum ESPRESSO Reference

Load this file when the request is QE-specific or when you need `pw.x`-style workflow details.

## Minimum file sets

### SCF or relax

- Required to run: a `pw.x` input and the referenced `.UPF` pseudopotentials
- Inspect during review: `pw.x` output, any restart directory under `outdir`, scheduler log

### DOS

- Parent sequence: `scf -> nscf`
- Post-processing: `dos.x`, optionally `projwfc.x`
- Keep `prefix`, `pseudo_dir`, and `outdir` consistent across stages

### Band structure

- Parent sequence: `scf -> bands`
- Post-processing: `bands.x`
- Do not fabricate `K_POINTS crystal_b` paths for unknown or low-symmetry structures

## Conservative defaults

These are workflow defaults, not universal truths.

### Pseudopotentials and cutoffs

- Keep the pseudo family consistent across the whole calculation.
- `ecutwfc` and `ecutrho` must follow the pseudo recommendation or project convention.
- Ultrasoft and PAW datasets often require much larger `ecutrho` than norm-conserving sets.

### Occupations and smearing

- Metals: use `occupations='smearing'` with an explicit smearing scheme and `degauss`.
- Semiconductors and insulators: prefer `occupations='fixed'` unless there is a clear reason not to.
- Do not compare energies across inconsistent smearing conventions.

### Thresholds and relaxation

- Tighten `conv_thr` for production-quality static properties compared with a cheap exploratory run.
- For ionic optimization, be explicit about whether the task is `relax` or `vc-relax`.
- Do not enable cell relaxation casually for slabs, fixed-volume comparisons, or workflows that depend on a reference lattice.

## Workflow patterns

### SCF

Typical intent:

- produce a trustworthy charge density on a uniform mesh

Watch for:

- mismatched pseudo filenames
- too-small `ecutwfc` or `ecutrho`
- metallic systems treated as fixed occupations

### Relax

Typical intent:

- reduce forces on ions or relax the cell

Watch for:

- oscillatory BFGS behavior
- geometry updates that break the intended symmetry or slab setup
- thresholds that are too loose for the downstream property

### DOS

Typical intent:

- SCF on a uniform mesh, then NSCF on a denser mesh, then `dos.x`

Watch for:

- forgetting that `dos.x` reads from the QE scratch tree, not just the text input
- using an NSCF mesh no denser than the SCF mesh
- losing consistency in `prefix` or `outdir`

### Band

Typical intent:

- SCF on a uniform mesh, then `bands` along a symmetry path, then `bands.x`

Watch for:

- invalid path coordinates
- too few unoccupied bands for the requested energy window
- mixing up `bands` and `nscf` semantics

## Restart guidance

- A QE restart is only as good as the `outdir` contents it can actually see.
- If the scratch directory is gone, be explicit that the workflow may need to rerun the parent stage.
- Preserve input and output pairs before modifying restart flags or thresholds.

## Files worth reading first

- the main `pw.x` input for `calculation`, cutoffs, occupations, `prefix`, `pseudo_dir`, and `outdir`
- the `pw.x` output for convergence messages, final energies, forces, and error signatures
- scheduler logs for walltime or MPI launch problems

## Common judgment calls

- If the pseudo family is unclear, ask before changing cutoffs.
- If the user wants a band plot, insist on a real path source such as SeeK-path or a literature reference.
- If the workflow spans `pw.x`, `dos.x`, and `bands.x`, keep naming and scratch layout consistent across all stages.
